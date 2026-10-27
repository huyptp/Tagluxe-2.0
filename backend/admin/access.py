"""Server-side admin identity, revocation and least-privilege role presets."""
import secrets
from flask import current_app, g, session, request, redirect, url_for, abort
from werkzeug.security import check_password_hash
from backend.database import db
from backend.models import AdminUser, SiteSetting
from backend.config import ADMIN_USERNAME

ROLE_LABELS = {'manager':'Quản lý vận hành', 'sales':'Tư vấn khách hàng', 'content':'Nội dung & hình ảnh'}
ROLE_PERMISSIONS = {'manager':{'quotes','catalog','pricing','content'},
                    'sales':{'quotes'}, 'content':{'catalog','content'}}
OWNER_ONLY = {'admin_staff','admin_staff_edit','admin_notifications','admin_notification_edit',
              'admin_system','admin_migration_backup','admin_restore_sheet_quotes','admin_activity',
              'admin_export_quotes','admin_delete_quote','admin_delete_customer','admin_delete_product','admin_delete_accessory'}


def epoch_matches(value, expected):
    return isinstance(value,str) and secrets.compare_digest(value.encode('utf-8'),expected.encode('utf-8'))


def owner_epoch():
    row = db.session.get(SiteSetting, '_owner_session_epoch')
    if not row:
        # Atomic insert: concurrent owner logins must not invalidate one another.
        from sqlalchemy.exc import IntegrityError
        row = SiteSetting(key='_owner_session_epoch',value_json=secrets.token_urlsafe(32))
        db.session.add(row)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            row = db.session.get(SiteSetting, '_owner_session_epoch')
    return row.value_json


def staff_credentials(username, password):
    user = AdminUser.query.filter_by(username=username.casefold()).first()
    # Run a password hash even for unknown usernames to reduce account probing.
    from werkzeug.security import generate_password_hash
    dummy = getattr(staff_credentials, '_dummy', None)
    if dummy is None:
        dummy = staff_credentials._dummy = generate_password_hash(secrets.token_urlsafe(32))
    valid = check_password_hash(user.password_hash if user else dummy, password)
    return user if user and valid and user.active and user.role in ROLE_PERMISSIONS else None


def start_admin_session(user=None):
    session.clear()
    session.update(logged_in=True, _admin_csrf_token=secrets.token_hex(24))
    if user:
        session.update(_auth_kind='staff', staff_user_id=user.id, _auth_epoch=user.auth_epoch,
                       admin_username=user.username)
    else:
        session.update(_auth_kind='owner', _auth_epoch=owner_epoch(), admin_username=ADMIN_USERNAME)


def load_identity():
    g.admin_identity = None
    if not session.get('logged_in'):
        return
    kind = session.get('_auth_kind')
    if kind == 'staff':
        uid = session.get('staff_user_id')
        user = db.session.get(AdminUser, uid) if type(uid) is int else None
        if user and user.active and user.role in ROLE_PERMISSIONS and epoch_matches(
                session.get('_auth_epoch',''),user.auth_epoch):
            g.admin_identity = {'owner':False,'name':user.display_name,'username':user.username,
                                'role':user.role,'user':user,'permissions':ROLE_PERMISSIONS[user.role]}
    elif kind == 'owner':
        row = db.session.get(SiteSetting, '_owner_session_epoch')
        if row and epoch_matches(session.get('_auth_epoch',''),row.value_json):
            g.admin_identity = {'owner':True,'name':'Chủ shop','username':ADMIN_USERNAME,'role':'owner','permissions':set()}
    elif current_app.testing:
        # Historical test fixtures only; production sessions must carry a DB seal.
        g.admin_identity = {'owner':True,'name':'Chủ shop','username':ADMIN_USERNAME,'role':'owner','permissions':set()}
    if g.admin_identity:
        session['admin_username'] = g.admin_identity['username']
    else:
        session.clear()


def can_access(endpoint):
    identity = getattr(g,'admin_identity',None)
    if not identity:
        return False
    if identity['owner']:
        return True
    name = (endpoint or '').split('.')[-1]
    if name in OWNER_ONLY:
        return False
    if name in ('admin_logout','admin_account_password'):
        return True
    if name == 'admin_dashboard':
        return 'quotes' in identity['permissions']
    if name.startswith(('admin_quote','admin_bulk_quote','admin_update_quote','admin_retry_quote','admin_customer')):
        return 'quotes' in identity['permissions']
    if name in ('admin_accessories','admin_update_pricing'):
        return 'pricing' in identity['permissions']
    if 'accessory' in name:
        return 'pricing' in identity['permissions']
    if name.startswith(('admin_product','admin_add_product','admin_edit_product','admin_update_product','admin_delete_product')):
        return 'catalog' in identity['permissions']
    if any(term in name for term in ('demo_image','campaign_banner')):
        return 'content' in identity['permissions']
    return False


def landing_endpoint():
    return 'admin.admin_dashboard' if can_access('admin.admin_dashboard') else 'admin.admin_products'


def enforce_admin_access():
    if request.endpoint == 'admin.static':
        return
    load_identity()
    if request.endpoint == 'admin.admin_login':
        return
    if not g.admin_identity:
        return redirect(url_for('admin.admin_login'))
    if not can_access(request.endpoint):
        abort(403)
