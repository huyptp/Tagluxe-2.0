import os
import re
import time
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from core.config import UPLOAD_REQUESTS_FOLDER, allowed_request_file
from core.services.data_service import (
    add_demo_request, add_quote, calculate_lanyard_price, 
    calculate_product_price, get_pvc_pricing_matrix, get_holder_pricing_matrix
)
from core.security import rate_limit, idempotency

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/pricing/pvc', methods=['GET'])
def api_get_pvc_pricing():
    """Trả về toàn bộ ma trận bảng giá Thẻ Nhựa PVC theo kích thước và số lượng"""
    return jsonify({
        'success': True,
        'data': get_pvc_pricing_matrix()
    })

@api_bp.route('/pricing/holder', methods=['GET'])
def api_get_holder_pricing():
    """Trả về toàn bộ bảng giá Vỏ đựng thẻ nhựa ABS theo số lượng"""
    return jsonify({
        'success': True,
        'data': get_holder_pricing_matrix()
    })

@api_bp.route('/request-demo', methods=['POST'])
@rate_limit(limit=5, window_sec=60, error_message='Bạn gửi yêu cầu quá thường xuyên. Vui lòng đợi 1 phút trước khi gửi tiếp.')
def api_request_demo():
    phone = (request.form.get('phone') or '').strip()
    if not phone:
        return jsonify({'success': False, 'message': 'Vui lòng cung cấp số điện thoại hoặc Zalo.'}), 400

    customer_name = (request.form.get('customer_name') or '').strip()
    product_category = request.form.get('product_category') or 'lanyard'
    quantity_range = request.form.get('quantity_range') or '10-20'
    notes = (request.form.get('notes') or '').strip()

    # Idempotency check: detect identical duplicate requests within 30s
    idemp_key = idempotency.generate_key('demo', phone, product_category, quantity_range, notes)
    cached_result = idempotency.get_existing(idemp_key)
    if cached_result:
        return jsonify(cached_result), 200

    file_path = None
    original_filename = None
    if 'logo_file' in request.files:
        file = request.files['logo_file']
        if file and file.filename != '':
            if allowed_request_file(file.filename):
                clean_name = secure_filename(file.filename)
                unique_name = f"req_{int(time.time())}_{uuid.uuid4().hex[:6]}_{clean_name}"
                save_dest = os.path.join(UPLOAD_REQUESTS_FOLDER, unique_name)
                file.save(save_dest)
                file_path = unique_name
                original_filename = file.filename
            else:
                return jsonify({'success': False, 'message': 'Định dạng file không hỗ trợ. Vui lòng tải file ảnh, PDF, AI, PSD hoặc ZIP.'}), 400

    new_req = add_demo_request(
        phone=phone,
        customer_name=customer_name,
        product_category=product_category,
        quantity_range=quantity_range,
        notes=notes,
        file_path=file_path,
        original_filename=original_filename
    )

    result = {'success': True, 'request_id': new_req['id'], 'phone': phone}
    idempotency.store(idemp_key, result)
    return jsonify(result)


@api_bp.route('/calculate-price', methods=['POST'])
def api_calculate_price():
    data = request.get_json(silent=True) or request.form
    category = data.get('category', 'lanyard')
    quantity = data.get('quantity', 10)
    width = data.get('width', '2.0')
    accessories = data.get('accessories', [])
    if isinstance(accessories, str) and accessories:
        accessories = [a.strip() for a in accessories.split(',') if a.strip()]

    include_vat = bool(data.get('include_vat', False) or data.get('vat', False))
    result = calculate_product_price(
        category=category,
        quantity=quantity,
        width=width,
        accessories=accessories,
        finish=data.get('finish', 'matte'),
        effects=data.get('effects', []),
        orientation=data.get('orientation', 'vertical'),
        printed_logo=data.get('printed_logo'),
        holder_type=data.get('holder_type') or data.get('material'),
        include_vat=include_vat,
        size=data.get('size') or width,
        punched_hole=data.get('punched_hole', False)
    )
    return jsonify({'success': True, 'data': result})


@api_bp.route('/submit-quote', methods=['POST'])
@rate_limit(limit=10, window_sec=60, error_message='Bạn thao tác quá nhanh. Vui lòng chờ giây lát trước khi gửi báo giá tiếp theo.')
def api_submit_quote():
    data = request.get_json(silent=True) or request.form
    customer_name = (data.get('customer_name') or '').strip()
    raw_phone = (data.get('phone') or '').strip()
    raw_quantity = data.get('quantity')
    category = data.get('category', 'lanyard')
    width = data.get('width', '2.0')
    accessories = data.get('accessories', [])
    notes = (data.get('notes') or '').strip()
    include_vat = bool(data.get('include_vat', False) or data.get('vat', False))

    # 1. Validate customer name
    if not customer_name:
        return jsonify({'success': False, 'message': 'Vui lòng nhập họ và tên của bạn.'}), 400

    # 2. Validate Vietnamese phone number
    clean_phone = re.sub(r'[\s\.\-\(\)]', '', raw_phone)
    if clean_phone.startswith('+84'):
        clean_phone = '0' + clean_phone[3:]
    elif clean_phone.startswith('84') and len(clean_phone) == 11:
        clean_phone = '0' + clean_phone[2:]

    if not re.match(r'^0[1-9]\d{8}$', clean_phone):
        return jsonify({'success': False, 'message': 'Số điện thoại không hợp lệ. Vui lòng nhập số điện thoại gồm 10 chữ số (VD: 0912345678).'}), 400

    # 3. Validate quantity
    min_qty = 20 if category in ['holder', 'vo'] else 10
    try:
        quantity = int(raw_quantity)
        if quantity < min_qty:
            item_name = "vỏ đựng thẻ " if min_qty == 20 else ""
            return jsonify({'success': False, 'message': f'Số lượng đặt in {item_name}tối thiểu là {min_qty} cái.'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': f'Số lượng phải là một số nguyên hợp lệ (tối thiểu {min_qty}).'}), 400

    if isinstance(accessories, str) and accessories:
        accessories = [a.strip() for a in accessories.split(',') if a.strip()]

    # 4. Idempotency check: prevent duplicate submissions within 30s
    idemp_key = idempotency.generate_key('quote', clean_phone, category, quantity, width, str(accessories), notes)
    cached_resp = idempotency.get_existing(idemp_key)
    if cached_resp:
        return jsonify(cached_resp), 200

    quote_record = add_quote(
        customer_name=customer_name,
        phone=clean_phone,
        quantity=quantity,
        category=category,
        width=width,
        accessories=accessories,
        notes=notes,
        finish=data.get('finish', 'matte'),
        effects=data.get('effects', []),
        orientation=data.get('orientation', 'vertical'),
        printed_logo=data.get('printed_logo'),
        holder_type=data.get('holder_type') or data.get('material'),
        include_vat=include_vat,
        size=data.get('size') or width,
        punched_hole=data.get('punched_hole', False)
    )

    response_data = {
        'success': True,
        'message': 'Gửi yêu cầu tư vấn & in ấn thành công! TagLuxe sẽ liên hệ hỗ trợ bạn sớm nhất.',
        'quote': quote_record
    }
    idempotency.store(idemp_key, response_data)

    return jsonify(response_data)



