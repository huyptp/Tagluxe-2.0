"""Queries shared by the admin list, exports and follow-up dashboard."""
from backend.time_utils import vietnam_now
from datetime import date, datetime, time, timedelta
from sqlalchemy import or_, func, case
from backend.models import Quote, QuoteAdminState

PRIORITIES = {'normal': 'Bình thường', 'high': 'Ưu tiên', 'urgent': 'Khẩn cấp'}
CLOSED_STATUSES = ('Đã xong', 'Đã hủy')
FILTER_KEYS = ('q', 'phone', 'status', 'sync', 'priority', 'follow_up', 'from_date', 'to_date', 'sort')


def local_today():
    return vietnam_now().date()


def page_number(values):
    try:
        return max(1, int(values.get('page', 1)))
    except (TypeError, ValueError):
        return 1


def quote_filters(values):
    result = {key: str(values.get(key, '') or '').strip()[:200] for key in FILTER_KEYS}
    for key in ('from_date', 'to_date'):
        if result[key]:
            try:
                day = date.fromisoformat(result[key])
                if not 1900 <= day.year <= 2100:
                    raise ValueError()
                result[key] = day.isoformat()
            except ValueError:
                raise ValueError('Ngày lọc không hợp lệ. Vui lòng chọn ngày từ năm 1900 đến 2100.')
    if result['from_date'] and result['to_date'] and result['from_date'] > result['to_date']:
        raise ValueError('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')
    return result


def filtered_quotes(filters):
    query = Quote.query.outerjoin(QuoteAdminState)
    if filters['q']:
        query = query.filter(or_(Quote.customer_name.icontains(filters['q'], autoescape=True),
            Quote.phone.contains(filters['q'], autoescape=True), Quote.id.icontains(filters['q'], autoescape=True)))
    if filters['phone']:
        query = query.filter(Quote.phone == filters['phone'])
    if filters['status'] and filters['status'] != 'all':
        query = query.filter(Quote.status == filters['status'])
    if filters['sync'] in ('pending', 'synced', 'failed'):
        query = query.filter(Quote.sync_status == filters['sync'])
    if filters['priority'] in PRIORITIES:
        query = query.filter(func.coalesce(QuoteAdminState.priority, 'normal') == filters['priority'])
    if filters['from_date']:
        query = query.filter(Quote.created_at >= datetime.combine(date.fromisoformat(filters['from_date']), time.min))
    if filters['to_date']:
        query = query.filter(Quote.created_at < datetime.combine(date.fromisoformat(filters['to_date']) + timedelta(days=1), time.min))
    if filters['follow_up'] in ('due', 'scheduled'):
        query = query.filter(Quote.status.notin_(CLOSED_STATUSES), QuoteAdminState.follow_up_on.isnot(None))
        if filters['follow_up'] == 'due':
            query = query.filter(QuoteAdminState.follow_up_on <= local_today())
    sort = filters['sort']
    if sort == 'oldest':
        return query.order_by(Quote.created_at.asc(), Quote.id.asc())
    if sort == 'value':
        return query.order_by(Quote.total_price.desc(), Quote.id.desc())
    if sort == 'follow_up':
        return query.order_by(case((QuoteAdminState.follow_up_on.is_(None), 1), else_=0),
                              QuoteAdminState.follow_up_on.asc(), Quote.id.desc())
    return query.order_by(Quote.created_at.desc(), Quote.id.desc())


def quote_summary(query):
    row = query.order_by(None).with_entities(
        func.count(Quote.id),
        func.coalesce(func.sum(case((Quote.status != 'Đã hủy', Quote.total_price), else_=0)), 0),
        func.coalesce(func.sum(case((Quote.status.in_(('Đã chốt', 'Đã xong')), Quote.total_price), else_=0)), 0),
        func.coalesce(func.sum(case((Quote.sync_status == 'failed', 1), else_=0)), 0),
    ).one()
    return dict(count=row[0], value=row[1], closed_value=row[2], failed_sync=row[3])
