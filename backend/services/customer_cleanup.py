"""Transaction-scoped deletion of quote-derived customer records."""
import hashlib
from datetime import datetime
from backend.database import db
from backend.models import QuoteDeletion, SyncTask, IdempotencyRecord


def quote_set_fingerprint(quote_ids):
    return hashlib.sha256('\n'.join(sorted(quote_ids)).encode('utf-8')).hexdigest()


def delete_quote_records(quotes, deleted_by):
    """Caller commits or rolls back the whole deletion; no outbound messages."""
    ids=[q.id for q in quotes]
    if not ids:return 0
    tasks=SyncTask.query.filter(SyncTask.record_type=='quote',SyncTask.record_id.in_(ids)).with_for_update().all()
    now=datetime.utcnow()
    if any(t.status=='processing' and (t.lease_until is None or t.lease_until>now) for t in tasks):
        raise ValueError('Báo giá đang được đồng bộ. Vui lòng đợi ít giây rồi tải lại hồ sơ trước khi xóa.')
    for task in tasks:db.session.delete(task)
    keys=[q.idempotency_key for q in quotes if q.idempotency_key]
    if keys:IdempotencyRecord.query.filter(IdempotencyRecord.key.in_(keys)).delete(synchronize_session=False)
    existing={r[0] for r in db.session.query(QuoteDeletion.quote_id).filter(QuoteDeletion.quote_id.in_(ids)).all()}
    for quote in quotes:
        if quote.id not in existing:
            db.session.add(QuoteDeletion(quote_id=quote.id,deleted_by=deleted_by))
        db.session.delete(quote)
    return len(quotes)
