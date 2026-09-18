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
    retry_quote_sync, retry_demo_request_sync
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
@login_required
def admin_dashboard():
    return redirect(url_for('admin.admin_products'))

@admin_bp.route('/products')
@login_required
def admin_products():
    products = get_all_products()
    return render_template('admin/products.html', products=products)

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

        if 'images' in request.files:
            files = request.files.getlist('images')
            new_images = []
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
                updated_data['images'] = new_images

        saved = update_product(id, updated_data)
        if not saved:
            flash('Lỗi cơ sở dữ liệu: Không thể cập nhật thông tin sản phẩm.', 'error')
            return redirect(url_for('admin.admin_products'))

        record_audit('update_product', 'product', id, f"Updated product {updated_data.get('name')}")
        flash('Cập nhật sản phẩm thành công', 'success')
        return redirect(url_for('admin.admin_products'))

    return render_template('admin/product_form.html', product=product)

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
    page = request.args.get('page', 1, type=int)
    requests_list = get_demo_requests()
    pagination = paginate_items(requests_list, page=page, per_page=20)
    return render_template(
        'admin/requests.html',
        requests=pagination['items'],
        page=pagination['page'],
        total_pages=pagination['total_pages'],
        total_items=pagination['total_items'],
        has_prev=pagination['has_prev'],
        has_next=pagination['has_next']
    )

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
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    quotes_list = get_quotes(status=status_filter, search=search_query)
    pagination = paginate_items(quotes_list, page=page, per_page=20)
    return render_template(
        'admin/quotes.html',
        quotes=pagination['items'],
        page=pagination['page'],
        total_pages=pagination['total_pages'],
        total_items=pagination['total_items'],
        has_prev=pagination['has_prev'],
        has_next=pagination['has_next'],
        current_status=status_filter,
        search_query=search_query
    )

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
