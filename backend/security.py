import time
import json
import hashlib
import threading
from datetime import datetime
from functools import wraps
from flask import request, jsonify, flash, redirect, url_for

class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory Sliding Window Rate Limiter.
    Tracks timestamps per IP/key to prevent spam and brute-force attacks.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._records = {}  # {key: [timestamp1, timestamp2, ...]}
        self._last_cleanup = time.time()

    def _cleanup(self, now, max_window):
        """Removes expired entries every 10 minutes to prevent memory leak"""
        if now - self._last_cleanup < 600:
            return
        self._last_cleanup = now
        expired_keys = []
        for key, timestamps in self._records.items():
            valid_ts = [t for t in timestamps if now - t < max_window]
            if not valid_ts:
                expired_keys.append(key)
            else:
                self._records[key] = valid_ts
        for k in expired_keys:
            self._records.pop(k, None)

    def is_allowed(self, key, limit, window_sec):
        """
        Returns True if request is within limits, False otherwise.
        """
        now = time.time()
        with self._lock:
            self._cleanup(now, window_sec)
            timestamps = self._records.get(key, [])
            # Filter out timestamps outside the window
            timestamps = [t for t in timestamps if now - t < window_sec]
            if len(timestamps) >= limit:
                self._records[key] = timestamps
                return False
            timestamps.append(now)
            self._records[key] = timestamps
            return True

    def reset_key(self, key):
        """Resets the rate limit for a specific key (e.g., after successful login)"""
        with self._lock:
            self._records.pop(key, None)


def generate_canonical_hash(data):
    """
    Creates a deterministic, stable SHA256 hash from canonical normalized dictionary.
    Keys are sorted, accessories list is sorted, customer_name and notes preserve case.
    """
    canonical_dict = {}
    for k in [
        'customer_name', 'phone', 'category', 'quantity', 'width', 'size',
        'accessories', 'include_vat', 'finish', 'effects', 'orientation',
        'printed_logo', 'holder_type', 'punched_hole', 'notes'
    ]:
        val = data.get(k)
        if k == 'accessories':
            if isinstance(val, list):
                val = sorted([str(x).strip() for x in val if str(x).strip()])
            elif isinstance(val, str) and val.strip():
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        val = sorted([str(x).strip() for x in parsed if str(x).strip()])
                    else:
                        val = [val.strip()]
                except Exception:
                    val = [val.strip()]
            else:
                val = []
        elif k in ('include_vat', 'printed_logo'):
            val = bool(val)
        elif k == 'quantity':
            try:
                val = int(val)
            except Exception:
                val = 0
        elif k == 'phone':
            val = str(val or '').strip()
        else:
            val = str(val or '').strip()
        canonical_dict[k] = val

    canonical_json = json.dumps(canonical_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


class IdempotencyManager:
    """
    Atomic Idempotency Manager with Database Persistence.
    Prevents duplicate submissions across multiple worker processes (Gunicorn)
    and handles double-clicks within a 60-second window.
    """
    def __init__(self, ttl_sec=60):
        self._lock = threading.Lock()
        self._cache = {}
        self._ttl = ttl_sec

    def generate_key(self, *args, **kwargs):
        """Creates a deterministic hash key from canonical attributes or request_id"""
        scope = kwargs.get('scope')
        request_id = kwargs.get('request_id')
        content_hash = kwargs.get('content_hash')

        if not scope and args and args[0] in ('quote', 'demo'):
            scope = args[0]
            if len(args) == 2 and isinstance(args[1], str) and len(args[1]) > 30:
                content_hash = args[1]
            elif len(args) == 3:
                request_id = args[1]
                content_hash = args[2]

        if scope and request_id:
            return f"{scope}:{request_id.strip()}"
        if scope and content_hash:
            time_bucket = int(time.time() // 60)
            return f"{scope}:hash:{content_hash}:{time_bucket}"

        raw_str = "|".join(str(a if a is not None else '').strip().lower() for a in args)
        return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

    def get_existing(self, key):
        """Checks if a valid recent request exists for this key in DB or memory"""
        from backend.models import IdempotencyRecord
        rec = IdempotencyRecord.query.filter_by(key=key).first()
        if rec and rec.created_at:
            age = (datetime.utcnow() - rec.created_at).total_seconds()
            if age < self._ttl:
                if rec.status == 'COMPLETED' and rec.response_json:
                    return json.loads(rec.response_json)
        return None

    def store(self, key, result, request_id=None, content_hash=None):
        """Stores the result into DB"""
        from backend.database import db
        from backend.models import IdempotencyRecord
        rec = IdempotencyRecord.query.filter_by(key=key).first()
        if not rec:
            rec = IdempotencyRecord(
                key=key,
                request_id=request_id,
                content_hash=content_hash,
                created_at=datetime.utcnow(),
                status='COMPLETED',
                response_json=json.dumps(result, ensure_ascii=False)
            )
            db.session.add(rec)
        else:
            rec.status = 'COMPLETED'
            rec.response_json = json.dumps(result, ensure_ascii=False)
            if request_id:
                rec.request_id = request_id
            if content_hash:
                rec.content_hash = content_hash
        db.session.commit()


# Singleton instances
limiter = SlidingWindowRateLimiter()
idempotency = IdempotencyManager(ttl_sec=30)


def get_client_ip():
    """Extracts client IP address safely set by ProxyFix / WSGI environment"""
    return request.remote_addr or '127.0.0.1'


def rate_limit(limit=10, window_sec=60, error_message=None, is_json=True):
    """
    Decorator to apply sliding-window rate limiting to Flask routes.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = get_client_ip()
            key = f"{request.endpoint}:{client_ip}"
            
            if not limiter.is_allowed(key, limit=limit, window_sec=window_sec):
                msg = error_message or f"Bạn đang thao tác quá nhanh. Vui lòng thử lại sau ít giây."
                if is_json:
                    return jsonify({
                        'success': False,
                        'rate_limited': True,
                        'message': msg
                    }), 429
                else:
                    flash(msg, 'error')
                    return redirect(request.referrer or url_for('storefront.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
