"""Private CRM and per-quote follow-up workflow."""
from backend.time_utils import vietnam_now
from datetime import date
from flask import render_template, request, redirect, url_for, flash, session, abort
from sqlalchemy import or_, func, case
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.database import db
from backend.models import Quote, QuoteAdminState, AuditLog, CustomerProfile
from backend.admin.routes import admin_bp, login_required, validate_csrf, QUOTE_STATUSES
from backend.admin.workspace_services import PRIORITIES, page_number, local_today
from backend.services.customer_cleanup import quote_set_fingerprint, delete_quote_records
from backend.admin.customer_services import (SOURCES, CUSTOMER_STATUSES, INACTIVE_STATUSES,
    clean_customer, customer_list)


@admin_bp.route('/quotes/<id>', methods=['GET', 'POST'])
@login_required
def admin_quote_detail(id):
    quote = db.get_or_404(Quote, id)
    workflow = db.session.get(QuoteAdminState, id)
    form_values = None
    error_code = 200
    if request.method == 'POST':
        if not validate_csrf():
            abort(400, 'Phiên làm việc đã hết hạn. Vui lòng tải lại trang.')
        form_values = request.form
        notes = request.form.get('internal_notes', '').strip()
        owner = request.form.get('owner', '').strip()
        priority = request.form.get('priority', 'normal')
        follow_up = request.form.get('follow_up_on', '').strip()
        try:
            if len(notes) > 5000 or len(owner) > 80 or priority not in PRIORITIES:
                raise ValueError('Ghi chú tối đa 5.000 ký tự, người phụ trách tối đa 80 ký tự và mức ưu tiên phải hợp lệ.')
            day = date.fromisoformat(follow_up) if follow_up else None
            if day and not 2000 <= day.year <= 2100:
                raise ValueError('Ngày liên hệ cần nằm trong khoảng năm 2000–2100.')
            version = int(request.form.get('version', '-1'))
            if version < 0:
                raise ValueError('Thiếu phiên bản hồ sơ. Vui lòng tải lại trang.')
        except ValueError as exc:
            flash(str(exc) if str(exc).startswith(('Ghi chú', 'Ngày', 'Thiếu')) else 'Ngày liên hệ hoặc phiên bản không hợp lệ.', 'error')
            error_code = 400
        else:
            values = dict(internal_notes=notes, owner=owner, priority=priority, follow_up_on=day,
                          updated_at=vietnam_now(), updated_by=session['admin_username'])
            try:
                if workflow:
                    changed = QuoteAdminState.query.filter_by(quote_id=id, version=version).update(
                        dict(values, version=version + 1), synchronize_session=False)
                    if changed != 1:
                        raise IntegrityError('stale version', {}, None)
                elif version == 0:
                    db.session.add(QuoteAdminState(quote_id=id, version=1, **values))
                else:
                    raise IntegrityError('stale version', {}, None)
                db.session.add(AuditLog(admin_user=session['admin_username'], action='update_quote_workflow',
                    target_type='quote', target_id=id, details='Cập nhật ghi chú, phụ trách và lịch liên hệ',
                    ip_address=request.remote_addr))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('Hồ sơ đã được thay đổi ở phiên khác. Nội dung bạn nhập vẫn ở bên dưới; tải lại trang để đối chiếu trước khi lưu.', 'error')
                error_code = 409
            except SQLAlchemyError:
                db.session.rollback()
                flash('Chưa lưu được hồ sơ. Vui lòng thử lại.', 'error')
                error_code = 503
            else:
                flash('Đã lưu thông tin chăm sóc báo giá.', 'success')
                return redirect(url_for('admin.admin_quote_detail', id=id))
    logs = AuditLog.query.filter_by(target_type='quote', target_id=id).order_by(
        AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(20).all()
    return render_template('admin/quote_detail.html', quote=quote, workflow=workflow,
        form_values=form_values, priorities=PRIORITIES, logs=logs, statuses=QUOTE_STATUSES,
        today=local_today(), page_title=f'Báo giá {id}'), error_code


@admin_bp.route('/customers')
@login_required
def admin_customers():
    query, metrics, filters = customer_list(request.args)
    total = query.count()
    page = min(page_number(request.args), max(1, (total + 19) // 20))
    customers = query.offset((page - 1) * 20).limit(20).all()
    return render_template('admin/customers.html', customers=customers, metrics=metrics, filters=filters,
        sources=SOURCES, customer_statuses=CUSTOMER_STATUSES, today=local_today(),inactive_statuses=INACTIVE_STATUSES,
        total=total, page=page, pages=max(1, (total + 19) // 20), page_title='Khách hàng')


@admin_bp.route('/customers/new', methods=['GET','POST'])
@login_required
def admin_customer_new():
    return customer_form()


@admin_bp.route('/customers/<phone>/edit', methods=['GET','POST'])
@login_required
def admin_customer_edit(phone):
    profile = db.session.get(CustomerProfile,phone)
    latest = Quote.query.filter_by(phone=phone).order_by(Quote.created_at.desc(),Quote.id.desc()).first()
    if not profile and not latest:abort(404)
    return customer_form(phone,profile,latest)


def customer_form(phone=None,profile=None,latest=None):
    editing=phone is not None
    duplicate_phone=None
    values={key:getattr(profile,key) for key in ('customer_name','phone','source','status','company','email',
        'address','needs','notes','owner','needed_on','follow_up_on','version')} if profile else dict(
        customer_name=latest.customer_name if latest else '',phone=phone or '',source='website' if latest else 'zalo',
        status=('Đã chốt' if latest and latest.status in ('Đã chốt','Đã xong') else
                'Chưa chốt' if latest and latest.status=='Đã hủy' else 'Đang tư vấn'),version=0)
    for key in ('needed_on','follow_up_on'):
        values[key]=values[key].isoformat() if values.get(key) else ''
    status_code=200
    if request.method=='POST':
        if not validate_csrf():abort(400,'Phiên làm việc hết hạn. Hãy tải lại trang.')
        values=request.form.to_dict()
        try:
            clean=clean_customer(values)
            if editing and clean['phone']!=phone:
                raise ValueError('Số điện thoại là khóa ghép lịch sử. Không thay số trên hồ sơ này; hãy tạo khách khác nếu cần.')
            existing=db.session.get(CustomerProfile,clean['phone'])
            if not editing and existing:
                duplicate_phone=existing.phone
                raise ValueError('Số điện thoại này đã có hồ sơ. Mở hồ sơ có sẵn để cập nhật, tránh ghi đè thông tin.')
            try:version=int(values.get('version','-1'))
            except ValueError:raise ValueError('Phiên bản hồ sơ không hợp lệ. Vui lòng tải lại trang.')
            if version<0:raise ValueError('Thiếu phiên bản hồ sơ. Vui lòng tải lại trang.')
            now=vietnam_now()
            update=dict(clean,updated_at=now,updated_by=session['admin_username'])
            if profile:
                changed=CustomerProfile.query.filter_by(phone=phone,version=version).update(
                    dict(update,version=version+1),synchronize_session=False)
                if changed!=1:raise IntegrityError('stale customer',{},None)
            else:
                if version!=0:raise IntegrityError('stale customer',{},None)
                db.session.add(CustomerProfile(**update,created_at=now,version=1))
            db.session.add(AuditLog(admin_user=session['admin_username'],action='update_customer' if editing else 'create_customer',
                target_type='customer',target_id=quote_set_fingerprint([clean['phone']])[:16],
                details='Cập nhật hồ sơ khách hàng' if editing else 'Thêm hồ sơ khách hàng',ip_address=request.remote_addr))
            db.session.commit()
        except ValueError as error:
            db.session.rollback();flash(str(error),'error');status_code=409 if duplicate_phone else 400
        except IntegrityError:
            db.session.rollback();flash('Hồ sơ đã được lưu hoặc chỉnh ở phiên khác. Dữ liệu vừa nhập vẫn được giữ bên dưới. Hãy mở lại hồ sơ để đối chiếu.','error');status_code=409
        except SQLAlchemyError:
            db.session.rollback();flash('Chưa lưu được hồ sơ. Nội dung vừa nhập vẫn còn; vui lòng thử lại.','error');status_code=503
        else:
            flash('Đã lưu hồ sơ khách hàng. Lịch sử báo giá cùng số điện thoại được ghép tự động.','success')
            return redirect(url_for('admin.admin_customer_detail',phone=clean['phone']))
    return render_template('admin/customer_form.html',values=values,editing=editing,phone=phone,
        duplicate_phone=duplicate_phone,sources=SOURCES,customer_statuses=CUSTOMER_STATUSES,
        page_title='Chỉnh hồ sơ khách' if editing else 'Thêm khách hàng'),status_code


@admin_bp.route('/customers/<phone>')
@login_required
def admin_customer_detail(phone):
    query = Quote.query.filter_by(phone=phone)
    latest = query.order_by(Quote.created_at.desc(), Quote.id.desc()).first()
    profile = db.session.get(CustomerProfile,phone)
    if not latest and not profile:abort(404)
    customer=profile or latest
    from backend.admin.workspace_services import quote_summary
    summary = quote_summary(query)
    page = min(page_number(request.args), max(1, (summary['count'] + 19) // 20))
    quotes = query.order_by(Quote.created_at.desc(), Quote.id.desc()).offset((page - 1) * 20).limit(20).all()
    ids=[row[0] for row in query.with_entities(Quote.id).all()]
    closed_count=query.filter(Quote.status.in_(('Đã chốt','Đã xong'))).count()
    if profile:ids.append('profile:'+str(profile.version))
    return render_template('admin/customer_detail.html', customer=customer, profile=profile, quotes=quotes,
        summary=summary, page=page, pages=max(1, (summary['count'] + 19) // 20), page_title='Hồ sơ khách hàng',
        deletion_snapshot=quote_set_fingerprint(ids),closed_count=closed_count,sources=SOURCES,
        today=local_today(),inactive_statuses=INACTIVE_STATUSES)


@admin_bp.route('/customers/<phone>/delete',methods=['POST'])
@login_required
def admin_delete_customer(phone):
    import secrets
    if not validate_csrf():abort(400,'Phiên làm việc đã hết hạn. Vui lòng tải lại trang.')
    quotes=Quote.query.filter_by(phone=phone).with_for_update().all()
    profile=CustomerProfile.query.filter_by(phone=phone).with_for_update().first()
    if not quotes and not profile:abort(404)
    try:
        if request.form.get('confirm_delete')!='1' or request.form.get('confirm_phone','').strip()!=phone:
            raise ValueError('Cần nhập đúng số điện thoại và đánh dấu xác nhận trước khi xóa khách hàng.')
        ids=[q.id for q in quotes]
        if profile:ids.append('profile:'+str(profile.version))
        expected=quote_set_fingerprint(ids)
        supplied=request.form.get('deletion_snapshot','')
        if not secrets.compare_digest(supplied.encode('utf-8'),expected.encode('utf-8')):
            raise ValueError('Hồ sơ vừa có thay đổi. Hãy xem lại danh sách báo giá và xác nhận xóa lần nữa.')
        if any(q.status in ('Đã chốt','Đã xong') for q in quotes) and request.form.get('confirm_closed')!='1':
            raise ValueError('Khách này có báo giá đã chốt hoặc đã xong. Cần xác nhận riêng trước khi xóa.')
        count=delete_quote_records(quotes,session['admin_username'])
        if profile:db.session.delete(profile)
        db.session.add(AuditLog(admin_user=session['admin_username'],action='delete_customer',
            target_type='customer',target_id=quote_set_fingerprint([phone])[:16],
            details='Xóa hồ sơ khách cùng '+str(count)+' báo giá và thông tin chăm sóc liên quan.'))
        db.session.commit()
        flash('Đã xóa khách hàng cùng '+str(count)+' báo giá trên web. Bản lưu trong bảng tính được giữ riêng.','success')
        return redirect(url_for('admin.admin_customers'))
    except ValueError as error:
        db.session.rollback();flash(str(error),'error')
    except SQLAlchemyError:
        db.session.rollback();flash('Chưa xóa được hồ sơ. Dữ liệu được giữ nguyên; vui lòng thử lại.','error')
    return redirect(url_for('admin.admin_customer_detail',phone=phone))
