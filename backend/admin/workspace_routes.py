"""Private CRM and per-quote follow-up workflow."""
from backend.time_utils import vietnam_now
from datetime import date
from flask import render_template, request, redirect, url_for, flash, session, abort
from sqlalchemy import or_, func, case
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.database import db
from backend.models import Quote, QuoteAdminState, AuditLog
from backend.admin.routes import admin_bp, login_required, validate_csrf, QUOTE_STATUSES
from backend.admin.workspace_services import PRIORITIES, page_number, local_today


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
    search = request.args.get('q', '').strip()[:200]
    sort = request.args.get('sort', 'recent')
    # Aggregate before filtering so searching one name retains all of that phone's history.
    groups = db.session.query(
        Quote.phone.label('phone'), func.max(Quote.customer_name).label('name'),
        func.count(Quote.id).label('quote_count'), func.max(Quote.created_at).label('last_contact'),
        func.sum(case((Quote.status != 'Đã hủy', Quote.total_price), else_=0)).label('value'),
        func.sum(case((Quote.status.in_(('Đã chốt', 'Đã xong')), Quote.total_price), else_=0)).label('closed_value')
    ).filter(Quote.phone != '').group_by(Quote.phone).subquery()
    query = db.session.query(groups)
    if search:
        matching_phones = db.session.query(Quote.phone).filter(
            Quote.customer_name.icontains(search, autoescape=True))
        query = query.filter(or_(groups.c.phone.contains(search, autoescape=True), groups.c.phone.in_(matching_phones)))
    order = {'value': groups.c.value.desc(), 'count': groups.c.quote_count.desc()}.get(sort, groups.c.last_contact.desc())
    query = query.order_by(order, groups.c.phone)
    total = query.count()
    page = min(page_number(request.args), max(1, (total + 19) // 20))
    customers = query.offset((page - 1) * 20).limit(20).all()
    return render_template('admin/customers.html', customers=customers, search_query=search,
        sort=sort, total=total, page=page, pages=max(1, (total + 19) // 20), page_title='Khách hàng')


@admin_bp.route('/customers/<phone>')
@login_required
def admin_customer_detail(phone):
    query = Quote.query.filter_by(phone=phone)
    latest = query.order_by(Quote.created_at.desc(), Quote.id.desc()).first_or_404()
    from backend.admin.workspace_services import quote_summary
    summary = quote_summary(query)
    page = min(page_number(request.args), max(1, (summary['count'] + 19) // 20))
    quotes = query.order_by(Quote.created_at.desc(), Quote.id.desc()).offset((page - 1) * 20).limit(20).all()
    return render_template('admin/customer_detail.html', customer=latest, quotes=quotes,
        summary=summary, page=page, pages=max(1, (summary['count'] + 19) // 20), page_title='Hồ sơ khách hàng')
