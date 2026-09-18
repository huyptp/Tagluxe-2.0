import os
import time
from flask import Blueprint, request, jsonify
from backend.services.data_service import (
    add_demo_request, add_quote,
    calculate_product_price, get_pvc_pricing_matrix, get_holder_pricing_matrix
)
from backend.security import rate_limit, idempotency
from backend.validators import validate_quote_input, validate_demo_input, ALLOWED_CATEGORIES, parse_bool

api_bp = Blueprint('api', __name__, url_prefix='/api')

def _extract_request_data(req):
    """
    Safely extracts dict payload from request, handling JSON or Form data.
    Returns (data: dict | None, is_valid_structure: bool)
    """
    if req.is_json:
        parsed = req.get_json(silent=True)
        if parsed is None or not isinstance(parsed, dict):
            return None, False
        return parsed, True
    elif req.form:
        return req.form.to_dict(), True
    else:
        # Check if there is an empty body or json attempt
        raw = req.get_json(silent=True)
        if raw is not None:
            if not isinstance(raw, dict):
                return None, False
            return raw, True
        return {}, True

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
    has_files = bool(request.files and len(request.files) > 0)
    data, is_valid_structure = _extract_request_data(request)
    if not is_valid_structure:
        return jsonify({
            'success': False,
            'message': 'Dữ liệu gửi lên phải là một đối tượng JSON hợp lệ (Object).'
        }), 400

    is_valid, err_msg, status_code, clean_data = validate_demo_input(data, has_files=has_files)
    if not is_valid:
        return jsonify({'success': False, 'message': err_msg}), status_code

    # Idempotency check: detect duplicate requests within 30s
    idemp_key = idempotency.generate_key(
        'demo', clean_data['phone'], clean_data['customer_name'],
        clean_data['product_category'], clean_data['quantity_range'], clean_data['notes']
    )
    cached_result = idempotency.get_existing(idemp_key)
    if cached_result:
        return jsonify(cached_result), 200

    new_req = add_demo_request(
        phone=clean_data['phone'],
        customer_name=clean_data['customer_name'],
        product_category=clean_data['product_category'],
        quantity_range=clean_data['quantity_range'],
        notes=clean_data['notes'],
        file_path=None,
        original_filename=None
    )

    if not new_req:
        return jsonify({
            'success': False,
            'message': 'Không thể lưu yêu cầu thiết kế vào hệ thống lúc này. Vui lòng thử lại sau giây lát.'
        }), 500

    result = {'success': True, 'request_id': new_req['id'], 'phone': clean_data['phone']}
    idempotency.store(idemp_key, result)
    return jsonify(result)

@api_bp.route('/calculate-price', methods=['POST'])
def api_calculate_price():
    data, is_valid_structure = _extract_request_data(request)
    if not is_valid_structure:
        return jsonify({
            'success': False,
            'message': 'Dữ liệu gửi lên phải là một đối tượng JSON hợp lệ (Object).'
        }), 400

    is_valid, err_msg, status_code, clean_data = validate_quote_input(data, is_submission=False)
    if not is_valid:
        return jsonify({'success': False, 'message': err_msg}), status_code

    result = calculate_product_price(
        category=clean_data['category'],
        quantity=clean_data['quantity'],
        width=clean_data['width'],
        accessories=clean_data['accessories'],
        finish=clean_data['finish'],
        effects=clean_data['effects'],
        orientation=clean_data['orientation'],
        printed_logo=clean_data['printed_logo'],
        holder_type=clean_data['holder_type'],
        include_vat=clean_data['include_vat'],
        size=clean_data['size'],
        punched_hole=clean_data['punched_hole']
    )
    return jsonify({'success': True, 'data': result})

@api_bp.route('/submit-quote', methods=['POST'])
@rate_limit(limit=10, window_sec=60, error_message='Bạn thao tác quá nhanh. Vui lòng chờ giây lát trước khi gửi báo giá tiếp theo.')
def api_submit_quote():
    data, is_valid_structure = _extract_request_data(request)
    if not is_valid_structure:
        return jsonify({
            'success': False,
            'message': 'Dữ liệu gửi lên phải là một đối tượng JSON hợp lệ (Object).'
        }), 400

    is_valid, err_msg, status_code, clean_data = validate_quote_input(data, is_submission=True)
    if not is_valid:
        return jsonify({'success': False, 'message': err_msg}), status_code

    # Idempotency check: include all pricing parameters in hash key
    idemp_key = idempotency.generate_key(
        'quote', clean_data['phone'], clean_data['category'], clean_data['quantity'],
        clean_data['width'], str(clean_data['accessories']),
        str(clean_data['include_vat']), str(clean_data['finish']),
        str(clean_data['effects']), str(clean_data['size']),
        str(clean_data['holder_type']), str(clean_data['punched_hole']),
        clean_data['notes']
    )
    cached_resp = idempotency.get_existing(idemp_key)
    if cached_resp:
        return jsonify(cached_resp), 200

    quote_record = add_quote(
        customer_name=clean_data['customer_name'],
        phone=clean_data['phone'],
        quantity=clean_data['quantity'],
        category=clean_data['category'],
        width=clean_data['width'],
        accessories=clean_data['accessories'],
        notes=clean_data['notes'],
        finish=clean_data['finish'],
        effects=clean_data['effects'],
        orientation=clean_data['orientation'],
        printed_logo=clean_data['printed_logo'],
        holder_type=clean_data['holder_type'],
        include_vat=clean_data['include_vat'],
        size=clean_data['size'],
        punched_hole=clean_data['punched_hole']
    )

    if not quote_record:
        return jsonify({
            'success': False,
            'message': 'Không thể lưu yêu cầu báo giá vào hệ thống lúc này. Vui lòng thử lại sau giây lát.'
        }), 500

    response_data = {
        'success': True,
        'message': 'Gửi yêu cầu tư vấn & in ấn thành công! TagLuxe sẽ liên hệ hỗ trợ bạn sớm nhất.',
        'quote': quote_record
    }
    idempotency.store(idemp_key, response_data)

    return jsonify(response_data)



