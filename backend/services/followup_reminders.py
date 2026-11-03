"""Durable reminders claimed by an external clock, independent of web sessions."""
import hashlib
import html
import json
import secrets
from datetime import datetime, timedelta
from urllib.parse import quote
from sqlalchemy import and_, or_, exists
from sqlalchemy.exc import IntegrityError
from backend import config
from backend.database import db
from backend.models import CustomerProfile, Quote, QuoteAdminState, FollowUpDelivery, SiteSetting
from backend.time_utils import vietnam_now
from backend.services.settings_storage import read_setting
from backend.services.notification_settings import clean_email

PROTOCOL = 'tagluxe-followups-v1'
SETTINGS_KEY = 'followup_reminders'
SCHEDULER_KEY = '_followup_scheduler_key'
HEALTH_KEY = '_followup_scheduler_health'
STATE_LABELS = {'leased':'Đang gửi', 'sent':'Đã gửi', 'retry':'Đang chờ thử lại', 'failed':'Cần kiểm tra'}


def settings():
    value = read_setting(SETTINGS_KEY)
    return {'enabled': value.get('enabled', False) is True,
            'email': value.get('email') or config.ADMIN_NOTIFICATION_EMAIL.lower(),
            'hour': value.get('hour', 9)}


def scheduler_key():
    row = db.session.get(SiteSetting, SCHEDULER_KEY)
    return row.value_json if row else ''


def save_settings(form):
    email = clean_email(form.get('email', ''))
    try:
        hour = int(form.get('hour', '9'))
        if not 0 <= hour <= 23: raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Giờ nhắc phải nằm trong khoảng 0–23.')
    value = {'enabled': form.get('enabled') == '1', 'email': email, 'hour': hour}
    row = db.session.get(SiteSetting, SETTINGS_KEY)
    if row is None: row = SiteSetting(key=SETTINGS_KEY); db.session.add(row)
    row.value_json = json.dumps(value, ensure_ascii=False)
    if value['enabled'] and not scheduler_key():
        db.session.add(SiteSetting(key=SCHEDULER_KEY, value_json=secrets.token_urlsafe(40)))
    db.session.commit()
    return value


def _blocked(kind, target, due, today, email, now):
    return exists().where(and_(FollowUpDelivery.kind == kind, FollowUpDelivery.target_id == target,
        FollowUpDelivery.due_on == due, FollowUpDelivery.reminder_on == today,
        FollowUpDelivery.recipient == email, or_(FollowUpDelivery.status.in_(['sent','failed']),
            and_(FollowUpDelivery.status == 'leased', FollowUpDelivery.lease_until > now),
            and_(FollowUpDelivery.status == 'retry', FollowUpDelivery.next_retry_at > now))))


def due_items(today, email, now):
    customers = CustomerProfile.query.filter(CustomerProfile.follow_up_on <= today,
        CustomerProfile.status.notin_(['Đã chốt','Chưa chốt','Tạm dừng']),
        ~_blocked('customer', CustomerProfile.phone, CustomerProfile.follow_up_on, today, email, now)
    ).order_by(CustomerProfile.follow_up_on, CustomerProfile.phone).limit(50).all()
    quotes = db.session.query(QuoteAdminState, Quote).join(Quote, Quote.id == QuoteAdminState.quote_id).filter(
        QuoteAdminState.follow_up_on <= today, Quote.status.notin_(['Đã xong','Đã hủy']),
        ~_blocked('quote', QuoteAdminState.quote_id, QuoteAdminState.follow_up_on, today, email, now)
    ).order_by(QuoteAdminState.follow_up_on, Quote.id).limit(50).all()
    items = [dict(kind='customer', target_id=c.phone, name=c.customer_name, phone=c.phone,
                  due=c.follow_up_on, owner=c.owner, label='Chăm sóc khách hàng') for c in customers]
    items.extend(dict(kind='quote', target_id=q.id, name=q.customer_name, phone=q.phone,
        due=state.follow_up_on, owner=state.owner, label='Báo giá #'+q.id) for state, q in quotes)
    return sorted(items, key=lambda item:(item['due'],item['kind'],item['target_id']))[:50]


def delivery_id(item, today, email):
    raw = json.dumps([item['kind'],item['target_id'],item['due'].isoformat(),today.isoformat(),email])
    return hashlib.sha256(raw.encode()).hexdigest()


def _claim(item, today, email, now, token):
    key = delivery_id(item, today, email)
    try:
        with db.session.begin_nested():
            db.session.add(FollowUpDelivery(id=key, kind=item['kind'], target_id=item['target_id'],
                due_on=item['due'], reminder_on=today, recipient=email, status='leased',
                lease_token=token, lease_until=now+timedelta(minutes=10)))
            db.session.flush()
        return True
    except IntegrityError:
        # A unique daily key plus a conditional update makes multi-process claims safe.
        changed = FollowUpDelivery.query.filter(FollowUpDelivery.id==key,
            FollowUpDelivery.status.in_(['leased','retry']),
            or_(FollowUpDelivery.lease_until.is_(None),FollowUpDelivery.lease_until<=now),
            or_(FollowUpDelivery.next_retry_at.is_(None),FollowUpDelivery.next_retry_at<=now)
        ).update({'status':'leased','lease_token':token,'lease_until':now+timedelta(minutes=10)},
                 synchronize_session=False)
        return changed == 1


def prepare(now=None, local_now=None):
    now = now or datetime.utcnow()
    local_now = local_now or vietnam_now()
    if db.session.get(SiteSetting, HEALTH_KEY) is None:
        try:
            with db.session.begin_nested():
                db.session.add(SiteSetting(key=HEALTH_KEY,value_json='{}'));db.session.flush()
        except IntegrityError: pass
    SiteSetting.query.filter_by(key=HEALTH_KEY).update(
        {'value_json':json.dumps({'checked_at':now.isoformat()})},synchronize_session=False)
    prefs = settings()
    empty = {'status':'success','protocol':PROTOCOL,'batch_token':None,'items_count':0}
    if not prefs['enabled'] or local_now.hour < prefs['hour']:
        db.session.commit()
        return empty
    email = clean_email(prefs['email'])
    token = secrets.token_urlsafe(32)
    items = [item for item in due_items(local_now.date(),email,now)
             if _claim(item,local_now.date(),email,now,token)]
    db.session.commit()
    if not items: return empty
    text, markup = email_content(items,local_now.date())
    return dict(empty, batch_token=token,items_count=len(items),recipient=email,
        subject='[TAGLUXE] '+str(len(items))+' lịch cần liên hệ · '+local_now.strftime('%d/%m/%Y'),
        text_body=text,html_body=markup)


def email_content(items, today):
    origin = config.site_origin()
    lines = ['TAGLUXE · LỊCH CẦN LIÊN HỆ '+today.strftime('%d/%m/%Y')]
    cards = []
    for item in items:
        link = origin + ('/admin/customers/' if item['kind']=='customer' else '/admin/quotes/') + quote(item['target_id'],safe='')
        overdue = (today-item['due']).days
        schedule = item['due'].strftime('%d/%m/%Y') + (' · quá hạn '+str(overdue)+' ngày' if overdue else ' · hôm nay')
        lines.append('\n'+item['name']+' · '+item['phone']+'\n'+item['label']+'\nHẹn: '+schedule+
                     '\nPhụ trách: '+(item['owner'] or 'Chưa phân công')+'\nMở hồ sơ: '+link)
        esc = lambda value:html.escape(str(value),quote=True)
        cards.append('<div style="border:1px solid #dce6de;border-radius:10px;padding:16px;margin:12px 0">'
            '<strong>'+esc(item['name'])+'</strong><p>'+esc(item['phone'])+' · '+esc(item['label'])+'</p>'
            '<p>Hẹn: '+esc(schedule)+'</p><p>Phụ trách: '+esc(item['owner'] or 'Chưa phân công')+'</p>'
            '<a href="'+esc(link)+'">Mở hồ sơ để kiểm tra →</a></div>')
    footer = 'Sau khi liên hệ, hãy cập nhật ngày hẹn tiếp theo hoặc bỏ lịch trong admin. Lịch quá hạn chưa xử lý sẽ được nhắc lại ngày mai.'
    lines.append('\n'+footer)
    return '\n'.join(lines),'<div style="font-family:Arial,sans-serif;color:#203f30;max-width:680px;margin:auto"><h2>TAGLUXE · Lịch cần liên hệ</h2><p>'+today.strftime('%d/%m/%Y')+'</p>'+''.join(cards)+'<p>'+footer+'</p></div>'


def finish(token, success=True, error='mail', now=None):
    now = now or datetime.utcnow()
    rows = FollowUpDelivery.query.filter_by(lease_token=token,status='leased').all()
    changed=0
    for row in rows:
        if success:
            values={'status':'sent','sent_at':now,'last_error':None}
        else:
            attempts=row.attempts+1
            values={'attempts':attempts,'status':'failed' if attempts>=5 and error!='quota' else 'retry',
                'next_retry_at':now+timedelta(hours=1),
                'last_error':'Google Mail hết hạn mức gửi.' if error=='quota' else 'Chưa gửi được email. Hệ thống sẽ thử lại.'}
        values['lease_until']=None
        changed+=FollowUpDelivery.query.filter_by(id=row.id,lease_token=token,status='leased').update(
            values,synchronize_session=False)
    db.session.commit()
    return {'status':'success','protocol':PROTOCOL,'updated':changed}


def last_delivery(kind, target_id, due):
    if not due: return None
    return FollowUpDelivery.query.filter_by(kind=kind,target_id=target_id,due_on=due).order_by(
        FollowUpDelivery.reminder_on.desc()).first()
