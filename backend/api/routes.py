import os
import time
from flask import Blueprint, request, jsonify
from backend.services.data_service import (
    add_demo_request, add_quote,
    calculate_product_price, get_pvc_pricing_matrix, get_holder_pricing_matrix,
    create_quote_with_idempotency, create_demo_with_idempotency
)
from backend.security import rate_limit, idempotency, generate_canonical_hash
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

    request_id = request.headers.get('X-Request-ID') or data.get('request_id')
    content_hash = generate_canonical_hash(clean_data)
    idemp_key = idempotency.generate_key('demo', request_id=request_id, content_hash=content_hash)

    status_code, resp = create_demo_with_idempotency(clean_data, idemp_key, request_id, content_hash)
    return jsonify(resp), status_code

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

    request_id = request.headers.get('X-Request-ID') or data.get('request_id')
    content_hash = generate_canonical_hash(clean_data)
    idemp_key = idempotency.generate_key('quote', request_id=request_id, content_hash=content_hash)

    status_code, resp = create_quote_with_idempotency(clean_data, idemp_key, request_id, content_hash)
    return jsonify(resp), status_code



