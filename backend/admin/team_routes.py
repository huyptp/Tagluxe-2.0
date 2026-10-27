"""Owner controls staff access and email destinations. No emails sent on save."""
import re
import secrets
import uuid
from flask import render_template, request, redirect, url_for, flash, abort, g, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.admin.routes import admin_bp, login_required, validate_csrf, record_audit
from backend.admin.access import ROLE_LABELS
from backend.database import db
from backend.models import AdminUser
from backend.config import ADMIN_USERNAME
from backend.time_utils import vietnam_now
from backend.services.notification_settings import clean_email, manual_recipients, notification_recipients
from backend.services.settings_storage import write_setting


def require_form_token():
    if not validate_csrf():
        abort(400,'Phiên làm việc đã hết hạn. Vui lòng tải lại trang.')


def staff_values(form):
    name=form.get('display_name','').strip()
    role=form.get('role','sales')
    email=form.get('email','').strip()
    receive=form.get('receive_notifications')=='1'
    if not name or len(name)>100 or role not in ROLE_LABELS:
        raise ValueError('Nhập tên nhân viên tối đa 100 ký tự và chọn quyền hợp lệ.')
    email=clean_email(email) if email else ''
    if receive and not email:
        raise ValueError('Cần nhập email trước khi bật nhận thông báo.')
    return dict(display_name=name,role=role,email=email,receive_notifications=receive)


def password_hash(value):
    if not 12<=len(value)<=200:
        raise ValueError('Mật khẩu cần từ 12 đến 200 ký tự.')
    return generate_password_hash(value)


@admin_bp.route('/staff',methods=['GET','POST'])
@login_required
def admin_staff():
    if request.method=='POST':
        require_form_token()
        try:
            username=request.form.get('username','').strip().casefold()
            if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{2,49}',username) or username==ADMIN_USERNAME.casefold():
                raise ValueError('Tên đăng nhập từ 3–50 ký tự: chữ thường, số, dấu chấm, gạch ngang; không trùng chủ shop.')
            if AdminUser.query.count()>=50:
                raise ValueError('Tối đa 50 tài khoản nhân viên. Có thể khóa tài khoản ngừng sử dụng.')
            user=AdminUser(username=username,password_hash=password_hash(request.form.get('password','')),**staff_values(request.form))
            db.session.add(user);db.session.flush()
            notification_recipients()
            db.session.commit()
            record_audit('create_staff','staff',user.id,'Tạo tài khoản '+username+' · quyền '+user.role)
            flash('Đã tạo tài khoản nhân viên. Bạn gửi tên đăng nhập và mật khẩu riêng cho nhân viên.','success')
        except ValueError as error:
            db.session.rollback();flash(str(error),'error')
        except IntegrityError:
            db.session.rollback();flash('Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.','error')
        except SQLAlchemyError:
            db.session.rollback();flash('Chưa lưu được tài khoản. Vui lòng thử lại.','error')
        return redirect(url_for('admin.admin_staff'))
    return render_template('admin/staff.html',users=AdminUser.query.order_by(AdminUser.active.desc(),AdminUser.username).all(),roles=ROLE_LABELS,owner_username=ADMIN_USERNAME)


@admin_bp.route('/staff/<int:user_id>',methods=['POST'])
@login_required
def admin_staff_edit(user_id):
    require_form_token()
    user=db.get_or_404(AdminUser,user_id)
    try:
        action=request.form.get('action','update')
        if action=='toggle':
            user.active=not user.active
        elif action=='update':
            for key,value in staff_values(request.form).items():setattr(user,key,value)
            new_password=request.form.get('password','')
            if new_password:user.password_hash=password_hash(new_password)
        else:raise ValueError('Thao tác không hợp lệ.')
        user.auth_epoch=secrets.token_urlsafe(32)
        user.updated_at=vietnam_now()
        db.session.flush();notification_recipients();db.session.commit()
        record_audit('update_staff','staff',user.id,'Cập nhật '+user.username+' · quyền '+user.role+' · hoạt động '+str(user.active))
        flash('Đã cập nhật. Những phiên đăng nhập cũ của nhân viên cần đăng nhập lại.','success')
    except ValueError as error:
        db.session.rollback();flash(str(error),'error')
    except SQLAlchemyError:
        db.session.rollback();flash('Chưa lưu được thay đổi. Vui lòng thử lại.','error')
    return redirect(url_for('admin.admin_staff'))


@admin_bp.route('/notifications',methods=['GET','POST'])
@login_required
def admin_notifications():
    if request.method=='POST':
        require_form_token()
        try:
            records=manual_recipients()
            email=clean_email(request.form.get('email',''))
            name=request.form.get('name','').strip()
            if not name or len(name)>100:raise ValueError('Nhập tên người nhận tối đa 100 ký tự.')
            if any(r['email'].casefold()==email for r in records):raise ValueError('Email này đã có trong danh sách người nhận thêm.')
            if len(records)>=30:raise ValueError('Tối đa 30 người nhận thêm; có thể xóa người không còn sử dụng.')
            records.append({'id':uuid.uuid4().hex,'name':name,'email':email,'enabled':True})
            save_recipients(records)
            record_audit('notification_recipient_add','setting','notifications','Thêm người nhận '+name)
            flash('Đã thêm email nhận thông báo. Không gửi thư thử khi lưu.','success')
        except ValueError as error:flash(str(error),'error')
        return redirect(url_for('admin.admin_notifications'))
    manual=manual_recipients()
    staff=AdminUser.query.filter_by(active=True,receive_notifications=True).order_by(AdminUser.username).all()
    return render_template('admin/notifications.html',recipients=manual,staff_recipients=staff,active_count=len(notification_recipients()))


def save_recipients(records):
    enabled={clean_email(r['email']) for r in records if r.get('enabled')}
    enabled.update(clean_email(u.email) for u in AdminUser.query.filter_by(active=True,receive_notifications=True).all())
    if len(enabled)>20:raise ValueError('Tối đa 20 email đang bật nhận thông báo, tính cả nhân viên.')
    write_setting('notifications',{'recipients':records})


@admin_bp.route('/notifications/<recipient_id>',methods=['POST'])
@login_required
def admin_notification_edit(recipient_id):
    require_form_token()
    records=manual_recipients()
    match=next((r for r in records if r['id']==recipient_id),None)
    if not match:abort(404)
    action=request.form.get('action')
    try:
        if action=='toggle':match['enabled']=not match.get('enabled')
        elif action=='remove':records=[r for r in records if r['id']!=recipient_id]
        else:raise ValueError('Thao tác không hợp lệ.')
        save_recipients(records)
        record_audit('notification_recipient_'+action,'setting','notifications','Cập nhật người nhận thông báo')
        flash('Đã lưu danh sách người nhận.','success')
    except ValueError as error:flash(str(error),'error')
    return redirect(url_for('admin.admin_notifications'))


@admin_bp.route('/account/password',methods=['GET','POST'])
@login_required
def admin_account_password():
    if g.admin_identity['owner']:
        return render_template('admin/account_password.html',owner=True)
    if request.method=='POST':
        require_form_token()
        user=g.admin_identity['user']
        try:
            if not check_password_hash(user.password_hash,request.form.get('current_password','')):
                raise ValueError('Mật khẩu hiện tại chưa đúng.')
            new=request.form.get('new_password','')
            if new!=request.form.get('confirm_password',''):raise ValueError('Hai lần nhập mật khẩu mới chưa khớp.')
            user.password_hash=password_hash(new);user.auth_epoch=secrets.token_urlsafe(32);user.updated_at=vietnam_now()
            db.session.commit();session['_auth_epoch']=user.auth_epoch
            record_audit('change_own_password','staff',user.id,'Nhân viên đổi mật khẩu cá nhân')
            flash('Đã đổi mật khẩu. Các phiên đăng nhập khác của bạn đã hết hiệu lực.','success')
            return redirect(url_for('admin.admin_account_password'))
        except ValueError as error:flash(str(error),'error')
    return render_template('admin/account_password.html',owner=False)


@admin_bp.errorhandler(403)
def admin_forbidden(error):
    return render_template('admin/forbidden.html'),403
