import os
import json
import time
import uuid
import random
import logging
import threading
import urllib.request
import urllib.error
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Singleton thread management
_worker_thread = None
_stop_event = threading.Event()


def get_worker_id():
    """Generates unique worker instance identifier"""
    return f"worker-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def lease_due_tasks(db, limit=10, lease_sec=60):
    """
    Atomically leases due tasks using database transaction.
    Tasks are locked to worker_id with lease_until timestamp before network calls.
    """
    from backend.models import SyncTask
    worker_id = get_worker_id()
    now = datetime.utcnow()

    try:
        # Find tasks that are pending or ready for retry, and not currently leased
        tasks = SyncTask.query.filter(
            SyncTask.status.in_(['pending', 'retry']),
            (SyncTask.next_retry_at.is_(None) | (SyncTask.next_retry_at <= now)),
            (SyncTask.lease_until.is_(None) | (SyncTask.lease_until < now))
        ).order_by(SyncTask.id.asc()).limit(limit).all()

        if not tasks:
            return worker_id, []

        leased_ids = []
        for t in tasks:
            t.status = 'processing'
            t.worker_id = worker_id
            t.lease_until = now + timedelta(seconds=lease_sec)
            t.updated_at = now
            leased_ids.append(t.id)

        db.session.commit()
        return worker_id, leased_ids
    except Exception as ex:
        db.session.rollback()
        logger.error(f"[SYNC_WORKER_LEASE_ERROR] Failed to lease tasks: {ex}")
        return worker_id, []


def execute_sync_task(task_id, worker_id, app):
    """
    Executes a leased sync task against Google Sheets webhook.
    Strictly validates HTTP 200, JSON dict, status: 'success', and matching record_id.
    """
    with app.app_context():
        from backend.database import db
        from backend.models import SyncTask, Quote, DemoRequest
        from backend.config import GOOGLE_SHEET_WEBHOOK_URL, GOOGLE_SHEET_SECRET

        now = datetime.utcnow()
        task = SyncTask.query.filter_by(id=task_id).first()
        if not task:
            return False, "Task not found"

        # Verify this worker still holds the lease
        if task.worker_id != worker_id or (task.lease_until and task.lease_until < now):
            logger.warning(f"[SYNC_WORKER_LEASE_EXPIRED] Task {task_id} lease expired or stolen.")
            return False, "Lease expired"

        webhook_url = GOOGLE_SHEET_WEBHOOK_URL
        if not webhook_url:
            err_msg = "Google Sheet webhook URL not configured (GOOGLE_SHEET_WEBHOOK_URL is empty)"
            _record_task_failure(db, task, err_msg)
            return False, err_msg

        # Prepare payload with mandatory secret and record identification
        try:
            payload_data = json.loads(task.payload) if isinstance(task.payload, str) else task.payload
        except Exception:
            payload_data = {}

        payload_data['secret'] = GOOGLE_SHEET_SECRET or ''
        payload_data['record_id'] = task.record_id
        payload_data['record_type'] = task.record_type
        payload_data['id'] = task.record_id
        payload_data['event_key'] = task.event_key

        encoded_data = json.dumps(payload_data, ensure_ascii=False).encode('utf-8')
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'TagLuxe-SyncWorker/2.0'
        }

        resp_code = 0
        resp_text = ""
        resp_json = None

        try:
            try:
                import requests
                r = requests.post(webhook_url, json=payload_data, headers=headers, timeout=15)
                resp_code = r.status_code
                resp_text = r.text
                try:
                    resp_json = r.json()
                except Exception:
                    resp_json = None
            except ImportError:
                req = urllib.request.Request(webhook_url, data=encoded_data, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_code = resp.getcode()
                    resp_text = resp.read().decode('utf-8')
                    try:
                        resp_json = json.loads(resp_text)
                    except Exception:
                        resp_json = None
        except Exception as net_err:
            resp_code = 0
            resp_text = str(net_err)
            resp_json = None

        # STRICT VALIDATION CONTRACT:
        # 1. HTTP 200
        # 2. Response body is valid JSON Object (dict)
        # 3. resp_json.get('status') == 'success'
        # 4. Returned record_id matches task.record_id (if returned)
        is_success = False
        err_detail = ""

        if resp_code == 200:
            if isinstance(resp_json, dict):
                status_val = resp_json.get('status')
                returned_id = resp_json.get('record_id')
                if status_val == 'success':
                    if not returned_id or str(returned_id).strip() == str(task.record_id).strip():
                        is_success = True
                    else:
                        err_detail = f"Record ID mismatch: expected {task.record_id}, got {returned_id}"
                else:
                    err_detail = resp_json.get('message') or resp_json.get('error') or f"Status: {status_val}"
            else:
                err_detail = f"Invalid response structure: expected JSON object, got {resp_text[:120]}"
        else:
            err_detail = f"HTTP {resp_code}: {resp_text[:150]}"

        if is_success:
            _record_task_success(db, task)
            return True, "Synced successfully"
        else:
            _record_task_failure(db, task, err_detail)
            return False, err_detail


def _record_task_success(db, task):
    """Marks task as succeeded and updates corresponding Quote/DemoRequest record"""
    from backend.models import Quote, DemoRequest
    now = datetime.utcnow()
    task.status = 'succeeded'
    task.last_error = None
    task.lease_until = None
    task.worker_id = None
    task.updated_at = now

    if task.record_type == 'quote':
        q = Quote.query.filter_by(id=task.record_id).first()
        if q:
            q.sync_status = 'synced'
            q.sync_error = None
    elif task.record_type == 'demo':
        d = DemoRequest.query.filter_by(id=task.record_id).first()
        if d:
            d.sync_status = 'synced'
            d.sync_error = None

    try:
        db.session.commit()
    except Exception as ex:
        db.session.rollback()
        logger.error(f"[SYNC_WORKER_COMMIT_SUCCESS_ERROR] {ex}")


def _record_task_failure(db, task, err_detail):
    """
    Applies exponential backoff with jitter and records error.
    Transitions task to 'retry' or 'failed' if max attempts reached.
    """
    from backend.models import Quote, DemoRequest
    now = datetime.utcnow()
    task.attempt_count += 1
    task.last_error = str(err_detail)[:500]
    task.lease_until = None
    task.worker_id = None
    task.updated_at = now

    # Exponential backoff schedule with jitter: 30s, 2m, 10m, 30m, 2h
    backoff_delays = [30, 120, 600, 1800, 7200]
    idx = min(task.attempt_count - 1, len(backoff_delays) - 1)
    jitter = random.randint(0, 15)
    delay_sec = backoff_delays[idx] + jitter
    task.next_retry_at = now + timedelta(seconds=delay_sec)

    if task.attempt_count >= 5:
        task.status = 'failed'
    else:
        task.status = 'retry'

    if task.record_type == 'quote':
        q = Quote.query.filter_by(id=task.record_id).first()
        if q:
            q.sync_status = 'failed'
            q.sync_error = str(err_detail)[:500]
            q.retry_count = task.attempt_count
    elif task.record_type == 'demo':
        d = DemoRequest.query.filter_by(id=task.record_id).first()
        if d:
            d.sync_status = 'failed'
            d.sync_error = str(err_detail)[:500]
            d.retry_count = task.attempt_count

    try:
        db.session.commit()
    except Exception as ex:
        db.session.rollback()
        logger.error(f"[SYNC_WORKER_COMMIT_FAIL_ERROR] {ex}")


def run_sync_worker_loop(app, poll_interval_sec=5, stop_event=None):
    """Continuous polling loop for the sync worker"""
    logger.info("[SYNC_WORKER] Background sync worker started.")
    while stop_event is None or not stop_event.is_set():
        try:
            with app.app_context():
                from backend.database import db
                worker_id, task_ids = lease_due_tasks(db, limit=5, lease_sec=60)

            for tid in task_ids:
                try:
                    execute_sync_task(tid, worker_id, app)
                except Exception as task_ex:
                    logger.error(f"[SYNC_WORKER_TASK_ERROR] Task {tid} failed: {task_ex}")

        except Exception as loop_ex:
            logger.error(f"[SYNC_WORKER_LOOP_ERROR] Error in worker loop: {loop_ex}")

        # Sleep interval with interruptible polling
        for _ in range(poll_interval_sec * 2):
            if stop_event and stop_event.is_set():
                break
            time.sleep(0.5)

    logger.info("[SYNC_WORKER] Background sync worker stopped.")


def start_background_sync_worker(app):
    """Launches the background sync worker daemon thread"""
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return _worker_thread

    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=run_sync_worker_loop,
        args=(app, 5, _stop_event),
        daemon=True,
        name="TagLuxe-SyncWorker"
    )
    _worker_thread.start()
    return _worker_thread


def stop_background_sync_worker():
    """Signals the worker thread to stop cleanly"""
    _stop_event.set()
