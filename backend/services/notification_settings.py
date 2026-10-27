"""Owner-managed recipients; never accept recipients from a public quote payload."""
import re
import time
import threading
from backend import config
from backend.database import db
from backend.models import AdminUser, SiteSetting
from backend.services.settings_storage import read_setting

MAX_RECIPIENTS = 20
_capabilities = {}
_capability_lock = threading.Lock()


def clean_email(value):
    value = str(value or '').strip().lower()
    if len(value)>254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}",value):
        raise ValueError('Địa chỉ email chưa hợp lệ. Mỗi dòng chỉ nhập một email.')
    local, domain = value.rsplit('@',1)
    if local.startswith('.') or local.endswith('.') or '..' in value or any(p.startswith('-') or p.endswith('-') for p in domain.split('.')):
        raise ValueError('Địa chỉ email chưa hợp lệ.')
    return value


def manual_recipients():
    if db.session.get(SiteSetting,'notifications') is None:
        default = config.ADMIN_NOTIFICATION_EMAIL.strip()
        return [{'id':'owner-default','name':'Chủ shop','email':clean_email(default),'enabled':True}] if default else []
    return read_setting('notifications').get('recipients',[])


def notification_recipients():
    addresses = [clean_email(r['email']) for r in manual_recipients() if r.get('enabled')]
    addresses.extend(clean_email(u.email) for u in AdminUser.query.filter_by(active=True,receive_notifications=True).all())
    unique = sorted(set(addresses))
    if len(unique)>MAX_RECIPIENTS:
        raise ValueError('Tối đa 20 địa chỉ email đang bật nhận thông báo.')
    return unique


def notification_envelope():
    return {'notification_recipients':notification_recipients(), 'notification_protocol':'tagluxe-email-v2'}


def prepare_notifications(payload, webhook_url):
    """Explicit recipient settings require a compatible deployment BEFORE POST.

    This prevents an older script from silently mailing its hardcoded address
    when the owner has disabled it or selected staff recipients instead.
    """
    payload.update(notification_envelope())
    required = (db.session.get(SiteSetting,'notifications') is not None or
                AdminUser.query.filter_by(active=True,receive_notifications=True).first() is not None)
    if not required:
        return False
    with _capability_lock:
        valid_until=_capabilities.get(webhook_url,0)
    if valid_until < time.monotonic():
        try:
            import requests
            response=requests.get(webhook_url,timeout=(5,10))
            if response.status_code!=200 or response.json().get('notification_protocol')!='tagluxe-email-v2':
                raise ValueError('Unsupported notification protocol')
        except Exception:
            raise RuntimeError('Cần cập nhật và triển khai Apps Script hỗ trợ tagluxe-email-v2 trước khi gửi tới danh sách email mới.') from None
        with _capability_lock:
            _capabilities[webhook_url]=time.monotonic()+300
    return True
