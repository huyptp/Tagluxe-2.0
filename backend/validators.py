import re

ALLOWED_CATEGORIES = {'lanyard', 'pvc', 'pvc_5.4x8.6', 'pvc_7x11', 'pvc_9x12', 'holder', 'vo', 'combo'}
ALLOWED_FINISHES = {'matte', 'textured', 'glossy'}
ALLOWED_ORIENTATIONS = {'vertical', 'horizontal'}
ALLOWED_HOLE_TYPES = {'none', 'round', 'capsule'}

HOLE_TYPE_ALIASES = {
    'round': 'round',
    'tron': 'round',
    'tròn': 'round',
    'capsule': 'capsule',
    'oval': 'capsule',
    'nhong': 'capsule',
    'nhộng': 'capsule',
    'con_nhong': 'capsule',
    'none': 'none',
    'khong': 'none',
    'không': 'none',
    'false': 'none',
    '': 'none'
}

def parse_bool(val):
    """Safely parse boolean values avoiding Python's bool('false') == True trap"""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val == 1
    if isinstance(val, str):
        return val.strip().lower() in ('true', '1', 'yes', 'y', 'on')
    return False

def normalize_hole_type(raw_hole):
    """Normalizes punched_hole into strictly 'none', 'round', or 'capsule'"""
    if raw_hole is None or raw_hole is False:
        return 'none'
    if raw_hole is True:
        return 'round'
    
    clean = str(raw_hole).strip().lower()
    return HOLE_TYPE_ALIASES.get(clean, 'none')

def normalize_phone(raw_phone):
    """Normalizes and validates Vietnamese mobile phone number"""
    if not isinstance(raw_phone, str):
        return None
    clean = re.sub(r'[\s\.\-\(\)]', '', raw_phone)
    if clean.startswith('+84'):
        clean = '0' + clean[3:]
    elif clean.startswith('84') and len(clean) == 11:
        clean = '0' + clean[2:]
    
    if re.match(r'^0[1-9]\d{8}$', clean):
        return clean
    return None

def validate_quote_input(data, is_submission=False):
    """
    Shared validator for both price calculation and quote submission.
    Returns: (is_valid: bool, error_message: str | None, status_code: int, clean_data: dict | None)
    """
    if not isinstance(data, dict):
        return False, "Dữ liệu gửi lên phải là một đối tượng JSON hợp lệ (Object).", 400, None

    category = str(data.get('category', 'lanyard')).strip()
    if category not in ALLOWED_CATEGORIES:
        return False, f"Danh mục sản phẩm '{category}' không hợp lệ.", 400, None

    min_qty = 20 if category in ['holder', 'vo'] else 10
    raw_qty = data.get('quantity', 10)
    try:
        if isinstance(raw_qty, bool) or not isinstance(raw_qty, (int, float, str)):
            raise ValueError()
        quantity = int(raw_qty)
        if quantity < min_qty:
            item_name = "vỏ đựng thẻ " if min_qty == 20 else ""
            return False, f"Số lượng đặt in {item_name}tối thiểu là {min_qty} cái.", 400, None
        if quantity > 1000000:
            return False, "Số lượng đặt in vượt quá giới hạn hệ thống (tối đa 1.000.000 cái). Vui lòng liên hệ hotline để nhận báo giá dự án lớn.", 400, None
    except (ValueError, TypeError):
        return False, f"Số lượng phải là một số nguyên hợp lệ (tối thiểu {min_qty}).", 400, None

    clean_phone = ''
    customer_name = ''
    notes = ''

    if is_submission:
        raw_name = data.get('customer_name')
        if not isinstance(raw_name, str) or not raw_name.strip():
            return False, "Vui lòng nhập họ và tên của bạn.", 400, None
        customer_name = raw_name.strip()
        if len(customer_name) > 120:
            return False, "Họ và tên không được vượt quá 120 ký tự.", 400, None
        if not re.search(r'[a-zA-Z\u00C0-\u1EF9]', customer_name):
            return False, "Họ và tên không hợp lệ (phải chứa ít nhất một chữ cái).", 400, None

        raw_phone = data.get('phone')
        if not raw_phone:
            return False, "Vui lòng cung cấp số điện thoại liên hệ.", 400, None
        clean_phone = normalize_phone(str(raw_phone).strip())
        if not clean_phone:
            return False, "Số điện thoại không hợp lệ. Vui lòng nhập số điện thoại gồm 10 chữ số (VD: 0912345678).", 400, None

        raw_notes = data.get('notes', '')
        if raw_notes is not None:
            if not isinstance(raw_notes, str):
                raw_notes = str(raw_notes)
            notes = raw_notes.strip()
            if len(notes) > 1000:
                return False, "Ghi chú không được vượt quá 1000 ký tự.", 400, None

    raw_accs = data.get('accessories', [])
    if isinstance(raw_accs, str) and raw_accs:
        accessories = [a.strip() for a in raw_accs.split(',') if a.strip()]
    elif isinstance(raw_accs, list):
        accessories = [str(a).strip() for a in raw_accs if a]
    else:
        accessories = []

    punched_hole = normalize_hole_type(data.get('punched_hole'))
    include_vat = parse_bool(data.get('include_vat') or data.get('vat'))
    
    finish = str(data.get('finish', 'matte')).strip().lower()
    if finish not in ALLOWED_FINISHES:
        finish = 'matte'

    orientation = str(data.get('orientation', 'vertical')).strip().lower()
    if orientation not in ALLOWED_ORIENTATIONS:
        orientation = 'vertical'

    width = str(data.get('width', '2.0')).strip()
    size = str(data.get('size') or width).strip()
    holder_type = str(data.get('holder_type') or data.get('material') or '').strip()
    printed_logo = parse_bool(data.get('printed_logo', False))

    clean_data = {
        'customer_name': customer_name,
        'phone': clean_phone,
        'category': category,
        'quantity': quantity,
        'width': width,
        'size': size,
        'accessories': accessories,
        'notes': notes,
        'finish': finish,
        'orientation': orientation,
        'punched_hole': punched_hole,
        'include_vat': include_vat,
        'holder_type': holder_type,
        'printed_logo': printed_logo,
        'effects': data.get('effects', []) if isinstance(data.get('effects'), list) else []
    }

    return True, None, 200, clean_data

def validate_demo_input(data, has_files=False):
    """
    Validates input for /api/request-demo endpoint.
    Returns: (is_valid: bool, error_message: str | None, status_code: int, clean_data: dict | None)
    """
    if has_files:
        return False, "Hệ thống không nhận file tải lên qua biểu mẫu này. Vui lòng gửi file thiết kế trực tiếp qua Zalo hỗ trợ.", 400, None

    if not isinstance(data, dict):
        return False, "Dữ liệu gửi lên phải là một đối tượng JSON hợp lệ (Object).", 400, None

    raw_phone = data.get('phone')
    if not raw_phone:
        return False, "Vui lòng cung cấp số điện thoại hoặc Zalo.", 400, None

    clean_phone = normalize_phone(str(raw_phone).strip())
    if not clean_phone:
        return False, "Số điện thoại không hợp lệ. Vui lòng nhập số điện thoại gồm 10 chữ số (VD: 0912345678).", 400, None

    customer_name = str(data.get('customer_name') or '').strip()
    if customer_name:
        if len(customer_name) > 120:
            return False, "Họ và tên không được vượt quá 120 ký tự.", 400, None
        if not re.search(r'[a-zA-Z\u00C0-\u1EF9]', customer_name):
            return False, "Họ và tên không hợp lệ (phải chứa ít nhất một chữ cái).", 400, None

    product_category = str(data.get('product_category') or 'lanyard').strip()
    if product_category not in ALLOWED_CATEGORIES:
        return False, f"Danh mục sản phẩm '{product_category}' không hợp lệ.", 400, None

    quantity_range = str(data.get('quantity_range') or '10-20').strip()
    notes = str(data.get('notes') or '').strip()
    if len(notes) > 1000:
        return False, "Ghi chú không được vượt quá 1000 ký tự.", 400, None

    clean_data = {
        'phone': clean_phone,
        'customer_name': customer_name,
        'product_category': product_category,
        'quantity_range': quantity_range,
        'notes': notes
    }
    return True, None, 200, clean_data
