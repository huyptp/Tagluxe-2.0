"""Progressive enhancement for admin save forms; normal form posts still work."""
from flask import g, get_flashed_messages, jsonify, request, session

SAVE_ENDPOINTS = {
    'admin_update_product_specs', 'admin_add_product', 'admin_edit_product',
    'admin_update_pricing', 'admin_add_accessory', 'admin_edit_accessory',
    'admin_update_demo_images', 'admin_update_campaign_banner',
    'admin_customer_new', 'admin_customer_edit', 'admin_quote_detail',
    'admin_update_quote_status', 'admin_bulk_quote_status', 'admin_payments', 'admin_staff',
    'admin_staff_edit', 'admin_notifications', 'admin_notification_edit',
    'admin_account_password', 'admin_reminders',
}


def save_response(response):
    endpoint = (request.endpoint or '').removeprefix('admin.')
    if (request.method != 'POST' or request.headers.get('X-Admin-Save') != '1'
            or endpoint not in SAVE_ENDPOINTS):
        return response
    messages = get_flashed_messages(with_categories=True)
    errors = [message for category, message in messages if category in ('error', 'danger')]
    if not session.get('logged_in'):
        payload, status = {'success': False, 'message': 'Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại ở tab khác rồi thử lưu.'}, 401
    elif response.is_json:
        payload, status = response.get_json(), response.status_code
    else:
        success = response.status_code < 400 and not errors and any(
            category == 'success' for category, _ in messages)
        status = 200 if success else response.status_code if response.status_code >= 400 else 400
        payload = {'success': success, 'message': (errors or [m for _, m in messages] or [
            'Chưa xác nhận được kết quả lưu. Nội dung của bạn vẫn được giữ; hãy kiểm tra lại trước khi thử tiếp.'
        ])[-1]}
    if payload.get('success'):
        payload.update(getattr(g, 'admin_saved', {}))
    result = jsonify(payload)
    result.status_code = status
    return result
