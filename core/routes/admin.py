import os
import uuid
from functools import wraps
from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from werkzeug.utils import secure_filename
from core.config import UPLOAD_FOLDER, UPLOAD_REQUESTS_FOLDER
from core.services.data_service import (
    get_all_products, get_product_by_id, add_product, update_product, delete_product,
    get_demo_requests, update_demo_request_status, delete_demo_request,
    get_quotes, update_quote_status, delete_quote
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('admin.admin_login'))
    return wrap

from core.security import rate_limit, limiter, get_client_ip

@admin_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(limit=5, window_sec=60, error_message='Bạn đã nhập sai quá nhiều lần. Vui lòng chờ 1 phút trước khi thử lại.', is_json=False)
def admin_login():
    admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'admin123')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == admin_user and password == admin_pass:
            session['logged_in'] = True
            limiter.reset_key(f"admin.admin_login:{get_client_ip()}")
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Sai tên đăng nhập hoặc mật khẩu', 'error')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def admin_logout():
    session.pop('logged_in', None)
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

        add_product(new_product)
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
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                    new_images.append(unique_filename)
            if new_images:
                updated_data['images'] = new_images

        update_product(id, updated_data)
        flash('Cập nhật sản phẩm thành công', 'success')
        return redirect(url_for('admin.admin_products'))

    return render_template('admin/product_form.html', product=product)

@admin_bp.route('/products/delete/<id>', methods=['POST'])
@login_required
def admin_delete_product(id):
    deleted_prod = delete_product(id)
    if deleted_prod and deleted_prod.get('images'):
        for img in deleted_prod['images']:
            img_path = os.path.join(UPLOAD_FOLDER, img)
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception:
                    pass
    flash('Xóa sản phẩm thành công', 'success')
    return redirect(url_for('admin.admin_products'))

# ===== DEMO REQUESTS =====
@admin_bp.route('/requests')
@login_required
def admin_requests():
    requests_list = get_demo_requests()
    return render_template('admin/requests.html', requests=requests_list)

@admin_bp.route('/requests/status/<id>', methods=['POST'])
@login_required
def admin_update_request_status(id):
    status = request.form.get('status')
    if status:
        update_demo_request_status(id, status)
        flash('Cập nhật trạng thái yêu cầu thành công', 'success')
    return redirect(url_for('admin.admin_requests'))

@admin_bp.route('/requests/delete/<id>', methods=['POST'])
@login_required
def admin_delete_request(id):
    deleted_req = delete_demo_request(id)
    if deleted_req and deleted_req.get('file_path'):
        fpath = os.path.join(UPLOAD_REQUESTS_FOLDER, deleted_req['file_path'])
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass
    flash('Đã xóa yêu cầu demo thành công', 'success')
    return redirect(url_for('admin.admin_requests'))

# ===== BÁO GIÁ TRỰC TUYẾN (QUOTES) =====
@admin_bp.route('/quotes')
@login_required
def admin_quotes():
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()
    quotes_list = get_quotes(status=status_filter, search=search_query)
    return render_template(
        'admin/quotes.html',
        quotes=quotes_list,
        current_status=status_filter,
        search_query=search_query
    )

@admin_bp.route('/quotes/status/<id>', methods=['POST'])
@login_required
def admin_update_quote_status(id):
    status = request.form.get('status')
    if status:
        update_quote_status(id, status)
        flash('Cập nhật trạng thái báo giá thành công', 'success')
    return redirect(url_for('admin.admin_quotes'))

@admin_bp.route('/quotes/delete/<id>', methods=['POST'])
@login_required
def admin_delete_quote(id):
    delete_quote(id)
    flash('Đã xóa báo giá thành công', 'success')
    return redirect(url_for('admin.admin_quotes'))
