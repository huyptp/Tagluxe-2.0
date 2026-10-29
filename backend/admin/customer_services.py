"""Unified private directory; manual leads never manufacture quote/revenue rows."""
import re
from datetime import date
from sqlalchemy import select, func, case, or_
from backend.database import db
from backend.models import Quote, CustomerProfile
from backend.validators import normalize_phone
from backend.admin.workspace_services import local_today

SOURCES = {'zalo':'Zalo', 'website':'Website', 'facebook':'Facebook', 'phone':'Điện thoại',
           'direct':'Trực tiếp', 'referral':'Giới thiệu', 'other':'Khác'}
CUSTOMER_STATUSES = ('Mới', 'Đang tư vấn', 'Đã chốt', 'Chưa chốt', 'Tạm dừng')
INACTIVE_STATUSES = ('Đã chốt', 'Chưa chốt', 'Tạm dừng')


def clean_customer(form):
    value = {}
    for key, limit in {'customer_name':120,'company':160,'email':254,'address':500,
                       'needs':3000,'notes':5000,'owner':80}.items():
        value[key] = form.get(key, '').strip()
        if len(value[key]) > limit or any(ord(c)<32 and c not in '\r\n\t' for c in value[key]):
            raise ValueError('Một trường quá dài hoặc chứa ký tự không hợp lệ. Vui lòng kiểm tra lại.')
    if len(value['customer_name']) < 2:
        raise ValueError('Vui lòng nhập tên khách hàng từ 2 ký tự.')
    value['phone'] = normalize_phone(form.get('phone',''))
    if not value['phone']:
        raise ValueError('Nhập số di động Việt Nam hợp lệ, ví dụ 0901234567 hoặc +84901234567.')
    value['source'] = form.get('source', 'zalo')
    value['status'] = form.get('status', 'Đang tư vấn')
    if value['source'] not in SOURCES or value['status'] not in CUSTOMER_STATUSES:
        raise ValueError('Nguồn khách hoặc trạng thái không hợp lệ.')
    if value['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value['email']):
        raise ValueError('Địa chỉ email chưa đúng định dạng.')
    for key in ('needed_on','follow_up_on'):
        raw = form.get(key,'').strip()
        try:
            value[key] = date.fromisoformat(raw) if raw else None
            if value[key] and not 2000 <= value[key].year <= 2100: raise ValueError()
        except ValueError:
            raise ValueError('Ngày cần hàng và ngày hẹn cần nằm trong khoảng 2000–2100.')
    return value


def directory_query():
    aggregate = db.session.query(Quote.phone.label('phone'), func.count(Quote.id).label('quote_count'),
        func.max(Quote.created_at).label('quote_at'),
        func.sum(case((Quote.status!='Đã hủy',Quote.total_price),else_=0)).label('value'),
        func.sum(case((Quote.status.in_(('Đã chốt','Đã xong')),Quote.total_price),else_=0)).label('closed_value'),
        case((func.max(case((Quote.status.in_(('Đã chốt','Đã xong')),1),else_=0))==1,'Đã chốt'),
             (func.max(case((Quote.status!='Đã hủy',1),else_=0))==0,'Chưa chốt'),
             (func.max(case((Quote.status.in_(('Đang tư vấn','Đã tư vấn','Đang chốt')),1),else_=0))==1,'Đang tư vấn'),
             else_='Mới').label('inferred_status')
    ).filter(Quote.phone!='').group_by(Quote.phone).subquery()
    phones = select(Quote.phone).where(Quote.phone!='').union(select(CustomerProfile.phone)).subquery()
    latest_name = select(Quote.customer_name).where(Quote.phone==phones.c.phone).order_by(
        Quote.created_at.desc(),Quote.id.desc()).limit(1).correlate(phones).scalar_subquery()
    recent = case((aggregate.c.quote_at.is_(None),CustomerProfile.updated_at),
        (CustomerProfile.updated_at.is_(None),aggregate.c.quote_at),
        (CustomerProfile.updated_at>aggregate.c.quote_at,CustomerProfile.updated_at),else_=aggregate.c.quote_at)
    return db.session.query(phones.c.phone,func.coalesce(CustomerProfile.customer_name,latest_name).label('name'),
        func.coalesce(aggregate.c.quote_count,0).label('quote_count'),
        func.coalesce(aggregate.c.value,0).label('value'),func.coalesce(aggregate.c.closed_value,0).label('closed_value'),
        recent.label('last_contact'),func.coalesce(CustomerProfile.source,'website').label('source'),
        func.coalesce(CustomerProfile.status,aggregate.c.inferred_status,'Mới').label('status'),CustomerProfile.owner,
        CustomerProfile.company,CustomerProfile.follow_up_on,CustomerProfile.needed_on
    ).select_from(phones).outerjoin(aggregate,aggregate.c.phone==phones.c.phone).outerjoin(
        CustomerProfile,CustomerProfile.phone==phones.c.phone)


def customer_list(args):
    rows = directory_query().subquery()
    base = db.session.query(rows)
    due = (rows.c.follow_up_on<=local_today()) & rows.c.status.notin_(INACTIVE_STATUSES)
    counts = db.session.query(func.count(rows.c.phone),
        func.coalesce(func.sum(case((rows.c.source!='website',1),else_=0)),0),
        func.coalesce(func.sum(case((rows.c.quote_count==0,1),else_=0)),0),
        func.coalesce(func.sum(case((due,1),else_=0)),0)).one()
    metrics = dict(zip(('total','manual','unquoted','due'),counts))
    search = args.get('q','').strip()[:200]
    source = args.get('source','')
    status = args.get('status','')
    view = args.get('view','all')
    sort = args.get('sort','recent')
    if source not in SOURCES: source=''
    if status not in CUSTOMER_STATUSES: status=''
    if view not in ('all','due','unquoted'):view='all'
    if sort not in ('recent','value','count'):sort='recent'
    if search:
        normalized = normalize_phone(search)
        matching = select(Quote.phone).where(Quote.customer_name.icontains(search,autoescape=True))
        base = base.filter(or_(rows.c.name.icontains(search,autoescape=True),
            rows.c.phone.contains(normalized or search,autoescape=True),rows.c.phone.in_(matching),
            rows.c.company.icontains(search,autoescape=True)))
    if source:base=base.filter(rows.c.source==source)
    if status:base=base.filter(rows.c.status==status)
    if view=='due':base=base.filter(due)
    if view=='unquoted':base=base.filter(rows.c.quote_count==0)
    order={'value':rows.c.value.desc(),'count':rows.c.quote_count.desc()}.get(sort,rows.c.last_contact.desc())
    return base.order_by(order,rows.c.phone),metrics,dict(q=search,source=source,status=status,view=view,sort=sort)
