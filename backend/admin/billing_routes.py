"""Authenticated print bills; bank configuration is owner-only."""
from flask import render_template, request, redirect, url_for, flash, abort, Response
from sqlalchemy.exc import SQLAlchemyError
from backend.database import db
from backend.models import Quote
from backend.time_utils import vietnam_now
from backend.admin.routes import admin_bp, login_required, validate_csrf, record_audit
from backend.services.settings_storage import read_setting, write_setting
from backend.services.billing import (banks, validate_payment_settings, payment_settings,
                                      payment_reference, vietqr_payload, qr_svg)


@admin_bp.route('/payments', methods=['GET', 'POST'])
@login_required
def admin_payments():
    saved = read_setting('payments')
    values = saved
    status = 200
    if request.method == 'POST':
        if not validate_csrf():
            abort(400)
        values = request.form
        try:
            clean = validate_payment_settings(values)
            if (saved.get('source_qr') and clean['source_qr'] == saved['source_qr'] and
                    any(clean[k] != saved.get(k) for k in ('bank_bin','account_number','account_name'))):
                raise ValueError('Khi đổi tài khoản nhận tiền, hãy xóa hoặc thay QR gốc để tránh dùng nhầm tài khoản.')
            write_setting('payments', clean)
        except ValueError as exc:
            flash(str(exc), 'error')
            status = 400
        except SQLAlchemyError:
            db.session.rollback()
            flash('Chưa lưu được tài khoản nhận tiền. Vui lòng thử lại.', 'error')
            status = 503
        else:
            record_audit('update_payments', 'setting', 'payments', 'Cập nhật cấu hình nhận tiền trên bill')
            flash('Đã lưu tài khoản nhận tiền. Bill mới sẽ sử dụng cấu hình này.', 'success')
            return redirect(url_for('admin.admin_payments'))
    return render_template('admin/payments.html', values=values, banks=banks(),
                           page_title='Thanh toán & in bill'), status


def bill_data(id):
    quote = db.get_or_404(Quote, id)
    settings = payment_settings()
    error = None
    payload = None
    reference = ''
    try:
        reference = payment_reference(quote.id)
        if quote.status == 'Đã hủy':
            raise ValueError('Báo giá đã hủy. Không tạo QR yêu cầu thanh toán.')
        if not settings:
            raise ValueError('Chủ shop cần cấu hình tài khoản nhận tiền trước khi tạo QR.')
        payload = vietqr_payload(settings, quote.total_price, reference)
    except ValueError as exc:
        error = str(exc)
    return quote, settings, reference, payload, error


@admin_bp.route('/quotes/<id>/bill')
@login_required
def admin_quote_bill(id):
    quote, settings, reference, payload, error = bill_data(id)
    return render_template('admin/bill.html', quote=quote, payment=settings,
                           reference=reference, has_qr=bool(payload), error=error,
                           printed_at=vietnam_now(), page_title=f'Bill {id}')


@admin_bp.route('/quotes/<id>/bill/qr.svg')
@login_required
def admin_quote_bill_qr(id):
    _, _, _, payload, error = bill_data(id)
    if error:
        abort(409, error)
    response = Response(qr_svg(payload), mimetype='image/svg+xml')
    response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response
