import os
import uuid
import secrets
from functools import wraps
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from backend.config import (
    UPLOAD_FOLDER, PRIVATE_STORAGE_FOLDER, UPLOAD_REQUESTS_FOLDER,
    ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_PASSWORD_HASH, ALLOWED_IMAGE_EXTENSIONS
)
from backend.services.data_service import (
    get_all_products, get_product_by_id, add_product, update_product, delete_product,
    get_demo_requests, update_demo_request_status, delete_demo_request,
    get_quotes, update_quote_status, delete_quote,
    retry_quote_sync, retry_demo_request_sync,
    get_quotes_paginated, get_demo_requests_paginated,
    get_all_accessories, get_accessory_by_id, update_accessory,
    get_all_price_tiers_grouped, update_price_tiers_bulk,
    add_accessory, delete_accessory, toggle_accessory_visibility,
    get_demo_images_config, save_demo_images_config, reset_single_demo_image
)
from backend.security import rate_limit, limiter, get_client_ip

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_valid_image_file(file_storage):
    """
    Validates file extension and inspects magic header bytes
    to ensure the file is an authentic image (png, jpg, jpeg, webp, gif).
    """
    if not file_storage or not file_storage.filename:
        return False
    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False
    header = file_storage.read(512)
    file_storage.seek(0)
    if not header:
        return False
    is_png = header.startswith(b'\x89PNG\r\n\x1a\n')
    is_jpeg = header.startswith(b'\xff\xd8\xff')
    is_gif = header.startswith(b'GIF87a') or header.startswith(b'GIF89a')
    is_webp = header.startswith(b'RIFF') and b'WEBP' in header[:16]
    return is_png or is_jpeg or is_gif or is_webp

def paginate_items(items, page=1, per_page=20):
    page = max(1, page)
    total_items = len(items) if items else 0
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    return {
        'items': items[start:end] if items else [],
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_items': total_items,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }

def get_csrf_token():
    if '_admin_csrf_token' not in session:
        session['_admin_csrf_token'] = secrets.token_hex(24)
    return session['_admin_csrf_token']

def validate_csrf():
    token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    expected = session.get('_admin_csrf_token')
    if not token or not expected or not secrets.compare_digest(token, expected):
        return False
    return True

@admin_bp.context_processor
def inject_admin_globals():
    return {
        'csrf_token': get_csrf_token(),
        'admin_username': session.get('admin_username', 'Quản trị viên')
    }

def record_audit(action, target_type, target_id, details=""):
    try:
        from backend.database import db
        from backend.models import AuditLog
        user = session.get('admin_username', 'admin')
        ip = request.remote_addr or '127.0.0.1'
        log = AuditLog(
            admin_user=user,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            details=str(details),
            ip_address=ip
        )
        db.session.add(log)
        db.session.commit()
    except Exception as ex:
        print(f"[AUDIT_LOG_ERROR] {ex}")

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and session.get('logged_in'):
            return f(*args, **kwargs)
        else:
            return redirect(url_for('admin.admin_login'))
    return wrap

def verify_admin_credentials(username, password):
    if not secrets.compare_digest(username, ADMIN_USERNAME):
        return False
    if ADMIN_PASSWORD_HASH:
        return check_password_hash(ADMIN_PASSWORD_HASH, password)
    return secrets.compare_digest(password, ADMIN_PASSWORD)

@admin_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(limit=5, window_sec=60, error_message='Bạn đã nhập sai quá nhiều lần. Vui lòng chờ 1 phút trước khi thử lại.', is_json=False)
def admin_login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        if verify_admin_credentials(username, password):
            session.clear()
            session['logged_in'] = True
            session['admin_username'] = username
            session['_admin_csrf_token'] = secrets.token_hex(24)
            limiter.reset_key(f"admin.admin_login:{get_client_ip()}")
            record_audit('login', 'admin_session', username, 'Đăng nhập thành công')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            record_audit('failed_login', 'admin_session', username, 'Đăng nhập thất bại')
            flash('Sai tên đăng nhập hoặc mật khẩu', 'error')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def admin_logout():
    user = session.get('admin_username', 'admin')
    record_audit('logout', 'admin_session', user, 'Đăng xuất')
    session.clear()
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    from backend.admin.services import get_admin_dashboard_stats
    stats = get_admin_dashboard_stats()
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/products')
@login_required
def admin_products():
    products = get_all_products()
    lan_prod = next((p for p in products if p['id'] == 'lan-1'), None)
    pvc_prod = next((p for p in products if p['id'] == 'acc-1' or 'pvc' in p['name'].lower()), None)
    holder_prod = next((p for p in products if p['id'] == 'acc-2' or 'vỏ' in p['name'].lower() or 'holder' in p['name'].lower()), None)

    active_tab = request.args.get('tab', 'list')
    active_prod = request.args.get('prod', 'lan-1')

    return render_template(
        'admin/products.html',
        products=products,
        lan_prod=lan_prod,
        pvc_prod=pvc_prod,
        holder_prod=holder_prod,
        active_tab=active_tab,
        active_prod=active_prod
    )

@admin_bp.route('/products/update-specs', methods=['POST'])
@login_required
def admin_update_product_specs():
    if not validate_csrf():
        flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
        return redirect(url_for('admin.admin_products', tab='specs'))

    product_id = request.form.get('product_id')
    if not product_id:
        flash('Thiếu mã sản phẩm cần cập nhật.', 'error')
        return redirect(url_for('admin.admin_products', tab='specs'))

    prod = get_product_by_id(product_id, visible_only=False)
    if not prod:
        flash('Sản phẩm không tồn tại.', 'error')
        return redirect(url_for('admin.admin_products', tab='specs'))

    badge = (request.form.get('badge') or '').strip()
    name = (request.form.get('name') or '').strip()
    description = (request.form.get('description') or '').strip()
    min_order = request.form.get('min_order')
    width = request.form.get('width')

    # Parse dynamic specs list from arrays: spec_icon[], spec_label[], spec_value[]
    spec_icons = request.form.getlist('spec_icon[]')
    spec_labels = request.form.getlist('spec_label[]')
    spec_values = request.form.getlist('spec_value[]')

    specs = []
    max_len = max(len(spec_icons), len(spec_labels), len(spec_values))
    for i in range(max_len):
        icon = spec_icons[i].strip() if i < len(spec_icons) else 'check-circle-2'
        label = spec_labels[i].strip() if i < len(spec_labels) else ''
        value = spec_values[i].strip() if i < len(spec_values) else ''
        if label or value:
            specs.append({
                'icon': icon or 'check-circle-2',
                'label': label,
                'value': value
            })

    updated_fields = {
        'badge': badge,
        'description': description,
        'specs': specs
    }
    if name:
        updated_fields['name'] = name
    if min_order:
        try:
            updated_fields['min_order'] = int(min_order)
        except ValueError:
            pass
    if width is not None:
        updated_fields['width'] = width

    saved = update_product(product_id, updated_fields)
    if saved:
        record_audit('update_product_specs', 'product', product_id, f"Updated specs & badge for {product_id}")
        flash(f'Đã cập nhật thông số và mô tả cho sản phẩm "{saved.get("name", product_id)}" thành công!', 'success')
    else:
        flash('Lỗi khi lưu thông số sản phẩm.', 'error')

    return redirect(url_for('admin.admin_products', tab='specs', prod=product_id))

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if request.method == 'POST':
        if not validate_csrf():
            flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
            return redirect(url_for('admin.admin_products'))

        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        width = request.form.get('width')
        min_order = int(request.form.get('min_order', 10))
        price_type = request.form.get('price_type')
        price = int(request.form.get('price', 0) or 0)
        featured = request.form.get('featured') == 'on'
        visible = request.form.get('visible') == 'on'

        image_filenames = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename != '':
                    if not is_valid_image_file(file):
                        flash(f'File "{file.filename}" không hợp lệ. Chỉ chấp nhận định dạng ảnh (PNG, JPG, JPEG, WEBP, GIF).', 'error')
                        return render_template('admin/product_form.html', product=None)
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                    image_filenames.append(unique_filename)

        new_product = {
            "id": uuid.uuid4().hex[:8],
            "name": name,
            "category": category,
            "description": description,
            "images": image_filenames,
            "width": width,
            "min_order": min_order,
            "price_type": price_type,
            "price": price,
            "featured": featured,
            "visible": visible
        }

        saved = add_product(new_product)
        if not saved:
            flash('Lỗi cơ sở dữ liệu: Không thể lưu sản phẩm mới.', 'error')
            return redirect(url_for('admin.admin_products'))

        record_audit('create_product', 'product', new_product['id'], f"Added product {name}")
        flash('Thêm sản phẩm thành công', 'success')
        return redirect(url_for('admin.admin_products'))

    return render_template('admin/product_form.html', product=None)

@admin_bp.route('/products/edit/<id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(id):
    product = get_product_by_id(id, visible_only=False)
    if not product:
        return "Sản phẩm không tồn tại", 404

    if request.method == 'POST':
        if not validate_csrf():
            flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
            return redirect(url_for('admin.admin_products'))

        updated_data = {
            'name': request.form.get('name'),
            'category': request.form.get('category'),
            'description': request.form.get('description'),
            'width': request.form.get('width'),
            'min_order': int(request.form.get('min_order', 10)),
            'price_type': request.form.get('price_type'),
            'price': int(request.form.get('price', 0) or 0),
            'featured': request.form.get('featured') == 'on',
            'visible': request.form.get('visible') == 'on'
        }

        existing_images = list(product.get('images', []) if isinstance(product, dict) else getattr(product, 'images', []))
        kept_images_present = request.form.get('kept_images_present') == '1'
        if kept_images_present:
            kept_list = [img.strip() for img in request.form.getlist('kept_images[]') if img.strip()]
            existing_images = [img for img in existing_images if img in kept_list]

        new_images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename != '':
                    if not is_valid_image_file(file):
                        flash(f'File "{file.filename}" không hợp lệ. Chỉ chấp nhận định dạng ảnh (PNG, JPG, JPEG, WEBP, GIF).', 'error')
                        return render_template('admin/product_form.html', product=product)
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                    new_images.append(unique_filename)

        if new_images:
            keep_existing = request.form.get('keep_existing_images') != '0'
            if keep_existing and existing_images:
                updated_data['images'] = list(existing_images) + new_images
            else:
                updated_data['images'] = new_images
        elif kept_images_present:
            updated_data['images'] = existing_images

        saved = update_product(id, updated_data)
        if not saved:
            flash('Lỗi cơ sở dữ liệu: Không thể cập nhật thông tin sản phẩm.', 'error')
            return redirect(url_for('admin.admin_products'))

        record_audit('update_product', 'product', id, f"Updated product {updated_data.get('name')}")
        flash('Cập nhật sản phẩm thành công', 'success')
        return redirect(url_for('admin.admin_products'))

    return render_template('admin/product_form.html', product=product)

@admin_bp.route('/products/<id>/delete-image', methods=['POST'])
@login_required
def admin_delete_product_image(id):
    if not validate_csrf():
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_edit_product', id=id))

    product = get_product_by_id(id, visible_only=False)
    if not product:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'Sản phẩm không tồn tại'}, 404
        flash('Sản phẩm không tồn tại.', 'error')
        return redirect(url_for('admin.admin_products'))

    body = request.get_json(silent=True) or {}
    img_to_remove = (request.form.get('image') or body.get('image') or '').strip()
    existing_images = list(product.get('images', []) if isinstance(product, dict) else getattr(product, 'images', []))

    if not img_to_remove or img_to_remove not in existing_images:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'Không tìm thấy ảnh cần xóa trong sản phẩm'}, 400
        flash('Không tìm thấy ảnh cần xóa.', 'error')
        return redirect(url_for('admin.admin_edit_product', id=id))

    remaining = [img for img in existing_images if img != img_to_remove]
    saved = update_product(id, {'images': remaining})
    if not saved:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'Lỗi cơ sở dữ liệu khi xóa ảnh'}, 500
        flash('Không thể xóa ảnh sản phẩm.', 'error')
        return redirect(url_for('admin.admin_edit_product', id=id))

    record_audit('delete_product_image', 'product', id, f"Removed image {img_to_remove}")
    if request.is_json or request.headers.get('Accept') == 'application/json':
        return {'success': True, 'message': 'Đã xóa ảnh khỏi sản phẩm!', 'images': remaining}
    flash('Đã xóa ảnh khỏi sản phẩm thành công!', 'success')
    return redirect(url_for('admin.admin_edit_product', id=id))

@admin_bp.route('/products/delete/<id>', methods=['POST'])
@login_required
def admin_delete_product(id):
    if not validate_csrf():
        flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
        return redirect(url_for('admin.admin_products'))

    deleted_prod = delete_product(id)
    if not deleted_prod:
        flash('Lỗi cơ sở dữ liệu: Không thể xóa sản phẩm.', 'error')
        return redirect(url_for('admin.admin_products'))

    if deleted_prod.get('images'):
        for img in deleted_prod['images']:
            img_path = os.path.join(UPLOAD_FOLDER, img)
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception:
                    pass
    record_audit('delete_product', 'product', id, f"Deleted product {id}")
    flash('Xóa sản phẩm thành công', 'success')
    return redirect(url_for('admin.admin_products'))

# ===== DEMO REQUESTS =====
@admin_bp.route('/requests')
@login_required
def admin_requests():
    return redirect(url_for('admin.admin_quotes'))

@admin_bp.route('/requests/status/<id>', methods=['POST'])
@login_required
def admin_update_request_status(id):
    if not validate_csrf():
        flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
        return redirect(url_for('admin.admin_requests'))

    status = request.form.get('status')
    if status:
        ok = update_demo_request_status(id, status)
        if ok:
            record_audit('update_request_status', 'demo_request', id, f"Changed status to {status}")
            flash('Cập nhật trạng thái yêu cầu thành công', 'success')
        else:
            flash('Lỗi cơ sở dữ liệu: Không thể cập nhật trạng thái yêu cầu.', 'error')
    return redirect(url_for('admin.admin_requests'))

@admin_bp.route('/requests/delete/<id>', methods=['POST'])
@login_required
def admin_delete_request(id):
    if not validate_csrf():
        flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
        return redirect(url_for('admin.admin_requests'))

    deleted_req = delete_demo_request(id)
    if not deleted_req:
        flash('Lỗi cơ sở dữ liệu: Không thể xóa yêu cầu demo.', 'error')
        return redirect(url_for('admin.admin_requests'))

    if deleted_req.get('file_path'):
        fpath = os.path.join(PRIVATE_STORAGE_FOLDER, deleted_req['file_path'])
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass
    record_audit('delete_request', 'demo_request', id, f"Deleted request {id}")
    flash('Đã xóa yêu cầu demo thành công', 'success')
    return redirect(url_for('admin.admin_requests'))

@admin_bp.route('/requests/retry-sync/<id>', methods=['POST'])
@login_required
def admin_retry_request_sync(id):
    if not validate_csrf():
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_requests'))

    from flask import current_app
    app = current_app._get_current_object()
    success, msg = retry_demo_request_sync(id, app)
    if success:
        record_audit('retry_request_sync', 'demo_request', id, 'Đồng bộ Google Sheets thành công')
        flash('Đã đồng bộ lại yêu cầu demo lên Google Sheets thành công!', 'success')
    else:
        record_audit('retry_request_sync_failed', 'demo_request', id, f"Thất bại: {msg}")
        flash(f'Đồng bộ thất bại: {msg}', 'error')
    return redirect(url_for('admin.admin_requests'))

@admin_bp.route('/requests/file/<id>')
@login_required
def admin_download_request_file(id):
    from backend.models import DemoRequest
    req_record = DemoRequest.query.filter_by(id=id).first()
    if not req_record or not req_record.file_path:
        flash('Không tìm thấy file đính kèm cho yêu cầu này.', 'error')
        return redirect(url_for('admin.admin_requests'))

    clean_filename = os.path.basename(req_record.file_path)
    full_path = os.path.join(PRIVATE_STORAGE_FOLDER, clean_filename)
    if not os.path.isfile(full_path):
        flash('File không tồn tại trên hệ thống lưu trữ.', 'error')
        return redirect(url_for('admin.admin_requests'))

    record_audit('download_request_file', 'demo_request', id, f"Downloaded {req_record.original_filename or clean_filename}")
    resp = send_from_directory(
        PRIVATE_STORAGE_FOLDER,
        clean_filename,
        as_attachment=True,
        download_name=req_record.original_filename or clean_filename
    )
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    return resp

# ===== BÁO GIÁ TRỰC TUYẾN (QUOTES) =====
@admin_bp.route('/quotes')
@login_required
def admin_quotes():
    from backend.admin.services import get_quotes_summary_stats
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    pagination = get_quotes_paginated(status=status_filter, search=search_query, page=page, per_page=20)
    all_filtered = get_quotes(status=status_filter, search=search_query)
    summary_stats = get_quotes_summary_stats(all_filtered)
    return render_template(
        'admin/quotes.html',
        quotes=pagination['items'],
        page=pagination['page'],
        total_pages=pagination['total_pages'],
        total_items=pagination['total_items'],
        has_prev=pagination['has_prev'],
        has_next=pagination['has_next'],
        current_status=status_filter,
        search_query=search_query,
        summary_stats=summary_stats
    )

@admin_bp.route('/quotes/export')
@login_required
def admin_export_quotes():
    from flask import Response
    from backend.admin.services import generate_quotes_csv_bytes
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()
    csv_bytes = generate_quotes_csv_bytes(status=status_filter, search=search_query)
    record_audit('export_quotes_csv', 'quote', status_filter or 'all', f"Xuất CSV báo giá (status={status_filter}, q={search_query})")
    resp = Response(csv_bytes, mimetype='text/csv; charset=utf-8')
    resp.headers['Content-Disposition'] = 'attachment; filename="TagLuxe_BaoGia.csv"'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    return resp

@admin_bp.route('/quotes/status/<id>', methods=['POST'])
@login_required
def admin_update_quote_status(id):
    if not validate_csrf():
        flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
        return redirect(url_for('admin.admin_quotes'))

    status = request.form.get('status')
    if status:
        ok = update_quote_status(id, status)
        if ok:
            record_audit('update_quote_status', 'quote', id, f"Changed status to {status}")
            flash('Cập nhật trạng thái báo giá thành công', 'success')
        else:
            flash('Lỗi cơ sở dữ liệu: Không thể cập nhật trạng thái báo giá.', 'error')
    return redirect(url_for('admin.admin_quotes'))

@admin_bp.route('/quotes/delete/<id>', methods=['POST'])
@login_required
def admin_delete_quote(id):
    if not validate_csrf():
        flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
        return redirect(url_for('admin.admin_quotes'))

    ok = delete_quote(id)
    if ok:
        record_audit('delete_quote', 'quote', id, f"Deleted quote {id}")
        flash('Đã xóa báo giá thành công', 'success')
    else:
        flash('Lỗi cơ sở dữ liệu: Không thể xóa báo giá.', 'error')
    return redirect(url_for('admin.admin_quotes'))

@admin_bp.route('/quotes/retry-sync/<id>', methods=['POST'])
@login_required
def admin_retry_quote_sync(id):
    if not validate_csrf():
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_quotes'))

    from flask import current_app
    app = current_app._get_current_object()
    success, msg = retry_quote_sync(id, app)
    if success:
        record_audit('retry_quote_sync', 'quote', id, 'Đồng bộ Google Sheets thành công')
        flash('Đã đồng bộ lại báo giá lên Google Sheets thành công!', 'success')
    else:
        record_audit('retry_quote_sync_failed', 'quote', id, f"Thất bại: {msg}")
        flash(f'Đồng bộ thất bại: {msg}', 'error')
    return redirect(url_for('admin.admin_quotes'))


@admin_bp.route('/accessories')
@login_required
def admin_accessories():
    accessories = get_all_accessories()
    stats = {
        'total': len(accessories),
        'lanyard': sum(1 for a in accessories if a.get('category') == 'lanyard_acc'),
        'holder_ori': sum(1 for a in accessories if a.get('category') == 'holder_orientation'),
        'holder_mat': sum(1 for a in accessories if a.get('category') == 'holder_material'),
    }
    price_tiers = get_all_price_tiers_grouped()
    active_tab = request.args.get('tab', 'pricing')
    return render_template('admin/accessories.html', accessories=accessories, stats=stats, price_tiers=price_tiers, active_tab=active_tab)


@admin_bp.route('/pricing/update', methods=['POST'])
@login_required
def admin_update_pricing():
    if not validate_csrf():
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_accessories', tab='pricing'))

    updates = []
    if request.is_json:
        body = request.get_json() or {}
        updates = body.get('updates', [])
    else:
        # Gom dữ liệu từ Form POST
        tier_dict = {}
        for key, val in request.form.items():
            if key.startswith('tier_price_'):
                tid = key.replace('tier_price_', '')
                tier_dict.setdefault(tid, {})['unit_price'] = val
            elif key.startswith('tier_min_'):
                tid = key.replace('tier_min_', '')
                tier_dict.setdefault(tid, {})['min_qty'] = val
            elif key.startswith('tier_max_'):
                tid = key.replace('tier_max_', '')
                tier_dict.setdefault(tid, {})['max_qty'] = val
            elif key.startswith('tier_deleted_'):
                tid = key.replace('tier_deleted_', '')
                tier_dict.setdefault(tid, {})['action'] = 'delete'
            elif key.startswith('tier_cat_'):
                tid = key.replace('tier_cat_', '')
                tier_dict.setdefault(tid, {})['category'] = val

        for tid, data in tier_dict.items():
            item = {'id': tid}
            item.update(data)
            updates.append(item)

    if not updates:
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': 'Không có bậc giá nào được chọn để cập nhật'}, 400
        flash('Không có bậc giá nào được thay đổi.', 'info')
        return redirect(url_for('admin.admin_accessories', tab='pricing'))

    ok, res = update_price_tiers_bulk(updates)
    if ok:
        record_audit('update_price_tiers', 'price_tier', 'bulk', f"Cập nhật {res} bậc giá mới")
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': True, 'message': f'Đã lưu thành công {res} bậc giá mới!'}
        flash(f'Đã lưu thành công {res} bậc giá mới! Hệ thống tính giá tự động đã cập nhật tức thì.', 'success')
    else:
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': f'Lỗi: {res}'}, 500
        flash(f'Lỗi cập nhật biểu giá: {res}', 'error')

    return redirect(url_for('admin.admin_accessories', tab='pricing'))


@admin_bp.route('/accessories/add', methods=['POST'])
@login_required
def admin_add_accessory():
    if not validate_csrf():
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_accessories', tab='accessories'))

    name = request.form.get('name', '').strip()
    if not name:
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': 'Tên phụ kiện không được để trống'}, 400
        flash('Tên phụ kiện không được để trống.', 'error')
        return redirect(url_for('admin.admin_accessories', tab='accessories'))

    category = request.form.get('category', 'lanyard_acc').strip()
    price_raw = request.form.get('price', '0').replace('.', '').replace(',', '').strip()
    try:
        price = int(price_raw)
    except ValueError:
        price = 0

    description = request.form.get('description', '').strip()
    title = request.form.get('title', '').strip() or name
    visible = request.form.get('visible') != '0'
    min_qty_raw = request.form.get('min_quantity', '0').replace('.', '').replace(',', '').strip()
    try:
        min_quantity = max(0, int(min_qty_raw))
    except ValueError:
        min_quantity = 0

    image_url = ''
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            if not is_valid_image_file(file):
                if request.headers.get('Accept') == 'application/json' or request.is_json:
                    return {'success': False, 'message': 'File ảnh không hợp lệ (hỗ trợ JPG, PNG, WEBP).'}, 400
                flash('File ảnh không đúng định dạng (hỗ trợ JPG, PNG, WEBP).', 'error')
                return redirect(url_for('admin.admin_accessories', tab='accessories'))
            ext = file.filename.rsplit('.', 1)[-1].lower()
            safe_name = f"acc_{uuid.uuid4().hex[:10]}.{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, safe_name)
            file.save(file_path)
            image_url = f"/static/uploads/{safe_name}"

    ok, res = add_accessory({
        'name': name,
        'category': category,
        'price': price,
        'image': image_url,
        'description': description,
        'title': title,
        'visible': visible,
        'min_quantity': min_quantity
    })

    if ok:
        record_audit('add_accessory', 'accessory', res.get('id', 'new'), f"Thêm phụ kiện mới: {name}")
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': True, 'message': f'Đã thêm mẫu phụ kiện "{name}" thành công!', 'data': res}
        flash(f'Đã thêm mẫu phụ kiện "{name}" thành công!', 'success')
    else:
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': f'Lỗi: {res}'}, 500
        flash(f'Lỗi thêm phụ kiện: {res}', 'error')

    return redirect(url_for('admin.admin_accessories', tab='accessories'))


@admin_bp.route('/accessories/delete/<acc_id>', methods=['POST'])
@login_required
def admin_delete_accessory(acc_id):
    if not validate_csrf():
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_accessories', tab='accessories'))

    ok, res = delete_accessory(acc_id)
    if ok:
        record_audit('delete_accessory', 'accessory', acc_id, f"Xóa phụ kiện {acc_id}")
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': True, 'message': 'Đã xóa phụ kiện thành công!'}
        flash('Đã xóa phụ kiện thành công!', 'success')
    else:
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': f'Lỗi: {res}'}, 500
        flash(f'Lỗi xóa phụ kiện: {res}', 'error')

    return redirect(url_for('admin.admin_accessories', tab='accessories'))


@admin_bp.route('/accessories/toggle/<acc_id>', methods=['POST'])
@login_required
def admin_toggle_accessory(acc_id):
    if not validate_csrf():
        return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
    ok, res = toggle_accessory_visibility(acc_id)
    if ok:
        record_audit('toggle_accessory', 'accessory', acc_id, f"Đổi trạng thái hiển thị: {res}")
        return {'success': True, 'visible': res}
    return {'success': False, 'message': str(res)}, 500



@admin_bp.route('/accessories/edit/<acc_id>', methods=['POST'])
@login_required
def admin_edit_accessory(acc_id):
    if not validate_csrf():
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_accessories'))

    acc = get_accessory_by_id(acc_id)
    if not acc:
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': 'Không tìm thấy phụ kiện'}, 404
        flash('Không tìm thấy phụ kiện.', 'error')
        return redirect(url_for('admin.admin_accessories'))

    name = request.form.get('name', '').strip() or acc.get('name')
    price_raw = request.form.get('price')
    try:
        price = int(price_raw) if price_raw is not None else acc.get('price', 0)
    except ValueError:
        price = acc.get('price', 0)
    description = request.form.get('description', '').strip() or acc.get('description')
    title = request.form.get('title', '').strip() or acc.get('title')
    visible = request.form.get('visible') == '1' or request.form.get('visible') == 'true' or ('visible' in request.form and request.form.get('visible') != '0')
    min_qty_raw = request.form.get('min_quantity')
    try:
        min_quantity = max(0, int(min_qty_raw)) if min_qty_raw is not None and min_qty_raw.strip() != '' else acc.get('min_quantity', 0)
    except ValueError:
        min_quantity = acc.get('min_quantity', 0)

    new_image_url = None
    if request.form.get('remove_image') == '1':
        new_image_url = ''
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            if not is_valid_image_file(file):
                if request.headers.get('Accept') == 'application/json' or request.is_json:
                    return {'success': False, 'message': 'Tệp hình ảnh không hợp lệ (hỗ trợ JPG, PNG, WEBP, GIF).'}, 400
                flash('Tệp hình ảnh không hợp lệ.', 'error')
                return redirect(url_for('admin.admin_accessories'))

            ext = file.filename.rsplit('.', 1)[-1].lower()
            safe_name = f"acc_{acc_id}_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, safe_name)
            file.save(file_path)
            new_image_url = f"/static/uploads/{safe_name}"

    ok, result = update_accessory(
        acc_id,
        name=name,
        price=price,
        image=new_image_url,
        description=description,
        title=title,
        visible=visible,
        min_quantity=min_quantity
    )

    if ok:
        record_audit('update_accessory', 'accessory', acc_id, f"Cập nhật phụ kiện {acc_id}")
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': True, 'message': 'Cập nhật phụ kiện thành công!', 'data': result}
        flash('Cập nhật phụ kiện thành công!', 'success')
    else:
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return {'success': False, 'message': f'Lỗi: {result}'}, 500
        flash(f'Lỗi cập nhật: {result}', 'error')

    return redirect(url_for('admin.admin_accessories'))


@admin_bp.route('/accessories/upload/<acc_id>', methods=['POST'])
@login_required
def admin_upload_accessory_image(acc_id):
    if not validate_csrf():
        return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400

    acc = get_accessory_by_id(acc_id)
    if not acc:
        return {'success': False, 'message': 'Không tìm thấy phụ kiện'}, 404

    if 'image' not in request.files:
        return {'success': False, 'message': 'Vui lòng chọn tệp hình ảnh'}, 400

    file = request.files['image']
    if not file or not file.filename:
        return {'success': False, 'message': 'Chưa chọn tệp hình ảnh'}, 400

    if not is_valid_image_file(file):
        return {'success': False, 'message': 'Định dạng ảnh không hợp lệ. Vui lòng tải file JPG, PNG, WEBP.'}, 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    safe_name = f"acc_{acc_id}_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(file_path)
    new_image_url = f"/static/uploads/{safe_name}"

    ok, result = update_accessory(acc_id, image=new_image_url)
    if ok:
        record_audit('upload_accessory_image', 'accessory', acc_id, f"Đổi ảnh cho {acc_id}")
        return {'success': True, 'message': 'Đã tải ảnh lên thành công!', 'image_url': new_image_url, 'data': result}
    else:
        return {'success': False, 'message': f'Lỗi lưu ảnh: {result}'}, 500


@admin_bp.route('/accessories/delete-image/<acc_id>', methods=['POST'])
@login_required
def admin_delete_accessory_image(acc_id):
    if not validate_csrf():
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_accessories', tab='accessories'))

    acc = get_accessory_by_id(acc_id)
    if not acc:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'Không tìm thấy phụ kiện'}, 404
        flash('Không tìm thấy phụ kiện.', 'error')
        return redirect(url_for('admin.admin_accessories', tab='accessories'))

    ok, result = update_accessory(acc_id, image='')
    if ok:
        record_audit('delete_accessory_image', 'accessory', acc_id, f"Xóa ảnh của phụ kiện {acc_id}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': True, 'message': 'Đã xóa ảnh phụ kiện thành công!', 'image_url': '/static/images/placeholder.jpg', 'data': result}
        flash('Đã xóa ảnh phụ kiện thành công!', 'success')
    else:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': f'Lỗi xóa ảnh: {result}'}, 500
        flash(f'Lỗi xóa ảnh: {result}', 'error')

    return redirect(url_for('admin.admin_accessories', tab='accessories'))


# --- QUẢN LÝ BỘ ẢNH DEMO BÁO GIÁ (STOREFRONT LIVE PREVIEW) ---
@admin_bp.route('/demo-images', methods=['GET'])
@login_required
def admin_demo_images():
    cfg = get_demo_images_config()
    return render_template('admin/demo_images.html', demo_images=cfg)


@admin_bp.route('/demo-images/update', methods=['POST'])
@login_required
def admin_update_demo_images():
    if not validate_csrf():
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('CSRF token không hợp lệ. Vui lòng thử lại.', 'error')
        return redirect(url_for('admin.admin_demo_images'))

    cfg = get_demo_images_config()
    keys = [
        'pvc_no_hole', 'pvc_oval_hole', 'pvc_round_hole',
        'holder_silicone_vertical', 'holder_silicone_horizontal',
        'holder_plain_vertical', 'holder_plain_horizontal',
        'holder_custom_vertical', 'holder_custom_horizontal',
        'holder_vertical', 'holder_horizontal',
        'lanyard_default', 'lanyard_15', 'lanyard_20', 'lanyard_25'
    ]
    updates = {}

    for k in keys:
        updates[k] = {}
        if f'title_{k}' in request.form:
            updates[k]['title'] = request.form.get(f'title_{k}', '').strip()
        if f'pill_{k}' in request.form:
            updates[k]['pill'] = request.form.get(f'pill_{k}', '').strip()
        if f'caption_{k}' in request.form:
            updates[k]['caption'] = request.form.get(f'caption_{k}', '').strip()

        file_key = f'file_{k}'
        if file_key in request.files:
            f = request.files[file_key]
            if f and f.filename:
                if is_valid_image_file(f):
                    ext = f.filename.rsplit('.', 1)[-1].lower()
                    safe_filename = f"demo_{k}_{uuid.uuid4().hex[:8]}.{ext}"
                    save_path = os.path.join(UPLOAD_FOLDER, safe_filename)
                    f.save(save_path)
                    updates[k]['image'] = f"/static/uploads/{safe_filename}"
                else:
                    if request.is_json or request.headers.get('Accept') == 'application/json':
                        return {'success': False, 'message': f'Tệp ảnh "{f.filename}" không hợp lệ (hỗ trợ JPG, PNG, WEBP).'}, 400
                    flash(f'Tệp ảnh "{f.filename}" không hợp lệ (hỗ trợ JPG, PNG, WEBP).', 'error')

        url_val = request.form.get(f'url_{k}', '').strip()
        if url_val and 'image' not in updates[k]:
            updates[k]['image'] = url_val

    ok, result = save_demo_images_config(updates)
    if ok:
        record_audit('update_demo_images', 'setting', 'demo_images', 'Cập nhật bộ ảnh demo báo giá trực quan')
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': True, 'message': 'Đã lưu cấu hình ảnh demo thành công!', 'data': result}
        flash('Đã lưu cấu hình ảnh demo báo giá thành công!', 'success')
    else:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': f'Lỗi lưu cấu hình: {result}'}, 500
        flash(f'Lỗi lưu cấu hình: {result}', 'error')

    return redirect(url_for('admin.admin_demo_images'))


@admin_bp.route('/demo-images/upload-single/<key>', methods=['POST'])
@login_required
def admin_upload_single_demo_image(key):
    if not validate_csrf():
        return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400

    keys = [
        'pvc_no_hole', 'pvc_oval_hole', 'pvc_round_hole',
        'holder_silicone_vertical', 'holder_silicone_horizontal',
        'holder_plain_vertical', 'holder_plain_horizontal',
        'holder_custom_vertical', 'holder_custom_horizontal',
        'holder_vertical', 'holder_horizontal',
        'lanyard_default', 'lanyard_15', 'lanyard_20', 'lanyard_25'
    ]
    if key not in keys:
        return {'success': False, 'message': 'Mục ảnh demo không hợp lệ'}, 400

    if 'image' not in request.files:
        return {'success': False, 'message': 'Vui lòng chọn tệp hình ảnh'}, 400

    f = request.files['image']
    if not f or not f.filename:
        return {'success': False, 'message': 'Chưa chọn tệp hình ảnh'}, 400

    if not is_valid_image_file(f):
        return {'success': False, 'message': 'Định dạng ảnh không hợp lệ (hỗ trợ JPG, PNG, WEBP).'}, 400

    ext = f.filename.rsplit('.', 1)[-1].lower()
    safe_filename = f"demo_{key}_{uuid.uuid4().hex[:8]}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, safe_filename)
    f.save(save_path)
    img_url = f"/static/uploads/{safe_filename}"

    payload = {key: {'image': img_url}}
    if key == 'lanyard_20':
        payload['lanyard_default'] = {'image': img_url}
    ok, result = save_demo_images_config(payload)
    if ok:
        record_audit('upload_single_demo_image', 'setting', key, f"Tải ảnh mới cho {key}")
        return {'success': True, 'message': 'Đã tải ảnh lên thành công!', 'image_url': img_url, 'key': key}
    else:
        return {'success': False, 'message': f'Lỗi lưu ảnh: {result}'}, 500


@admin_bp.route('/demo-images/reset/<key>', methods=['POST'])
@login_required
def admin_reset_single_demo_image(key):
    if not validate_csrf():
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('Yêu cầu không hợp lệ (CSRF error).', 'error')
        return redirect(url_for('admin.admin_demo_images'))

    ok, default_img = reset_single_demo_image(key)
    if ok:
        record_audit('reset_single_demo_image', 'setting', key, f"Xóa ảnh vừa tải và khôi phục ảnh mặc định cho {key}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {
                'success': True,
                'message': 'Đã xóa ảnh tải nhầm và khôi phục ảnh mặc định thành công!',
                'image_url': default_img,
                'key': key
            }
        flash('Đã xóa ảnh tải nhầm và khôi phục ảnh mặc định thành công!', 'success')
    else:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': str(default_img)}, 400
        flash(f'Lỗi khôi phục ảnh: {default_img}', 'error')

    return redirect(url_for('admin.admin_demo_images'))


# ==================== ROUTE QUẢN LÝ BANNER CHIẾN DỊCH (RESPONSIVE) ====================

@admin_bp.route('/campaign-banner', methods=['GET'])
@login_required
def admin_campaign_banner():
    from backend.services.data_service import get_campaign_banner_config
    banner = get_campaign_banner_config()
    return render_template('admin/campaign_banner.html', banner=banner, csrf_token=get_csrf_token())


@admin_bp.route('/campaign-banner/update', methods=['POST'])
@login_required
def admin_update_campaign_banner():
    if not validate_csrf():
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400
        flash('Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn (CSRF error).', 'error')
        return redirect(url_for('admin.admin_campaign_banner'))

    from backend.services.data_service import get_campaign_banner_config, save_campaign_banner_config
    current = get_campaign_banner_config()

    title = request.form.get('title', '').strip() or current.get('title', 'Chương Trình Khuyến Mại')
    enabled = request.form.get('enabled') in ('1', 'on', 'true', True)
    img_desk = current.get('image_desktop', '')
    img_mob = current.get('image_mobile', '')

    # Cho phép cờ xóa từng ảnh nếu gửi từ form
    if request.form.get('remove_desktop') == '1':
        img_desk = ''
    if request.form.get('remove_mobile') == '1':
        img_mob = ''

    # 1. Xử lý upload ảnh Desktop (16:9)
    if 'banner_image_desktop' in request.files:
        f_desk = request.files['banner_image_desktop']
        if f_desk and f_desk.filename != '':
            if not is_valid_image_file(f_desk):
                msg = f'Tệp ảnh Desktop "{f_desk.filename}" không hợp lệ (hỗ trợ JPG, PNG, WEBP).'
                if request.is_json:
                    return {'success': False, 'message': msg}, 400
                flash(msg, 'error')
                return redirect(url_for('admin.admin_campaign_banner'))

            ext = f_desk.filename.rsplit('.', 1)[-1].lower()
            safe_filename = f"campaign_banner_desk_{uuid.uuid4().hex[:8]}.{ext}"
            save_path = os.path.join(UPLOAD_FOLDER, safe_filename)
            f_desk.save(save_path)
            img_desk = f"/static/uploads/{safe_filename}"

    # 2. Xử lý upload ảnh Mobile (4:5 hoặc 1:1)
    if 'banner_image_mobile' in request.files:
        f_mob = request.files['banner_image_mobile']
        if f_mob and f_mob.filename != '':
            if not is_valid_image_file(f_mob):
                msg = f'Tệp ảnh Mobile "{f_mob.filename}" không hợp lệ (hỗ trợ JPG, PNG, WEBP).'
                if request.is_json:
                    return {'success': False, 'message': msg}, 400
                flash(msg, 'error')
                return redirect(url_for('admin.admin_campaign_banner'))

            ext = f_mob.filename.rsplit('.', 1)[-1].lower()
            safe_filename = f"campaign_banner_mob_{uuid.uuid4().hex[:8]}.{ext}"
            save_path = os.path.join(UPLOAD_FOLDER, safe_filename)
            f_mob.save(save_path)
            img_mob = f"/static/uploads/{safe_filename}"

    # 3. Hỗ trợ trường banner_image cũ tương thích ngược
    if 'banner_image' in request.files:
        f_legacy = request.files['banner_image']
        if f_legacy and f_legacy.filename != '':
            if is_valid_image_file(f_legacy):
                ext = f_legacy.filename.rsplit('.', 1)[-1].lower()
                safe_filename = f"campaign_banner_desk_{uuid.uuid4().hex[:8]}.{ext}"
                save_path = os.path.join(UPLOAD_FOLDER, safe_filename)
                f_legacy.save(save_path)
                img_desk = f"/static/uploads/{safe_filename}"

    # Ràng buộc an toàn: Nếu chưa có bất kỳ ảnh nào thì KHÔNG THỂ BẬT
    if not img_desk and not img_mob:
        enabled = False

    ok, result = save_campaign_banner_config({
        'title': title,
        'image_desktop': img_desk,
        'image_mobile': img_mob,
        'enabled': enabled
    })

    if ok:
        record_audit('update_campaign_banner', 'setting', 'campaign_banner', f"Cập nhật Banner Responsive: enabled={enabled}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': True, 'message': 'Đã cập nhật banner thành công!', 'data': result}
        flash('Đã lưu cấu hình banner chiến dịch thành công!', 'success')
    else:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': f'Lỗi lưu banner: {result}'}, 500
        flash(f'Lỗi lưu banner: {result}', 'error')

    return redirect(url_for('admin.admin_campaign_banner'))


@admin_bp.route('/campaign-banner/delete', methods=['POST'])
@login_required
def admin_delete_campaign_banner():
    if not validate_csrf():
        return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400

    target = request.form.get('target') or (request.get_json(silent=True) or {}).get('target') or 'all'
    from backend.services.data_service import delete_campaign_banner
    ok, result = delete_campaign_banner(target=target)
    if ok:
        msg = 'Đã xóa toàn bộ ảnh banner và tắt hiển thị thành công!' if target == 'all' else f'Đã xóa ảnh banner {target} thành công!'
        record_audit('delete_campaign_banner', 'setting', 'campaign_banner', f"Xóa banner: target={target}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': True, 'message': msg, 'data': result}
        flash(msg, 'success')
    else:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return {'success': False, 'message': f'Lỗi xóa banner: {result}'}, 500
        flash(f'Lỗi xóa banner: {result}', 'error')

    return redirect(url_for('admin.admin_campaign_banner'))


@admin_bp.route('/campaign-banner/toggle', methods=['POST'])
@login_required
def admin_toggle_campaign_banner():
    if not validate_csrf():
        return {'success': False, 'message': 'CSRF token không hợp lệ'}, 400

    from backend.services.data_service import get_campaign_banner_config, save_campaign_banner_config
    current = get_campaign_banner_config()

    # Ràng buộc an toàn: Chưa có ảnh nào thì không thể bật
    if not current.get('image_desktop') and not current.get('image_mobile') and not current.get('image'):
        return {'success': False, 'message': 'Bạn chưa tải ảnh banner lên. Hãy thêm ít nhất 1 ảnh trước khi bật hiển thị!'}, 400

    new_state = not current.get('enabled', False)
    ok, result = save_campaign_banner_config({'enabled': new_state})
    if ok:
        record_audit('toggle_campaign_banner', 'setting', 'campaign_banner', f"Chuyển trạng thái banner: enabled={new_state}")
        return {'success': True, 'message': f'Đã {"bật" if new_state else "tắt"} hiển thị banner thành công!', 'enabled': new_state}
    else:
        return {'success': False, 'message': f'Lỗi cập nhật: {result}'}, 500



