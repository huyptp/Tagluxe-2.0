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


class IdempotencyManager:
    """
    Atomic Idempotency Manager with Database Persistence.
    Prevents duplicate submissions across multiple worker processes (Gunicorn)
    and handles double-clicks within a 30-second window.
    """
    def __init__(self, ttl_sec=30):
        self._lock = threading.Lock()
        self._cache = {}  # In-memory fallback
        self._ttl = ttl_sec

    def generate_key(self, *args):
        """Creates a deterministic hash key from canonical order attributes"""
        raw_str = "|".join(str(a if a is not None else '').strip().lower() for a in args)
        return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

    def get_existing(self, key):
        """Checks if a valid recent request exists for this key in DB or memory"""
        now = time.time()
        # 1. Check database persistence
        try:
            from backend.models import IdempotencyRecord
            rec = IdempotencyRecord.query.filter_by(key=key).first()
            if rec and rec.created_at:
                age = (datetime.now() - rec.created_at).total_seconds()
                if age < self._ttl:
                    return json.loads(rec.response_json)
        except Exception:
            pass

        # 2. In-memory fallback
        with self._lock:
            entry = self._cache.get(key)
            if entry and (now - entry['time'] < self._ttl):
                return entry.get('result')
            return None

    def store(self, key, result):
        """Stores the result atomically into DB and memory"""
        now = time.time()
        # 1. Save to Database
        try:
            from backend.database import db
            from backend.models import IdempotencyRecord
            rec = IdempotencyRecord(
                key=key,
                created_at=datetime.now(),
                response_json=json.dumps(result, ensure_ascii=False)
            )
            db.session.merge(rec)
            db.session.commit()
        except Exception:
            try:
                from backend.database import db
                db.session.rollback()
            except Exception:
                pass

        # 2. Save to in-memory cache
        with self._lock:
            if len(self._cache) > 200:
                expired = [k for k, v in self._cache.items() if now - v['time'] > self._ttl]
                for k in expired:
                    self._cache.pop(k, None)
            self._cache[key] = {'time': now, 'result': result}


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
