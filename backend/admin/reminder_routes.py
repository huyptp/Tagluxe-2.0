"""Owner settings and operational history for follow-up emails."""
import json
from datetime import datetime, timedelta
from flask import render_template,request,flash,url_for
from sqlalchemy.exc import SQLAlchemyError
from backend import config
from backend.database import db
from backend.models import FollowUpDelivery,SiteSetting
from backend.admin.routes import admin_bp,login_required,validate_csrf,record_audit
from backend.services import followup_reminders as reminders


def vietnam_label(value):
    return (value+timedelta(hours=7)).strftime('%d/%m/%Y %H:%M') if value else '—'


@admin_bp.route('/reminders',methods=['GET','POST'])
@login_required
def admin_reminders():
    values=reminders.settings()
    status=200
    if request.method=='POST':
        if not validate_csrf():
            flash('Phiên làm việc hết hạn. Vui lòng tải lại trang.','error');status=400
        else:
            try:
                values=reminders.save_settings(request.form)
            except ValueError as error:
                db.session.rollback();flash(str(error),'error');status=400
                values=dict(values,email=request.form.get('email',''),enabled=request.form.get('enabled')=='1')
            except SQLAlchemyError:
                db.session.rollback();flash('Chưa lưu được nhắc lịch. Vui lòng thử lại.','error');status=503
            else:
                record_audit('update_reminders','setting','followup_reminders','Cập nhật email và giờ nhắc lịch chăm sóc')
                flash('Đã lưu cài đặt nhắc lịch. Lịch chạy cần được kết nối trong Google Sheets.','success')
    health_row=db.session.get(SiteSetting,reminders.HEALTH_KEY)
    checked=None
    if health_row:
        try:checked=datetime.fromisoformat(json.loads(health_row.value_json)['checked_at'])
        except (ValueError,KeyError,TypeError):pass
    key=reminders.scheduler_key()
    connection=json.dumps({'url':config.site_origin()+'/api/internal/follow-up-reminders','key':key}) if key else ''
    return render_template('admin/reminders.html',values=values,connection=connection,
        checked=checked,connected=bool(checked and datetime.utcnow()-checked<timedelta(minutes=45)),
        deliveries=FollowUpDelivery.query.order_by(FollowUpDelivery.reminder_on.desc(),FollowUpDelivery.sent_at.desc()).limit(25).all(),
        reminder_labels=reminders.STATE_LABELS,vietnam_label=vietnam_label,page_title='Email nhắc liên hệ'),status
