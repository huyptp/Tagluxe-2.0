"""Business timestamps use Vietnam wall time; queue/lease clocks remain UTC.

Existing business DateTime columns have no timezone. Keep their wall-time
contract consistent with CSV exports and the Google Sheets restore format.
Do not apply this helper to idempotency expiry or sync worker lease fields.
"""
from datetime import datetime, timedelta, timezone

VIETNAM_TIMEZONE = timezone(timedelta(hours=7), name='Asia/Ho_Chi_Minh')


def vietnam_now():
    return datetime.now(VIETNAM_TIMEZONE).replace(tzinfo=None)
