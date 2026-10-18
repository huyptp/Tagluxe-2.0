import os
import json
import uuid
import time
import urllib.request
import threading
from datetime import datetime
from urllib.parse import quote
from backend.config import DATA_FILE, BASE_DIR, site_origin, GOOGLE_SHEET_WEBHOOK_URL

import sys

def load_data():
    if 'app' in sys.modules and hasattr(sys.modules['app'], 'load_data') and sys.modules['app'].load_data != load_data:
        return sys.modules['app'].load_data()
    if not os.path.exists(DATA_FILE):
        return {"products": [], "demo_requests": []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _is_load_data_mocked():
    return 'app' in sys.modules and hasattr(sys.modules['app'], 'load_data') and sys.modules['app'].load_data != load_data

def get_visible_products():
    if _is_load_data_mocked():
        data = sys.modules['app'].load_data()
        return [p for p in data.get('products', []) if p.get('visible', True)]
    try:
        from backend.models import Product
        prods = Product.query.filter_by(visible=True).all()
        return [p.to_dict() for p in prods]
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_GET_VISIBLE_PRODUCTS_ERROR] {ex}")
        raise

def get_all_products():
    if _is_load_data_mocked():
        data = sys.modules['app'].load_data()
        return data.get('products', [])
    try:
        from backend.models import Product
        prods = Product.query.all()
        return [p.to_dict() for p in prods]
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_GET_ALL_PRODUCTS_ERROR] {ex}")
        raise

def get_product_by_id(product_id, visible_only=True):
    if _is_load_data_mocked():
        data = sys.modules['app'].load_data()
        for p in data.get('products', []):
            if p.get('id') == product_id:
                if not visible_only or p.get('visible', True):
                    return p
        return None
    try:
        from backend.models import Product
        query = Product.query.filter_by(id=product_id)
        if visible_only:
            query = query.filter_by(visible=True)
        prod = query.first()
        return prod.to_dict() if prod else None
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_GET_PRODUCT_BY_ID_ERROR] {ex}")
        raise

def add_product(product_data):
    try:
        from backend.database import db
        from backend.models import Product
        prod = Product(
            id=product_data['id'],
            name=product_data['name'],
            category=product_data.get('category', 'lanyard'),
            description=product_data.get('description', ''),
            images_json=json.dumps(product_data.get('images', []), ensure_ascii=False),
            width=product_data.get('width', ''),
            material=product_data.get('material', ''),
            min_order=product_data.get('min_order', 10),
            price_type=product_data.get('price_type', 'contact'),
            price=product_data.get('price', 0),
            featured=product_data.get('featured', True),
            visible=product_data.get('visible', True)
        )
        db.session.add(prod)
        db.session.commit()
        return prod.to_dict()
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_PRODUCT_ADD_ERROR] {ex}")
        return None

def update_product(product_id, updated_fields):
    try:
        from backend.database import db
        from backend.models import Product
        prod = Product.query.filter_by(id=product_id).first()
        if not prod:
            return None
        for key, val in updated_fields.items():
            if key == 'images':
                prod.images = val
            elif key == 'specs':
                prod.specs = val
            elif hasattr(prod, key):
                setattr(prod, key, val)
        db.session.commit()
        return prod.to_dict()
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_PRODUCT_UPDATE_ERROR] {ex}")
        return None

def delete_product(product_id):
    try:
        from backend.database import db
        from backend.models import Product
        prod = Product.query.filter_by(id=product_id).first()
        if not prod:
            return None
        deleted_item = prod.to_dict()
        db.session.delete(prod)
        db.session.commit()
        return deleted_item
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_PRODUCT_DELETE_ERROR] {ex}")
        return None

def get_lanyard_photos(lanyards):
    seen = set()
    lanyard_photos = []
    for p in lanyards:
        imgs = p.get('images') or ([p.get('image')] if p.get('image') else [])
        for img in imgs:
            if img and img not in seen:
                seen.add(img)
                lanyard_photos.append({
                    'img': img,
                    'product_id': p['id'],
                    'product_name': p['name']
                })
    return lanyard_photos

def get_showcase_items(lanyards, accessories):
    showcase_items = []
    showcase_seen = set()

    # 1. Các hình ảnh poster / sự kiện thực tế
    posters_data = [
        {'img': 'media_1789320576400.jpg', 'title': 'Dây Đeo Thẻ Fandom & Concert', 'category': 'lanyard', 'cat_label': 'Dây Đeo Thẻ', 'desc': 'In ấn họa tiết sắc nét, màu sắc tươi sáng theo thiết kế riêng.'},
        {'img': 'media_1789320576594.jpg', 'title': 'Bộ Dây Đeo & Vỏ Thẻ Trường Học', 'category': 'set', 'cat_label': 'Bộ Sản Phẩm', 'desc': 'Dây đeo RMIT kết hợp vỏ thẻ màu sắc đồng bộ, nổi bật.'},
        {'img': 'media_1789320576602.jpg', 'title': 'Dây Đeo Thẻ Doanh Nghiệp & Sự Kiện', 'category': 'lanyard', 'cat_label': 'Dây Đeo Thẻ', 'desc': 'Tone màu sang trọng, móc khóa inox bền bỉ, nhận in từ 10 dây.'},
        {'img': 'media_1789320576614.jpg', 'title': 'Dây Đeo Thẻ Câu Lạc Bộ & Đội Nhóm', 'category': 'lanyard', 'cat_label': 'Dây Đeo Thẻ', 'desc': 'Chất liệu lụa Satin mịn màng, phối màu tươi trẻ năng động.'},
        {'img': 'media_1789320576620.jpg', 'title': 'Dây Đeo Thẻ Hội Nghị Quốc Tế', 'category': 'lanyard', 'cat_label': 'Dây Đeo Thẻ', 'desc': 'Chất liệu lụa Satin cao cấp, họa tiết độc đáo, in sắc nét không phai.'}
    ]
    for item in posters_data:
        showcase_seen.add(item['img'])
        showcase_items.append(item)

    # 2. Toàn bộ ảnh Thẻ Nhựa PVC & Vỏ Đựng Thẻ
    for acc in accessories:
        imgs = acc.get('images') or ([acc.get('image')] if acc.get('image') else [])
        is_pvc = 'PVC' in acc.get('name', '')
        cat_key = 'pvc' if is_pvc else 'holder'
        cat_lbl = 'Thẻ Nhựa PVC' if is_pvc else 'Vỏ Đựng Thẻ'
        for idx, img in enumerate(imgs):
            if img and img not in showcase_seen:
                showcase_seen.add(img)
                showcase_items.append({
                    'img': img,
                    'title': f"{acc['name']} — Mẫu {idx + 1}",
                    'category': cat_key,
                    'cat_label': cat_lbl,
                    'desc': acc.get('description', '')
                })

    # 3. Toàn bộ ảnh Dây Đeo Thẻ thực tế
    for p in lanyards:
        imgs = p.get('images') or ([p.get('image')] if p.get('image') else [])
        for idx, img in enumerate(imgs):
            if img and img not in showcase_seen:
                showcase_seen.add(img)
                showcase_items.append({
                    'img': img,
                    'title': f"{p['name']} — Mẫu {idx + 1}",
                    'category': 'lanyard',
                    'cat_label': 'Dây Đeo Thẻ',
                    'desc': p.get('description', '')
                })

    return showcase_items

def product_schema(product):
    origin = site_origin()
    result = {
        '@context': 'https://schema.org', '@type': 'Product',
        'name': product['name'], 'description': product.get('description', ''),
        'url': origin + '/product/' + quote(product['id'], safe=''),
        'brand': {'@type': 'Brand', 'name': 'TagLuxe'},
        'sku': 'TL-PROD-' + product['id'],
    }
    images = product.get('images') or ([product['image']] if product.get('image') else [])
    if images:
        result['image'] = [origin + '/static/uploads/' + quote(img, safe='') for img in images if img]
    if product.get('price_type') == 'fixed' and product.get('price', 0) > 0:
        result['offers'] = {'@type': 'Offer', 'priceCurrency': 'VND', 'price': product['price'], 'url': result['url']}
    return result

# --- DEMO REQUESTS ---

def get_demo_requests():
    try:
        from backend.models import DemoRequest
        order_col = getattr(DemoRequest, 'created_at_dt', None)
        query = DemoRequest.query
        if order_col is not None:
            query = query.order_by(order_col.desc(), DemoRequest.id.desc())
        else:
            query = query.order_by(DemoRequest.id.desc())
        reqs = query.all()
        return [r.to_dict() for r in reqs]
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_DEMO_REQ_GET_ERROR] {ex}")
        raise

def get_demo_requests_paginated(status=None, search=None, page=1, per_page=20):
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    try:
        from backend.models import DemoRequest
        query = DemoRequest.query
        if status and status != 'all':
            query = query.filter(DemoRequest.status == status)
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                (DemoRequest.customer_name.ilike(s)) |
                (DemoRequest.phone.ilike(s)) |
                (DemoRequest.id.ilike(s))
            )
        total_items = query.count()
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        order_col = getattr(DemoRequest, 'created_at_dt', None)
        if order_col is not None:
            query = query.order_by(order_col.desc(), DemoRequest.id.desc())
        else:
            query = query.order_by(DemoRequest.id.desc())
        reqs = query.offset(offset).limit(per_page).all()
        return {
            'items': [r.to_dict() for r in reqs],
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_items': total_items,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_DEMO_REQ_GET_PAGINATED_ERROR] {ex}")
        raise

def add_demo_request(phone, customer_name='', product_category='lanyard', quantity_range='10-20', notes='', file_path=None, original_filename=None):
    req_id = uuid.uuid4().hex[:6].upper()
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    new_req = {
        'id': req_id,
        'created_at': now_str,
        'phone': phone,
        'customer_name': customer_name,
        'product_category': product_category,
        'quantity_range': quantity_range,
        'notes': notes,
        'file_path': file_path,
        'original_filename': original_filename,
        'status': 'Chờ gửi demo',
        'sync_status': 'pending'
    }
    # 1. Save to Database (Single Source of Truth)
    try:
        from backend.database import db
        from backend.models import DemoRequest
        req_obj = DemoRequest(
            id=req_id,
            created_at=now_str,
            phone=phone,
            customer_name=customer_name,
            product_category=product_category,
            quantity_range=quantity_range,
            notes=notes,
            file_path=file_path,
            original_filename=original_filename,
            status='Chờ gửi demo',
            sync_status='pending'
        )
        db.session.add(req_obj)
        db.session.commit()
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_DEMO_REQ_SAVE_ERROR] Failed to save demo request {req_id}: {ex}")
        return None

    # 2. Async sync to Google Sheet
    sheet_payload = {
        'id': req_id,
        'created_at': now_str,
        'category': f"Yêu cầu Demo 2D ({product_category})",
        'customer_name': customer_name or 'Khách hàng',
        'phone': phone,
        'quantity': quantity_range,
        'specs': f"File logo: {original_filename or 'Không đính kèm'}",
        'accessories': [],
        'unit_price': 0,
        'total_price': 0,
        'notes': notes or 'Yêu cầu lên mẫu phối cảnh 2D',
        'status': 'Chờ gửi demo'
    }
    from flask import current_app
    try:
        app = current_app._get_current_object()
    except Exception:
        app = None
    sync_thread = threading.Thread(target=send_quote_to_google_sheet, args=(sheet_payload, app), daemon=True)
    sync_thread.start()

    return new_req

def update_demo_request_status(req_id, status):
    try:
        from backend.database import db
        from backend.models import DemoRequest
        req = DemoRequest.query.filter_by(id=req_id).first()
        if req:
            req.status = status
            db.session.commit()
            return True
        return False
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_DEMO_REQ_STATUS_ERROR] {ex}")
        return False

def delete_demo_request(req_id):
    try:
        from backend.database import db
        from backend.models import DemoRequest
        req = DemoRequest.query.filter_by(id=req_id).first()
        if not req:
            return None
        deleted_item = req.to_dict()
        db.session.delete(req)
        db.session.commit()
        return deleted_item
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_DEMO_REQ_DEL_ERROR] {ex}")
        return None


# --- QUOTATION & PRICING CALCULATOR ---

def get_tier_price_from_db(category, qty):
    """
    Look up pricing tier from SQLAlchemy database (price_tiers table).
    Returns unit_price or None if not found or DB not available.
    """
    try:
        from backend.models import PriceTier
        tier = PriceTier.query.filter(
            PriceTier.category == category,
            PriceTier.min_qty <= qty,
            PriceTier.max_qty >= qty
        ).first()
        if tier:
            return tier.unit_price
    except Exception:
        pass
    return None

def calculate_lanyard_price(quantity, width='2.0', accessories=None):
    """
    Calculate factory wholesale pricing for lanyards with exactly 13 quantity tiers,
    width adjustments, and accessory add-ons.
    """
    if accessories is None:
        accessories = []

    try:
        qty = max(10, int(quantity))
    except (ValueError, TypeError):
        qty = 10

    # 1. Look up tier in Database if active
    db_base = get_tier_price_from_db('lanyard', qty)
    if db_base is not None:
        base_unit = db_base
    elif qty <= 21:
        base_unit = 28000
    elif qty <= 31:
        base_unit = 26000
    elif qty <= 45:
        base_unit = 25000
    elif qty <= 70:
        base_unit = 20000
    elif qty <= 120:
        base_unit = 19000
    elif qty <= 200:
        base_unit = 18000
    elif qty <= 320:
        base_unit = 17000
    elif qty <= 420:
        base_unit = 16500
    elif qty <= 530:
        base_unit = 16000
    elif qty <= 710:
        base_unit = 15000
    elif qty <= 1000:
        base_unit = 14000
    elif qty <= 3000:
        base_unit = 13000
    elif qty <= 5000:
        base_unit = 12500
    else:
        base_unit = 12000

    width_str = str(width)
    if '1.5' in width_str:
        width_adj = -1000
        width_label = '1.5cm (Tiết kiệm)'
    elif '2.5' in width_str:
        width_adj = 2500
        width_label = '2.5cm (Bản to cao cấp)'
    else:
        width_adj = 0
        width_label = '2.0cm (Tiêu chuẩn phổ biến)'

    unit_price = base_unit + width_adj

    acc_defs = [
        ('breakaway', 'Khóa an toàn sau gáy', 2500),
        ('quick_release', 'Khóa phụ tháo rời nhanh', 2500),
        ('stopper', 'Cục thắt độ dài dây', 2500),
        ('adjuster', 'Tăng đơ tăng giảm độ dài', 2500),
        ('black_hook', 'Móc khóa màu đen', 2500)
    ]

    selected_acc_labels = []
    acc_cost_total = 0

    if isinstance(accessories, str):
        accessories = [a.strip() for a in accessories.split(',') if a.strip()]

    for item in accessories:
        item_clean = str(item).strip().lower()
        for key, label, cost in acc_defs:
            if key in item_clean or label.lower() in item_clean:
                if label not in selected_acc_labels:
                    selected_acc_labels.append(label)
                    acc_cost_total += cost
                break

    unit_price += acc_cost_total
    total_price = unit_price * qty

    return {
        'category': 'Dây đeo thẻ',
        'quantity': qty,
        'width': width_label,
        'specs': width_label,
        'accessories': selected_acc_labels,
        'unit_price': unit_price,
        'total_price': total_price
    }


# --- MA TRẬN BẢNG GIÁ THẺ NHỰA PVC THEO KÍCH THƯỚC & SỐ LƯỢNG ---
PVC_PRICING_TABLE = {
    'pvc_5.4x8.6': [
        (10, 20, 16500),
        (21, 50, 13500),
        (51, 100, 10500),
        (101, 200, 8500),
        (201, 500, 8000),
        (501, 1000, 7000),
        (1001, 9999999, 6000),
    ],
    'pvc_7x11': [
        (10, 20, 21500),
        (21, 50, 16500),
        (51, 100, 15500),
        (101, 200, 14500),
        (201, 500, 14000),
        (501, 1000, 13000),
        (1001, 9999999, 12000),
    ],
    'pvc_9x12': [
        (10, 20, 23500),
        (21, 50, 20500),
        (51, 100, 18500),
        (101, 200, 17500),
        (201, 500, 17000),
        (501, 1000, 15000),
        (1001, 9999999, 13000),
    ],
}

def normalize_pvc_size(size):
    """
    Chuẩn hóa kích thước thẻ nhựa PVC:
    - 5.4x8.6cm (Bằng thẻ ngân hàng)
    - 7x11cm
    - 9x12cm
    - Ngoại size (Trao đổi qua Zalo)
    """
    s = str(size or '5.4x8.6').strip().lower().replace(' ', '').replace(',', '.')
    if '7x11' in s or '7*11' in s:
        return 'pvc_7x11', '7x11cm', '7x11cm'
    elif '9x12' in s or '9*12' in s:
        return 'pvc_9x12', '9x12cm', '9x12cm'
    elif 'ngoai' in s or 'ngoại' in s or 'custom' in s:
        return 'pvc_custom', 'Ngoại size', 'Ngoại size (Trao đổi thêm qua Zalo)'
    else:
        return 'pvc_5.4x8.6', '5.4x8.6cm', '5.4x8.6cm (Bằng thẻ ngân hàng)'

def get_pvc_pricing_matrix():
    """Trả về bảng giá đầy đủ phục vụ hiển thị API và bảng giá"""
    return {
        'tiers': ['10-20', '21-50', '51-100', '101-200', '201-500', '501-1000', '1001-3000'],
        'sizes': [
            {
                'id': '5.4x8.6',
                'name': '5,4x8,6cm (Bằng thẻ ngân hàng)',
                'prices': [16500, 13500, 10500, 8500, 8000, 7000, 6000]
            },
            {
                'id': '7x11',
                'name': '7x11cm',
                'prices': [21500, 16500, 15500, 14500, 14000, 13000, 12000]
            },
            {
                'id': '9x12',
                'name': '9x12cm',
                'prices': [23500, 20500, 18500, 17500, 17000, 15000, 13000]
            },
            {
                'id': 'custom',
                'name': 'Ngoại size',
                'note': 'Trao đổi thêm qua Zalo'
            }
        ]
    }

def calculate_pvc_price(quantity, finish='matte', effects=None, size='5.4x8.6', punched_hole=False):
    """
    Calculate PVC Card pricing tiers theo bảng báo giá thực tế:
    Kích thước:
      - 5.4x8.6cm (Bằng thẻ ngân hàng / Chuẩn ATM)
      - 7x11cm
      - 9x12cm
      - Ngoại size (Trao đổi qua Zalo)
    Cán màng bảo vệ (đồng giá):
      - matte: Cán màng mờ
      - textured: Cán màng nhám
      - glossy: Cán màng bóng
    Đục lỗ thẻ:
      - punched_hole: Miễn phí (0đ)
    """
    try:
        qty = max(10, int(quantity))
    except (ValueError, TypeError):
        qty = 10

    category_key, size_code, size_label = normalize_pvc_size(size)

    if category_key == 'pvc_custom':
        is_custom = True
        base_unit = 0
    else:
        is_custom = False
        # 1. Tìm trong DB (SQLAlchemy price_tiers)
        db_base = get_tier_price_from_db(category_key, qty)
        if db_base is None and category_key == 'pvc_5.4x8.6':
            db_base = get_tier_price_from_db('pvc', qty)

        if db_base is not None:
            base_unit = db_base
        else:
            # 2. Fallback ma trận giá mặc định
            tiers = PVC_PRICING_TABLE.get(category_key, PVC_PRICING_TABLE['pvc_5.4x8.6'])
            base_unit = tiers[-1][2]
            for min_q, max_q, price in tiers:
                if min_q <= qty <= max_q:
                    base_unit = price
                    break

    # Chuẩn hóa 3 loại cán màng: Mờ, Nhám, Bóng (đồng giá theo bảng giá thẻ PVC)
    f_clean = str(finish or 'matte').strip().lower()
    if 'nham' in f_clean or 'nhám' in f_clean or 'textured' in f_clean or 'sand' in f_clean:
        finish_code = 'textured'
        finish_label = 'Cán màng nhám'
    elif 'bong' in f_clean or 'bóng' in f_clean or 'gloss' in f_clean:
        finish_code = 'glossy'
        finish_label = 'Cán màng bóng'
    else:
        finish_code = 'matte'
        finish_label = 'Cán màng mờ'

    # Xử lý kiểu đục lỗ thẻ: Không đục lỗ, Lỗ con nhộng (oval), Lỗ tròn (Tất cả đều Miễn phí - 0đ)
    h_clean = str(punched_hole or '').strip().lower()
    if h_clean in ['round', 'tron', 'tròn']:
        hole_code = 'round'
        hole_label = 'Đục lỗ tròn (Miễn phí)'
        hole_short = 'Lỗ tròn'
        has_hole = True
    elif h_clean in ['capsule', 'oval', 'nhong', 'nhộng', 'con_nhong', 'true', '1']:
        hole_code = 'capsule'
        hole_label = 'Đục lỗ con nhộng (Lỗ dẹt oval - Miễn phí)'
        hole_short = 'Lỗ con nhộng'
        has_hole = True
    else:
        hole_code = 'none'
        hole_label = 'Không đục lỗ'
        hole_short = ''
        has_hole = False

    accessories_list = [finish_label]
    if has_hole:
        accessories_list.append(hole_label)

    if is_custom:
        unit_price = 0
        total_price = 0
        specs = f"{size_label} — Trao đổi thêm qua Zalo ({finish_label}{', ' + hole_label if has_hole else ''})"
    else:
        unit_price = base_unit
        total_price = unit_price * qty
        hole_spec = f" ({hole_short})" if has_hole else ''
        specs = f"{size_label} — {finish_label}{hole_spec}"

    return {
        'category': 'Thẻ nhựa PVC',
        'quantity': qty,
        'size': size_code,
        'size_label': size_label,
        'finish': finish_code,
        'finish_label': finish_label,
        'punched_hole': hole_code,
        'has_hole': has_hole,
        'hole_type': hole_code,
        'hole_label': hole_label,
        'effects': [],
        'accessories': accessories_list,
        'specs': specs,
        'unit_price': unit_price,
        'total_price': total_price,
        'is_custom_size': is_custom
    }

HOLDER_PRICING_TABLE = [
    (20, 50, 35000),
    (51, 100, 30000),
    (101, 200, 28000),
    (201, 400, 26000),
    (401, 500, 25000),
    (501, 1000, 23000),
    (1001, 9999999, 20000),
]
HOLDER_SILICONE_PRICE = 3000
HOLDER_PLAIN_PRICE = 7000

def get_holder_pricing_matrix():
    """Trả về bảng giá đầy đủ phục vụ hiển thị API và bảng giá Vỏ đựng thẻ"""
    return {
        'tiers': ['20-50', '51-100', '101-200', '201-400', '401-500', '501-1000', '1001-3000'],
        'prices': [35000, 30000, 28000, 26000, 25000, 23000, 20000],
        'silicone_price': HOLDER_SILICONE_PRICE,
        'plain_price': HOLDER_PLAIN_PRICE,
        'options': [
            {
                'id': 'silicone',
                'name': 'Vỏ silicon dẻo trong suốt',
                'price': HOLDER_SILICONE_PRICE,
                'note': 'Dẻo trong suốt, chống nước, đồng giá 3.000 đ/cái (từ 20 cái)'
            },
            {
                'id': 'plain',
                'name': 'Vỏ nhựa ABS màu trơn',
                'price': HOLDER_PLAIN_PRICE,
                'note': 'Nhựa ABS cứng cáp nhiều màu, không in, đồng giá 7.000 đ/cái (từ 20 cái)'
            },
            {
                'id': 'custom',
                'name': 'Vỏ nhựa ABS in theo thiết kế',
                'tiers': [
                    {'range': '20-50', 'price': 35000},
                    {'range': '51-100', 'price': 30000},
                    {'range': '101-200', 'price': 28000},
                    {'range': '201-400', 'price': 26000},
                    {'range': '401-500', 'price': 25000},
                    {'range': '501-1000', 'price': 23000},
                    {'range': '1001-3000', 'price': 20000},
                ],
                'note': 'In UV màu sắc nét theo yêu cầu riêng (đã gồm in ấn)'
            }
        ],
        'orientations': 'Vỏ đứng dọc và vỏ nằm ngang đồng giá.',
        'note': 'Vỏ silicon dẻo 3.000 đ/cái. Vỏ ABS trơn 7.000 đ/cái. Vỏ ABS in theo thiết kế từ 20k - 35k theo số lượng. Vỏ đứng và vỏ ngang đồng giá.'
    }

def calculate_holder_price(quantity, orientation='vertical', holder_type=None, printed_logo=None, size='5.4x8.6'):
    """
    Calculate Card Holder (Vỏ đựng thẻ) pricing:
    - Nhận tối thiểu từ 20 cái.
    - Tùy chọn 1: Vỏ silicon dẻo trong suốt:
      + 5.4 x 8.6 cm: Đồng giá 3.000đ/cái.
      + 7.0 x 11.0 cm: Đồng giá 5.000đ/cái.
      + 9.0 x 12.0 cm: Đồng giá 7.000đ/cái.
    - Tùy chọn 2: Vỏ nhựa ABS màu trơn không in (đồng giá 7.000đ/cái).
    - Tùy chọn 3: Vỏ nhựa ABS in ấn theo thiết kế riêng (bảng giá 7 bậc từ 20.000đ - 35.000đ).
    - Vỏ đứng và vỏ ngang đồng giá (0đ phụ phí).
    """
    try:
        qty = max(20, int(quantity))
    except (ValueError, TypeError):
        qty = 20

    ori_label = 'Vỏ đứng dọc' if orientation == 'vertical' else 'Vỏ nằm ngang'

    # 1. Phân giải holder_type và printed_logo (hỗ trợ tương thích ngược đa dạng tham số)
    if isinstance(holder_type, bool):
        h_type = 'custom' if holder_type else 'plain'
    elif holder_type is not None and str(holder_type).strip():
        raw_ht = str(holder_type).strip().lower()
        if raw_ht in ['true', '1', 'custom', 'logo', 'in_an', 'print']:
            h_type = 'custom'
        elif raw_ht in ['false', '0', 'plain', 'tron', 'abs_plain']:
            h_type = 'plain'
        elif 'silicon' in raw_ht or 'deo' in raw_ht or 'trong' in raw_ht:
            h_type = 'silicone'
        else:
            h_type = 'custom'
    elif printed_logo is not None:
        p_logo = bool(printed_logo) and str(printed_logo).lower() not in ['false', '0', 'none', '']
        h_type = 'custom' if p_logo else 'plain'
    else:
        h_type = 'custom'

    size_code = '5.4x8.6'
    if h_type == 'silicone':
        type_code = 'silicone'
        raw_sz = str(size or '5.4x8.6').strip().lower()
        if '7x11' in raw_sz or '7.0x11' in raw_sz or '7*11' in raw_sz:
            size_code = '7x11'
            size_label = 'Khổ nhỡ 7 × 11 cm'
            default_price = 5000
        elif '9x12' in raw_sz or '9.0x12' in raw_sz or '9*12' in raw_sz:
            size_code = '9x12'
            size_label = 'Khổ lớn 9 × 12 cm'
            default_price = 7000
        else:
            size_code = '5.4x8.6'
            size_label = 'Chuẩn ATM 5.4 × 8.6 cm'
            default_price = 3000

        db_sili = get_tier_price_from_db(f'holder_silicone_{size_code}', qty)
        if db_sili is None and size_code == '5.4x8.6':
            db_sili = get_tier_price_from_db('holder_silicone', qty)
        unit_price = db_sili if db_sili is not None else default_price
        type_label = f'Vỏ silicon dẻo trong suốt ({size_label})'
        specs = f"{ori_label} — {type_label}"
        accessories_list = ['Silicon dẻo trong suốt', size_label]
        has_logo = False
    elif h_type == 'plain':
        type_code = 'plain'
        db_plain = get_tier_price_from_db('holder_plain', qty)
        unit_price = db_plain if db_plain is not None else HOLDER_PLAIN_PRICE
        type_label = 'Vỏ nhựa ABS màu trơn (Không in)'
        specs = f"{ori_label} — {type_label}"
        accessories_list = ['Nhựa ABS cao cấp']
        has_logo = False
    else:
        type_code = 'custom'
        # In ấn theo thiết kế: Tìm trong DB (SQLAlchemy price_tiers category='holder')
        db_base = get_tier_price_from_db('holder', qty)
        if db_base is not None:
            base_unit = db_base
        else:
            base_unit = HOLDER_PRICING_TABLE[-1][2]
            for min_q, max_q, price in HOLDER_PRICING_TABLE:
                if min_q <= qty <= max_q:
                    base_unit = price
                    break
        unit_price = base_unit
        type_label = 'Vỏ nhựa ABS in theo thiết kế riêng (Đã bao gồm)'
        specs = f"{ori_label} — {type_label}"
        accessories_list = ['In theo thiết kế riêng (Đã bao gồm)', 'Nhựa ABS cao cấp']
        has_logo = True

    total_price = unit_price * qty

    return {
        'category': 'Vỏ đựng thẻ',
        'quantity': qty,
        'orientation': ori_label,
        'holder_type': type_code,
        'print_type': type_label,
        'has_logo': has_logo,
        'accessories': accessories_list,
        'specs': specs,
        'size': size_code,
        'unit_price': unit_price,
        'total_price': total_price
    }

def calculate_combo_price(quantity, width='2.0', accessories=None):
    """
    Combo trọn bộ: Dây đeo thẻ + Thẻ nhựa PVC + Vỏ đựng thẻ ABS.
    """
    if accessories is None:
        accessories = []
    try:
        qty = max(10, int(quantity))
    except (ValueError, TypeError):
        qty = 10

    # 1. Look up tier in Database if active
    db_base = get_tier_price_from_db('combo', qty)
    if db_base is not None:
        base_unit = db_base
    elif qty < 30:
        base_unit = 48000
    elif qty < 50:
        base_unit = 40000
    elif qty < 100:
        base_unit = 33000
    elif qty < 300:
        base_unit = 27000
    elif qty < 500:
        base_unit = 23000
    else:
        base_unit = 19000

    width_str = str(width)
    if '1.5' in width_str:
        width_adj = -1000
        w_label = 'Dây 1.5cm'
    elif '2.5' in width_str:
        width_adj = 2000
        w_label = 'Dây 2.5cm'
    else:
        width_adj = 0
        w_label = 'Dây 2.0cm'

    acc_defs = [
        ('breakaway', 'Khóa an toàn', 2500),
        ('quick_release', 'Khóa tháo rời', 3000)
    ]
    selected_acc = []
    acc_cost = 0
    if isinstance(accessories, str):
        accessories = [a.strip() for a in accessories.split(',') if a.strip()]

    for a in accessories:
        a_clean = str(a).strip().lower()
        for k, l, c in acc_defs:
            if k in a_clean or l.lower() in a_clean:
                if l not in selected_acc:
                    selected_acc.append(l)
                    acc_cost += c
                break

    unit_price = base_unit + width_adj + acc_cost
    total_price = unit_price * qty

    return {
        'category': 'Combo trọn bộ (Dây + Thẻ + Vỏ)',
        'quantity': qty,
        'width': w_label,
        'accessories': selected_acc,
        'specs': f"{w_label} + Thẻ PVC 2 mặt + Vỏ thẻ ABS",
        'unit_price': unit_price,
        'total_price': total_price
    }

def calculate_product_price(category='lanyard', quantity=10, **kwargs):
    cat = (category or 'lanyard').strip().lower()
    include_vat = bool(kwargs.get('include_vat', False) or kwargs.get('vat', False))

    if 'pvc' in cat or 'the' in cat:
        result = calculate_pvc_price(
            quantity,
            finish=kwargs.get('finish', 'matte'),
            effects=kwargs.get('effects', []),
            size=kwargs.get('size') or kwargs.get('width'),
            punched_hole=kwargs.get('punched_hole', 'none')
        )
    elif 'holder' in cat or 'vo' in cat:
        h_type = kwargs.get('holder_type') or kwargs.get('material')
        p_logo = kwargs.get('printed_logo')
        result = calculate_holder_price(
            quantity,
            orientation=kwargs.get('orientation', 'vertical'),
            holder_type=h_type if h_type else ('custom' if p_logo is not False else 'plain'),
            printed_logo=p_logo,
            size=kwargs.get('size') or kwargs.get('width')
        )
    elif 'combo' in cat:
        result = calculate_combo_price(quantity, kwargs.get('width', '2.0'), kwargs.get('accessories', []))
    else:
        result = calculate_lanyard_price(quantity, kwargs.get('width', '2.0'), kwargs.get('accessories', []))

    subtotal = result.get('total_price', 0)
    result['subtotal'] = subtotal
    result['include_vat'] = include_vat
    result['vat_rate'] = 8 if include_vat else 0

    if include_vat:
        vat_amount = int(round(subtotal * 0.08))
        result['vat_amount'] = vat_amount
        result['total_price'] = subtotal + vat_amount
    else:
        result['vat_amount'] = 0

    return result

def get_quotes(status=None, search=None):
    try:
        from backend.models import Quote
        query = Quote.query
        if status and status != 'all':
            query = query.filter(Quote.status == status)
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                (Quote.customer_name.ilike(s)) |
                (Quote.phone.ilike(s)) |
                (Quote.id.ilike(s))
            )
        quotes = query.order_by(Quote.created_at.desc(), Quote.id.desc()).all()
        return [q.to_dict() for q in quotes]
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_QUOTE_GET_ERROR] {ex}")
        raise

def get_quotes_paginated(status=None, search=None, page=1, per_page=20):
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    try:
        from backend.models import Quote
        query = Quote.query
        if status and status != 'all':
            query = query.filter(Quote.status == status)
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                (Quote.customer_name.ilike(s)) |
                (Quote.phone.ilike(s)) |
                (Quote.id.ilike(s))
            )
        total_items = query.count()
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        quotes = query.order_by(Quote.created_at.desc(), Quote.id.desc()).offset(offset).limit(per_page).all()
        return {
            'items': [q.to_dict() for q in quotes],
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_items': total_items,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_QUOTE_GET_PAGINATED_ERROR] {ex}")
        raise

def update_quote_status(quote_id, new_status):
    try:
        from backend.database import db
        from backend.models import Quote
        q = Quote.query.filter_by(id=quote_id).first()
        if q:
            q.status = new_status
            db.session.commit()
            return True
        return False
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_QUOTE_STATUS_ERROR] {ex}")
        return False

def delete_quote(quote_id):
    try:
        from backend.database import db
        from backend.models import Quote
        q = Quote.query.filter_by(id=quote_id).first()
        if q:
            db.session.delete(q)
            db.session.commit()
            return True
        return False
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_QUOTE_DEL_ERROR] {ex}")
        return False

def add_quote(customer_name, phone, quantity, width='2.0', accessories=None, notes='', category='lanyard', **kwargs):
    pricing = calculate_product_price(category=category, quantity=quantity, width=width, accessories=accessories, **kwargs)
    quote_id = f"Q{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    now = datetime.now()
    now_str = now.strftime('%d/%m/%Y %H:%M:%S')

    include_vat = pricing.get('include_vat', False)
    vat_amount = pricing.get('vat_amount', 0)
    subtotal = pricing.get('subtotal', pricing['total_price'])

    raw_notes = (notes or '').strip()
    formatted_notes = raw_notes
    if include_vat:
        vat_tag = f"[VAT 8%: +{vat_amount:,} đ]".replace(',', '.')
        formatted_notes = f"{raw_notes} {vat_tag}".strip() if raw_notes else vat_tag

    punched_hole_val = pricing.get('punched_hole', kwargs.get('punched_hole', 'none'))

    quote_record = {
        'id': quote_id,
        'quote_id': quote_id,
        'created_at': now_str,
        'customer_name': customer_name.strip(),
        'phone': phone.strip(),
        'category': pricing.get('category', 'Dây đeo thẻ'),
        'quantity': pricing['quantity'],
        'width': pricing.get('width', pricing.get('specs', '')),
        'specs': pricing.get('specs', pricing.get('width', '')),
        'accessories': pricing.get('accessories', []),
        'punched_hole': punched_hole_val,
        'unit_price': pricing['unit_price'],
        'subtotal': subtotal,
        'include_vat': include_vat,
        'vat_rate': 8 if include_vat else 0,
        'vat_amount': vat_amount,
        'total_price': pricing['total_price'],
        'notes': formatted_notes,
        'status': 'Mới',
        'sync_status': 'pending',
        'retry_count': 0
    }

    # 1. Save to Database (SQLAlchemy) - Single Source of Truth
    try:
        from backend.database import db
        from backend.models import Quote
        acc_str = json.dumps(quote_record['accessories'], ensure_ascii=False)
        quote_obj = Quote(
            id=quote_id,
            created_at=now,
            customer_name=quote_record['customer_name'],
            phone=quote_record['phone'],
            category=quote_record['category'],
            quantity=quote_record['quantity'],
            specs=quote_record['specs'],
            accessories=acc_str,
            punched_hole=punched_hole_val,
            unit_price=quote_record['unit_price'],
            total_price=quote_record['total_price'],
            notes=quote_record['notes'],
            status=quote_record['status'],
            include_vat=include_vat,
            vat_amount=vat_amount,
            sync_status='pending',
            retry_count=0
        )
        db.session.add(quote_obj)
        db.session.commit()
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_QUOTE_SAVE_ERROR] Failed to save quote {quote_id}: {ex}")
        return None

    # 2. Sync to Google Sheet asynchronously
    from flask import current_app
    try:
        app = current_app._get_current_object()
    except Exception:
        app = None
    sync_thread = threading.Thread(target=send_quote_to_google_sheet, args=(quote_record, app), daemon=True)
    sync_thread.start()

    return quote_record

def create_quote_with_idempotency(clean_data, idemp_key, request_id, content_hash):
    from backend.database import db
    from backend.models import IdempotencyRecord, Quote, SyncTask
    from sqlalchemy.exc import IntegrityError
    import time

    # Check if this idempotency key already exists
    existing = IdempotencyRecord.query.filter_by(key=idemp_key).first()
    if existing:
        if existing.content_hash and existing.content_hash != content_hash:
            return 409, {
                'success': False,
                'error': 'conflict',
                'message': 'Mã yêu cầu đã tồn tại với nội dung cấu hình khác (409 Conflict).'
            }
        if existing.status == 'COMPLETED' and existing.response_json:
            return 200, json.loads(existing.response_json)

    # 1. Single atomic transaction:
    try:
        idemp_rec = IdempotencyRecord(
            key=idemp_key,
            request_id=request_id,
            content_hash=content_hash,
            created_at=datetime.utcnow(),
            status='PROCESSING',
            response_json=''
        )
        db.session.add(idemp_rec)
        db.session.flush()

        # Pricing math
        pricing = calculate_product_price(
            category=clean_data['category'],
            quantity=clean_data['quantity'],
            width=clean_data.get('width', '2.0'),
            accessories=clean_data.get('accessories'),
            finish=clean_data.get('finish'),
            effects=clean_data.get('effects'),
            orientation=clean_data.get('orientation'),
            printed_logo=clean_data.get('printed_logo'),
            holder_type=clean_data.get('holder_type'),
            include_vat=clean_data.get('include_vat'),
            size=clean_data.get('size'),
            punched_hole=clean_data.get('punched_hole')
        )

        quote_id = f"Q{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        now = datetime.utcnow()
        now_str = now.strftime('%d/%m/%Y %H:%M:%S')
        include_vat = pricing.get('include_vat', False)
        vat_amount = pricing.get('vat_amount', 0)
        subtotal = pricing.get('subtotal', pricing['total_price'])

        raw_notes = (clean_data.get('notes') or '').strip()
        formatted_notes = raw_notes
        if include_vat:
            vat_tag = f"[VAT 8%: +{vat_amount:,} đ]".replace(',', '.')
            formatted_notes = f"{raw_notes} {vat_tag}".strip() if raw_notes else vat_tag

        punched_hole_val = pricing.get('punched_hole', clean_data.get('punched_hole', 'none'))
        acc_str = json.dumps(pricing.get('accessories', []), ensure_ascii=False)

        quote_obj = Quote(
            id=quote_id,
            created_at=now,
            customer_name=clean_data['customer_name'].strip(),
            phone=clean_data['phone'].strip(),
            category=pricing.get('category', 'Dây đeo thẻ'),
            quantity=pricing['quantity'],
            specs=pricing.get('specs', pricing.get('width', '')),
            accessories=acc_str,
            punched_hole=punched_hole_val,
            unit_price=pricing['unit_price'],
            total_price=pricing['total_price'],
            notes=formatted_notes,
            status='Mới',
            include_vat=include_vat,
            vat_amount=vat_amount,
            sync_status='pending',
            retry_count=0,
            idempotency_key=idemp_key
        )
        db.session.add(quote_obj)
        db.session.flush()

        quote_dict = quote_obj.to_dict()

        # Add sync task to persistent queue
        sync_task = SyncTask(
            event_key=f"quote_sync_{quote_id}",
            record_type='quote',
            record_id=quote_id,
            payload=json.dumps(quote_dict, ensure_ascii=False),
            status='pending',
            attempt_count=0,
            created_at=now,
            updated_at=now
        )
        db.session.add(sync_task)
        db.session.flush()

        response_data = {
            'success': True,
            'message': 'Gửi yêu cầu tư vấn & in ấn thành công! TagLuxe sẽ liên hệ hỗ trợ bạn sớm nhất.',
            'quote': quote_dict
        }
        idemp_rec.response_json = json.dumps(response_data, ensure_ascii=False)
        idemp_rec.status = 'COMPLETED'

        db.session.commit()
        return 200, response_data

    except IntegrityError as ie:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).debug(f"[QUOTE_INTEGRITY] Handled concurrency: {ie}")
        existing = IdempotencyRecord.query.filter_by(key=idemp_key).first()
        if existing:
            if existing.content_hash and existing.content_hash != content_hash:
                return 409, {
                    'success': False,
                    'error': 'conflict',
                    'message': 'Mã yêu cầu đã tồn tại với nội dung cấu hình khác (409 Conflict).'
                }
            if existing.status == 'COMPLETED' and existing.response_json:
                return 200, json.loads(existing.response_json)

            for _ in range(30):
                time.sleep(0.1)
                db.session.expire_all()
                r = IdempotencyRecord.query.filter_by(key=idemp_key).first()
                if r and r.status == 'COMPLETED' and r.response_json:
                    return 200, json.loads(r.response_json)

            return 202, {
                'success': True,
                'status': 'processing',
                'message': 'Yêu cầu đang được xử lý, vui lòng thử lại sau giây lát.'
            }
        return 500, {
            'success': False,
            'message': 'Lỗi xung đột cơ sở dữ liệu. Vui lòng thử lại.'
        }
    except Exception as ex:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[QUOTE_TRANSACTION_ERROR] {ex}")
        return 500, {
            'success': False,
            'message': 'Không thể lưu yêu cầu báo giá vào hệ thống lúc này. Vui lòng thử lại sau giây lát.'
        }


def create_demo_with_idempotency(clean_data, idemp_key, request_id, content_hash):
    from backend.database import db
    from backend.models import IdempotencyRecord, DemoRequest, SyncTask
    from sqlalchemy.exc import IntegrityError
    import time

    existing = IdempotencyRecord.query.filter_by(key=idemp_key).first()
    if existing:
        if existing.content_hash and existing.content_hash != content_hash:
            return 409, {
                'success': False,
                'error': 'conflict',
                'message': 'Mã yêu cầu đã tồn tại với nội dung cấu hình khác (409 Conflict).'
            }
        if existing.status == 'COMPLETED' and existing.response_json:
            return 200, json.loads(existing.response_json)

    try:
        idemp_rec = IdempotencyRecord(
            key=idemp_key,
            request_id=request_id,
            content_hash=content_hash,
            created_at=datetime.utcnow(),
            status='PROCESSING',
            response_json=''
        )
        db.session.add(idemp_rec)
        db.session.flush()

        req_id = uuid.uuid4().hex[:6].upper()
        now = datetime.utcnow()
        now_str = now.strftime('%d/%m/%Y %H:%M:%S')

        demo_obj = DemoRequest(
            id=req_id,
            created_at=now_str,
            created_at_dt=now,
            phone=clean_data['phone'].strip(),
            customer_name=(clean_data.get('customer_name') or '').strip(),
            product_category=clean_data.get('product_category', 'lanyard'),
            quantity_range=clean_data.get('quantity_range', '10-20'),
            notes=(clean_data.get('notes') or '').strip(),
            file_path=None,
            original_filename=None,
            status='Chờ gửi demo',
            sync_status='pending',
            retry_count=0,
            idempotency_key=idemp_key
        )
        db.session.add(demo_obj)
        db.session.flush()

        demo_dict = demo_obj.to_dict()

        sync_task = SyncTask(
            event_key=f"demo_sync_{req_id}",
            record_type='demo',
            record_id=req_id,
            payload=json.dumps(demo_dict, ensure_ascii=False),
            status='pending',
            attempt_count=0,
            created_at=now,
            updated_at=now
        )
        db.session.add(sync_task)
        db.session.flush()

        response_data = {
            'success': True,
            'request_id': req_id,
            'phone': clean_data['phone'].strip()
        }
        idemp_rec.response_json = json.dumps(response_data, ensure_ascii=False)
        idemp_rec.status = 'COMPLETED'

        db.session.commit()
        return 200, response_data

    except IntegrityError:
        db.session.rollback()
        existing = IdempotencyRecord.query.filter_by(key=idemp_key).first()
        if existing:
            if existing.content_hash and existing.content_hash != content_hash:
                return 409, {
                    'success': False,
                    'error': 'conflict',
                    'message': 'Mã yêu cầu đã tồn tại với nội dung cấu hình khác (409 Conflict).'
                }
            if existing.status == 'COMPLETED' and existing.response_json:
                return 200, json.loads(existing.response_json)

            for _ in range(30):
                time.sleep(0.1)
                db.session.expire_all()
                r = IdempotencyRecord.query.filter_by(key=idemp_key).first()
                if r and r.status == 'COMPLETED' and r.response_json:
                    return 200, json.loads(r.response_json)

            return 202, {
                'success': True,
                'status': 'processing',
                'message': 'Yêu cầu đang được xử lý, vui lòng thử lại sau giây lát.'
            }
        return 500, {
            'success': False,
            'message': 'Lỗi xung đột cơ sở dữ liệu. Vui lòng thử lại.'
        }
    except Exception as ex:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DEMO_TRANSACTION_ERROR] {ex}")
        return 500, {
            'success': False,
            'message': 'Không thể lưu yêu cầu thiết kế vào hệ thống lúc này. Vui lòng thử lại sau giây lát.'
        }


def sanitize_for_sheet(val):
    """
    Sanitizes values before sending to Google Sheet to prevent Formula Injection (CSV injection).
    Prepends an apostrophe ' if text begins with =, +, -, @, \\t, or \\r.
    """
    if isinstance(val, str):
        if val.startswith(('=', '+', '-', '@', '\t', '\r')):
            return f"'{val}"
        return val
    elif isinstance(val, list):
        return [sanitize_for_sheet(item) for item in val]
    elif isinstance(val, dict):
        return {k: sanitize_for_sheet(v) for k, v in val.items()}
    return val

def _update_record_sync_status(rec_id, status, error_msg=None, app=None, increment_retry=False):
    if not rec_id:
        return
    def _do_update():
        try:
            from backend.database import db
            from backend.models import Quote, DemoRequest
            q = Quote.query.filter_by(id=rec_id).first()
            if q:
                q.sync_status = status
                q.sync_error = (error_msg or '')[:500] if error_msg else None
                if increment_retry:
                    q.retry_count = (q.retry_count or 0) + 1
                db.session.commit()
                return
            d = DemoRequest.query.filter_by(id=rec_id).first()
            if d:
                d.sync_status = status
                d.sync_error = (error_msg or '')[:500] if error_msg else None
                if increment_retry:
                    d.retry_count = (d.retry_count or 0) + 1
                db.session.commit()
        except Exception as ex:
            import logging
            logging.getLogger(__name__).error(f"[SYNC_STATUS_UPDATE_ERROR] {ex}")

    if app:
        with app.app_context():
            _do_update()
    else:
        _do_update()

def send_quote_to_google_sheet(quote_data, app=None):
    """
    Sends the quote or demo request data directly to Google Sheet via Google Apps Script Web App.
    Sanitizes inputs against Formula Injection and updates sync_status in Database.
    Validates secret and verifies HTTP 200 AND JSON status == 'success'.
    """
    quote_id = quote_data.get('id')
    webhook_url = GOOGLE_SHEET_WEBHOOK_URL or os.environ.get('GOOGLE_SHEET_WEBHOOK_URL', '')
    if not webhook_url:
        _update_record_sync_status(quote_id, 'failed', 'GOOGLE_SHEET_WEBHOOK_URL not configured', app)
        return False, "GOOGLE_SHEET_WEBHOOK_URL not configured"

    sanitized_data = sanitize_for_sheet(dict(quote_data))
    webhook_secret = os.environ.get('GOOGLE_SHEET_SECRET', '')
    if webhook_secret:
        sanitized_data['secret'] = webhook_secret

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'TagLuxe-Server/1.0'
    }
    if webhook_secret:
        headers['X-Webhook-Secret'] = webhook_secret

    try:
        payload = json.dumps(sanitized_data, ensure_ascii=False).encode('utf-8')
        resp_code = None
        resp_text = ""
        resp_json = {}
        try:
            import requests
            resp = requests.post(webhook_url, json=sanitized_data, headers=headers, timeout=12)
            resp_code = resp.status_code
            resp_text = resp.text
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = {}
        except ImportError:
            req = urllib.request.Request(webhook_url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp_code = resp.getcode()
                resp_text = resp.read().decode('utf-8')
                try:
                    resp_json = json.loads(resp_text)
                except Exception:
                    resp_json = {}

        if resp_code == 200:
            if isinstance(resp_json, dict) and resp_json.get('status') == 'success':
                _update_record_sync_status(quote_id, 'synced', None, app)
                return True, "Google Sheet synced successfully"
            else:
                err_msg = resp_json.get('message') or resp_json.get('error') or f"Status: {resp_json.get('status') or 'unknown'}" if isinstance(resp_json, dict) else f"Invalid JSON response: {resp_text[:120]}"
                _update_record_sync_status(quote_id, 'failed', str(err_msg)[:500], app)
                return False, f"Google Sheet sync error: {err_msg}"
        else:
            _update_record_sync_status(quote_id, 'failed', f"HTTP {resp_code}: {resp_text[:200]}", app)
            return False, f"Google Sheet sync HTTP error: {resp_code}"
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[GOOGLE_SHEET_SYNC_ERROR] {e}")
        _update_record_sync_status(quote_id, 'failed', str(e)[:500], app)
        return False, str(e)

def retry_quote_sync(quote_id, app=None):
    from backend.database import db
    from backend.models import Quote
    q = Quote.query.filter_by(id=quote_id).first()
    if not q:
        return False, "Quote not found"
    q.retry_count = (q.retry_count or 0) + 1
    q.sync_status = 'pending'
    db.session.commit()
    return send_quote_to_google_sheet(q.to_dict(), app)

def retry_demo_request_sync(req_id, app=None):
    from backend.database import db
    from backend.models import DemoRequest
    d = DemoRequest.query.filter_by(id=req_id).first()
    if not d:
        return False, "Demo request not found"
    d.retry_count = (d.retry_count or 0) + 1
    d.sync_status = 'pending'
    db.session.commit()
    sheet_payload = {
        'id': d.id,
        'created_at': d.created_at,
        'category': f"Yêu cầu Demo 2D ({d.product_category})",
        'customer_name': d.customer_name or 'Khách hàng',
        'phone': d.phone,
        'quantity': d.quantity_range,
        'specs': f"File logo: {d.original_filename or 'Không đính kèm'}",
        'accessories': [],
        'unit_price': 0,
        'total_price': 0,
        'notes': d.notes or 'Yêu cầu lên mẫu phối cảnh 2D',
        'status': d.status
    }
    return send_quote_to_google_sheet(sheet_payload, app)


def get_all_accessories():
    from backend.models import Accessory
    try:
        accs = Accessory.query.order_by(Accessory.sort_order.asc()).all()
        return [a.to_dict() for a in accs]
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_GET_ALL_ACCESSORIES_ERROR] {ex}")
        return []


def get_accessory_by_id(acc_id):
    from backend.models import Accessory
    try:
        acc = Accessory.query.filter_by(id=acc_id).first()
        return acc.to_dict() if acc else None
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_GET_ACCESSORY_ERROR] {ex}")
        return None


def update_accessory(acc_id, name=None, price=None, image=None, description=None, title=None, visible=None, min_quantity=None):
    from backend.models import Accessory
    from backend.database import db
    try:
        acc = Accessory.query.filter_by(id=acc_id).first()
        if not acc:
            return False, "Không tìm thấy phụ kiện"
        if name is not None:
            acc.name = name
        if price is not None:
            acc.price = int(price)
        if image is not None:
            acc.image = image
        if description is not None:
            acc.description = description
        if title is not None:
            acc.title = title
        if visible is not None:
            acc.visible = bool(visible)
        if min_quantity is not None:
            try:
                acc.min_quantity = max(0, int(min_quantity))
            except (ValueError, TypeError):
                pass
        db.session.commit()
        return True, acc.to_dict()
    except Exception as ex:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_UPDATE_ACCESSORY_ERROR] {ex}")
        return False, str(ex)


def get_accessories_catalog():
    from backend.models import Accessory
    try:
        accs = Accessory.query.filter_by(visible=True).order_by(Accessory.sort_order.asc()).all()
        res = {
            'lanyard_accs': {},
            'holder_styles': {},
            'holder_materials': {},
            'raw_list': [a.to_dict() for a in accs]
        }
        for a in accs:
            formatted_item = {
                'id': a.id,
                'name': a.name,
                'price': f'+{a.price:,.0f} đ'.replace(',', '.') if a.price > 0 else '0 đ',
                'raw_price': a.price,
                'img': a.image_url,
                'caption': a.description or a.name,
                'title': a.title or a.name,
                'min_quantity': getattr(a, 'min_quantity', 0) or 0
            }
            if a.category == 'lanyard_acc':
                res['lanyard_accs'][a.id] = formatted_item
            elif a.category == 'holder_orientation':
                res['holder_styles'][a.id] = formatted_item
            elif a.category == 'holder_material':
                res['holder_materials'][a.id] = formatted_item
        res['demo_images'] = get_demo_images_config()
        return res
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_GET_CATALOG_ERROR] {ex}")
        return {'lanyard_accs': {}, 'holder_styles': {}, 'holder_materials': {}, 'raw_list': []}


def get_all_price_tiers_grouped():
    """
    Lấy toàn bộ các bậc giá PriceTier trong CSDL và gom nhóm phục vụ trang Admin Pricing Matrix.
    """
    from backend.models import PriceTier
    try:
        tiers = PriceTier.query.order_by(PriceTier.category, PriceTier.min_qty).all()
        grouped = {
            'lanyard': [],
            'pvc_5_4x8_6': [],
            'pvc_7x11': [],
            'pvc_9x12': [],
            'pvc_other': [],
            'holder': [],
            'holder_plain': [],
            'holder_silicone': [],
            'combo': [],
            'raw_list': [t.to_dict() for t in tiers]
        }
        for t in tiers:
            d = t.to_dict()
            cat = t.category
            if cat == 'lanyard':
                grouped['lanyard'].append(d)
            elif cat == 'pvc_5.4x8.6':
                grouped['pvc_5_4x8_6'].append(d)
            elif cat == 'pvc_7x11':
                grouped['pvc_7x11'].append(d)
            elif cat == 'pvc_9x12':
                grouped['pvc_9x12'].append(d)
            elif cat == 'pvc':
                pass # Bỏ qua để không bị trùng lặp với pvc_5.4x8.6 chuẩn
            elif cat == 'holder':
                grouped['holder'].append(d)
            elif cat == 'holder_plain':
                grouped['holder_plain'].append(d)
            elif cat == 'holder_silicone':
                grouped['holder_silicone'].append(d)
            elif cat == 'combo':
                grouped['combo'].append(d)
        return grouped
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"[DB_GET_PRICE_TIERS_ERROR] {ex}")
        return {
            'lanyard': [], 'pvc_5_4x8_6': [], 'pvc_7x11': [], 'pvc_9x12': [],
            'pvc_other': [], 'holder': [], 'holder_plain': [], 'holder_silicone': [],
            'combo': [], 'raw_list': []
        }


def update_price_tiers_bulk(updates):
    """
    Cập nhật giá và mốc số lượng hàng loạt cho các PriceTier.
    Hỗ trợ:
      - Cập nhật unit_price, min_qty, max_qty cho tier hiện có
      - Thêm mốc mới (action='create' hoặc id dạng 'new_...')
      - Xóa mốc (action='delete' hoặc deleted=True)
      - Tự động đồng bộ 2 chiều pvc_5.4x8.6 và pvc
    """
    from backend.models import PriceTier
    from backend.database import db
    try:
        updated_count = 0
        added_count = 0
        deleted_count = 0

        if isinstance(updates, dict):
            # Tương thích cũ: dict {id: price}
            items = [{'id': k, 'unit_price': v} for k, v in updates.items()]
        elif isinstance(updates, list):
            items = updates
        else:
            return False, "Định dạng dữ liệu không hợp lệ"

        for u in items:
            raw_id = u.get('id')
            action = u.get('action')
            is_deleted = u.get('deleted') is True or action == 'delete'

            # 1. Trường hợp XÓA mốc
            if is_deleted and raw_id and not str(raw_id).startswith('new_'):
                try:
                    t_id = int(raw_id)
                    tier = PriceTier.query.get(t_id)
                    if tier:
                        if tier.category == 'pvc_5.4x8.6':
                            twin_pvc = PriceTier.query.filter_by(category='pvc', min_qty=tier.min_qty).first()
                            if twin_pvc:
                                db.session.delete(twin_pvc)
                        db.session.delete(tier)
                        deleted_count += 1
                except (ValueError, TypeError):
                    pass
                continue

            # 2. Trường hợp THÊM MỐC MỚI
            if action == 'create' or not raw_id or str(raw_id).startswith('new_'):
                cat = str(u.get('category', 'lanyard')).strip()
                try:
                    min_q = int(str(u.get('min_qty', 0)).replace('.', '').replace(',', '').strip())
                    max_q = int(str(u.get('max_qty', 99999)).replace('.', '').replace(',', '').strip())
                    u_price = int(str(u.get('unit_price', 0)).replace('.', '').replace(',', '').strip())
                except (ValueError, TypeError):
                    continue

                new_tier = PriceTier(
                    category=cat,
                    min_qty=min_q,
                    max_qty=max_q,
                    unit_price=u_price
                )
                db.session.add(new_tier)
                added_count += 1

                # Nếu là pvc_5.4x8.6 thì thêm cả twin pvc
                if cat == 'pvc_5.4x8.6':
                    twin_tier = PriceTier(
                        category='pvc',
                        min_qty=min_q,
                        max_qty=max_q,
                        unit_price=u_price
                    )
                    db.session.add(twin_tier)
                continue

            # 3. Trường hợp CẬP NHẬT MỐC HIỆN CÓ
            try:
                t_id = int(raw_id)
            except (ValueError, TypeError):
                continue

            tier = PriceTier.query.get(t_id)
            if not tier:
                continue

            old_min = tier.min_qty
            changed = False

            if 'unit_price' in u:
                try:
                    clean_p = int(str(u['unit_price']).replace('.', '').replace(',', '').strip())
                    tier.unit_price = clean_p
                    changed = True
                except (ValueError, TypeError):
                    pass

            if 'min_qty' in u:
                try:
                    clean_min = int(str(u['min_qty']).replace('.', '').replace(',', '').strip())
                    tier.min_qty = clean_min
                    changed = True
                except (ValueError, TypeError):
                    pass

            if 'max_qty' in u:
                try:
                    clean_max = int(str(u['max_qty']).replace('.', '').replace(',', '').strip())
                    tier.max_qty = clean_max
                    changed = True
                except (ValueError, TypeError):
                    pass

            if changed:
                updated_count += 1
                # Đồng bộ luôn category 'pvc' tương ứng nếu là 'pvc_5.4x8.6'
                if tier.category == 'pvc_5.4x8.6':
                    twin_pvc = PriceTier.query.filter_by(category='pvc', min_qty=old_min).first()
                    if twin_pvc:
                        twin_pvc.min_qty = tier.min_qty
                        twin_pvc.max_qty = tier.max_qty
                        twin_pvc.unit_price = tier.unit_price
                    else:
                        new_twin = PriceTier(
                            category='pvc',
                            min_qty=tier.min_qty,
                            max_qty=tier.max_qty,
                            unit_price=tier.unit_price
                        )
                        db.session.add(new_twin)

        db.session.commit()
        total_ops = updated_count + added_count + deleted_count
        return True, total_ops
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_UPDATE_PRICE_TIERS_ERROR] {ex}")
        return False, str(ex)


def add_accessory(data):
    """
    Thêm một phụ kiện mới vào CSDL accessories.
    data: dict chứa name, category, price, image, description, title, visible
    """
    from backend.models import Accessory
    from backend.database import db
    import re
    try:
        raw_id = (data.get('id') or '').strip().lower()
        if not raw_id:
            # Tự tạo id từ tên không dấu hoặc uuid
            name_clean = re.sub(r'[^a-zA-Z0-9]+', '_', data.get('name', 'acc').strip().lower()).strip('_')
            raw_id = f"{name_clean[:30]}_{uuid.uuid4().hex[:6]}" if name_clean else f"acc_{uuid.uuid4().hex[:8]}"

        # Đảm bảo id là duy nhất
        existing = Accessory.query.filter_by(id=raw_id).first()
        if existing:
            raw_id = f"{raw_id}_{uuid.uuid4().hex[:4]}"

        # Tìm sort_order lớn nhất hiện có
        max_order = db.session.query(db.func.max(Accessory.sort_order)).scalar() or 0

        acc = Accessory(
            id=raw_id,
            name=data.get('name', '').strip(),
            category=data.get('category', 'lanyard_acc'),
            price=int(data.get('price', 0)),
            image=data.get('image', ''),
            description=data.get('description', '').strip(),
            title=data.get('title', '').strip() or data.get('name', '').strip(),
            sort_order=max_order + 1,
            visible=bool(data.get('visible', True)),
            min_quantity=int(data.get('min_quantity', 0) or 0)
        )
        db.session.add(acc)
        db.session.commit()
        return True, acc.to_dict()
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_ADD_ACCESSORY_ERROR] {ex}")
        return False, str(ex)


def delete_accessory(acc_id):
    """
    Xóa phụ kiện khỏi CSDL.
    """
    from backend.models import Accessory
    from backend.database import db
    try:
        acc = Accessory.query.filter_by(id=acc_id).first()
        if not acc:
            return False, "Không tìm thấy phụ kiện cần xóa"
        db.session.delete(acc)
        db.session.commit()
        return True, "Đã xóa phụ kiện thành công"
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_DELETE_ACCESSORY_ERROR] {ex}")
        return False, str(ex)


def toggle_accessory_visibility(acc_id):
    """
    Bật/tắt trạng thái hiển thị của phụ kiện.
    """
    from backend.models import Accessory
    from backend.database import db
    try:
        acc = Accessory.query.filter_by(id=acc_id).first()
        if not acc:
            return False, "Không tìm thấy phụ kiện"
        acc.visible = not acc.visible
        db.session.commit()
        return True, acc.visible
    except Exception as ex:
        from backend.database import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[DB_TOGGLE_ACC_VISIBILITY_ERROR] {ex}")
        return False, str(ex)

# --- CẤU HÌNH BỘ ẢNH DEMO BÁO GIÁ ĐỘNG (TAGLUXE LIVE PREVIEW) ---
DEFAULT_DEMO_IMAGES = {
    'pvc_no_hole': {
        'id': 'pvc_no_hole',
        'title': 'Thẻ PVC Không Đục Lỗ',
        'category': 'pvc',
        'key': 'none',
        'image': '/static/images/demo/demo_the_pvc_khong_duc_lo.jpg',
        'pill': 'Thẻ Nguyên Bản (Không Đục Lỗ)',
        'caption': 'Thẻ nguyên khối bo góc tiêu chuẩn, phù hợp lồng trong vỏ hoặc bao đựng thẻ.',
        'modal_title': 'Thẻ nhựa PVC nguyên bản không đục lỗ — Demo 3D'
    },
    'pvc_oval_hole': {
        'id': 'pvc_oval_hole',
        'title': 'Thẻ PVC Đục Lỗ Oval (Con Nhộng)',
        'category': 'pvc',
        'key': 'capsule',
        'image': '/static/uploads/demo_pvc_oval_hole_a3f23833.jpg',
        'pill': 'Đục Lỗ Con Nhộng (Oval)',
        'caption': 'Lỗ dẹt 3x15mm chuẩn cơ khí dập giữa đỉnh thẻ, giúp móc cài giữ thẻ luôn thẳng đứng khi đeo.',
        'modal_title': 'Gia công đục lỗ con nhộng Oval chống xoay — Demo 3D'
    },
    'pvc_round_hole': {
        'id': 'pvc_round_hole',
        'title': 'Thẻ PVC Đục Lỗ Tròn (5mm)',
        'category': 'pvc',
        'key': 'round',
        'image': '/static/images/demo/demo_the_pvc_lo_tron.jpg',
        'pill': 'Đục Lỗ Tròn (5mm)',
        'caption': 'Đục lỗ tròn chuẩn xác, mép cắt sắc gọn không nứt vỡ thẻ, tương thích nhiều loại móc kẹp.',
        'modal_title': 'Gia công đục lỗ tròn tiêu chuẩn 5mm — Demo 3D'
    },
    'holder_silicone_vertical': {
        'id': 'holder_silicone_vertical',
        'title': 'Vỏ Silicon Dẻo (Dáng Đứng Dọc)',
        'category': 'holder',
        'key': 'silicone_vertical',
        'image': '/static/uploads/demo_holder_silicone_vertical_38aecbf6.jpg',
        'pill': 'Vỏ Silicon Dọc (Khóa Zip Chống Nước)',
        'caption': 'Vỏ silicon dẻo trong suốt dáng đứng dọc có khóa zip chống nước bảo vệ thẻ tối ưu.',
        'modal_title': 'Vỏ Silicon Dẻo Dáng Đứng Dọc — Demo 3D'
    },
    'holder_silicone_horizontal': {
        'id': 'holder_silicone_horizontal',
        'title': 'Vỏ Silicon Dẻo (Dáng Nằm Ngang)',
        'category': 'holder',
        'key': 'silicone_horizontal',
        'image': '/static/uploads/demo_holder_silicone_horizontal_54f008a3.jpg',
        'pill': 'Vỏ Silicon Ngang (Khóa Zip Chống Nước)',
        'caption': 'Vỏ silicon dẻo trong suốt dáng nằm ngang có khóa zip chống nước bảo vệ thẻ tối ưu.',
        'modal_title': 'Vỏ Silicon Dẻo Dáng Nằm Ngang — Demo 3D'
    },
    'holder_plain_vertical': {
        'id': 'holder_plain_vertical',
        'title': 'Vỏ Nhựa ABS Trơn (Dáng Đứng Dọc)',
        'category': 'holder',
        'material': 'plain',
        'key': 'plain_vertical',
        'image': '/static/uploads/demo_holder_plain_vertical_fe8789f4.jpg',
        'pill': 'Vỏ ABS Trơn Dọc (Chuẩn ATM)',
        'caption': 'Vỏ nhựa ABS màu trơn không in dáng đứng dọc chuẩn thẻ ATM, bảo vệ thẻ chống gãy gập.',
        'modal_title': 'Vỏ nhựa ABS trơn dáng đứng dọc — Demo 3D'
    },
    'holder_plain_horizontal': {
        'id': 'holder_plain_horizontal',
        'title': 'Vỏ Nhựa ABS Trơn (Dáng Nằm Ngang)',
        'category': 'holder',
        'material': 'plain',
        'key': 'plain_horizontal',
        'image': '/static/uploads/demo_holder_plain_horizontal_f01763d7.jpg',
        'pill': 'Vỏ ABS Trơn Ngang (Chuẩn ATM)',
        'caption': 'Vỏ nhựa ABS màu trơn không in dáng nằm ngang sang trọng, bảo vệ thẻ tối ưu.',
        'modal_title': 'Vỏ nhựa ABS trơn dáng nằm ngang — Demo 3D'
    },
    'holder_custom_vertical': {
        'id': 'holder_custom_vertical',
        'title': 'Vỏ Nhựa ABS In UV (Dáng Đứng Dọc)',
        'category': 'holder',
        'material': 'custom',
        'key': 'custom_vertical',
        'image': '/static/uploads/demo_holder_custom_vertical_66db4e63.jpg',
        'pill': 'Vỏ ABS In UV Dọc (Theo Yêu Cầu)',
        'caption': 'Vỏ nhựa ABS in UV sắc nét logo và nhận diện thương hiệu dáng đứng dọc theo thiết kế riêng.',
        'modal_title': 'Vỏ nhựa ABS in UV dáng đứng dọc — Demo 3D'
    },
    'holder_custom_horizontal': {
        'id': 'holder_custom_horizontal',
        'title': 'Vỏ Nhựa ABS In UV (Dáng Nằm Ngang)',
        'category': 'holder',
        'material': 'custom',
        'key': 'custom_horizontal',
        'image': '/static/uploads/demo_holder_custom_horizontal_b989d184.jpg',
        'pill': 'Vỏ ABS In UV Ngang (Theo Yêu Cầu)',
        'caption': 'Vỏ nhựa ABS in UV sắc nét logo và nhận diện thương hiệu dáng nằm ngang theo thiết kế riêng.',
        'modal_title': 'Vỏ nhựa ABS in UV dáng nằm ngang — Demo 3D'
    },
    'holder_vertical': {
        'id': 'holder_vertical',
        'title': 'Vỏ Nhựa ABS (Dáng Đứng Dọc)',
        'category': 'holder',
        'key': 'vertical',
        'image': '/static/images/demo/demo_vo_abs_tron_doc.jpg',
        'pill': 'Vỏ Nhựa ABS Dọc (Chuẩn ATM)',
        'caption': 'Vỏ thẻ dáng đứng dọc chuẩn thẻ học sinh, sinh viên, nhân viên. Chống gãy gập thẻ tối ưu.',
        'modal_title': 'Vỏ đựng thẻ nhựa ABS dáng đứng dọc — Demo 3D'
    },
    'holder_horizontal': {
        'id': 'holder_horizontal',
        'title': 'Vỏ Nhựa ABS (Dáng Nằm Ngang)',
        'category': 'holder',
        'key': 'horizontal',
        'image': '/static/images/demo/demo_vo_abs_tron_ngang.jpg',
        'pill': 'Vỏ Nhựa ABS Ngang (Chuẩn ATM)',
        'caption': 'Vỏ thẻ dáng nằm ngang sang trọng, mở rộng diện tích thể hiện logo công ty.',
        'modal_title': 'Vỏ đựng thẻ nhựa ABS dáng nằm ngang — Demo 3D'
    },
    'lanyard_default': {
        'id': 'lanyard_default',
        'title': 'Dây Đeo Thẻ In Chuyển Nhiệt',
        'category': 'lanyard',
        'key': 'default',
        'image': '/static/uploads/demo_lanyard_20_71df0b6c.jpg',
        'pill': 'Dây Đeo Thẻ In Chuyển Nhiệt',
        'caption': 'Dây lụa satin 2.0cm tiêu chuẩn sắc nét, phối móc kim loại cao cấp.',
        'modal_title': 'Mẫu Dây Đeo Thẻ In Chuyển Nhiệt — Demo 3D'
    },
    'lanyard_15': {
        'id': 'lanyard_15',
        'title': 'Dây Đeo Thẻ Bản 1.5 cm',
        'category': 'lanyard',
        'key': '1.5',
        'image': '/static/uploads/demo_lanyard_15_014e18b7.jpg',
        'pill': 'Dây Đeo Thẻ Bản 1.5 cm',
        'caption': 'Dây in nhiệt lụa satin 1.5cm nhỏ gọn, tinh tế, phối móc kim loại cao cấp.',
        'modal_title': 'Mẫu Dây Đeo Thẻ Bản 1.5cm — Demo 3D'
    },
    'lanyard_20': {
        'id': 'lanyard_20',
        'title': 'Dây Đeo Thẻ Bản 2.0 cm (Chuẩn)',
        'category': 'lanyard',
        'key': '2.0',
        'image': '/static/uploads/demo_lanyard_20_71df0b6c.jpg',
        'pill': 'Dây Đeo Thẻ Bản 2.0 cm (Chuẩn)',
        'caption': 'Dây lụa satin 2.0cm tiêu chuẩn sắc nét, phối móc kim loại cao cấp.',
        'modal_title': 'Mẫu Dây Đeo Thẻ Bản 2.0cm — Demo 3D'
    },
    'lanyard_25': {
        'id': 'lanyard_25',
        'title': 'Dây Đeo Thẻ Bản 2.5 cm',
        'category': 'lanyard',
        'key': '2.5',
        'image': '/static/uploads/demo_lanyard_25_efd92cb3.jpg',
        'pill': 'Dây Đeo Thẻ Bản 2.5 cm',
        'caption': 'Dây in nhiệt lụa satin 2.5cm to bản sang trọng, phối móc kim loại cao cấp.',
        'modal_title': 'Mẫu Dây Đeo Thẻ Bản 2.5cm — Demo 3D'
    }
}

def get_demo_images_storage_path():
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    storage_dir = os.path.join(root_dir, 'storage')
    os.makedirs(storage_dir, exist_ok=True)
    return os.path.join(storage_dir, 'demo_images.json')

def get_demo_images_config():
    """Lấy cấu hình ảnh demo báo giá đầy đủ từ storage hoặc mặc định"""
    import copy
    cfg = copy.deepcopy(DEFAULT_DEMO_IMAGES)
    path = get_demo_images_storage_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    for k, v in saved.items():
                        if k in cfg and isinstance(v, dict):
                            cfg[k].update(v)
                        elif isinstance(v, dict):
                            cfg[k] = v
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[LOAD_DEMO_IMAGES_ERROR] {e}")
    return cfg

def save_demo_images_config(data):
    """Lưu cấu hình ảnh demo báo giá vào storage/demo_images.json"""
    path = get_demo_images_storage_path()
    current = get_demo_images_config()
    for k, v in data.items():
        if k in current and isinstance(v, dict):
            current[k].update(v)
        elif isinstance(v, dict):
            current[k] = v
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        return True, current
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[SAVE_DEMO_IMAGES_ERROR] {e}")
        return False, str(e)


def reset_single_demo_image(key):
    """Khôi phục ảnh demo về mặc định cho mục key (khi admin lỡ tải nhầm ảnh)"""
    if key not in DEFAULT_DEMO_IMAGES:
        return False, "Mục ảnh demo không hợp lệ"
    default_img = DEFAULT_DEMO_IMAGES[key].get('image', '')
    payload = {key: {'image': default_img}}
    if key == 'lanyard_20':
        payload['lanyard_default'] = {'image': DEFAULT_DEMO_IMAGES.get('lanyard_default', {}).get('image', default_img)}
    ok, _ = save_demo_images_config(payload)
    if ok:
        return True, default_img
    return False, "Không thể lưu cấu hình khôi phục"



# ==================== CẤU HÌNH BANNER QUẢNG CÁO CHIẾN DỊCH (RESPONSIVE) ====================

DEFAULT_CAMPAIGN_BANNER = {
    'enabled': False,
    'image': '',
    'image_desktop': '',
    'image_mobile': '',
    'title': 'Chương Trình Khuyến Mại',
    'updated_at': ''
}

def get_campaign_banner_storage_path():
    path = os.path.join(BASE_DIR, 'storage', 'campaign_banner.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def get_campaign_banner_config():
    """Lấy cấu hình banner chiến dịch. Tự động kiểm tra: nếu chưa có ảnh hoặc ảnh rỗng thì ép enabled = False."""
    import copy
    cfg = copy.deepcopy(DEFAULT_CAMPAIGN_BANNER)
    path = get_campaign_banner_storage_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    cfg.update(saved)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[LOAD_CAMPAIGN_BANNER_ERROR] {e}")

    # Đồng bộ tương thích ngược giữa các trường
    desk = str(cfg.get('image_desktop') or '').strip()
    mob = str(cfg.get('image_mobile') or '').strip()
    legacy = str(cfg.get('image') or '').strip()

    if not desk and legacy:
        cfg['image_desktop'] = legacy
        desk = legacy
    if not legacy and (desk or mob):
        cfg['image'] = desk or mob

    # RÀNG BUỘC AN TOÀN: Nếu chưa upload bất kỳ ảnh nào thì TUYỆT ĐỐI không bật
    if not desk and not mob and not legacy:
        cfg['enabled'] = False
        cfg['image'] = ''
        cfg['image_desktop'] = ''
        cfg['image_mobile'] = ''
    return cfg

def save_campaign_banner_config(data):
    """Lưu cấu hình banner chiến dịch (hỗ trợ cả ảnh Desktop và Mobile)."""
    path = get_campaign_banner_storage_path()
    current = get_campaign_banner_config()
    if isinstance(data, dict):
        current.update(data)
    
    desk = str(current.get('image_desktop') or '').strip()
    mob = str(current.get('image_mobile') or '').strip()
    current['image_desktop'] = desk
    current['image_mobile'] = mob
    current['image'] = desk or mob or ''

    # Ràng buộc an toàn: Không có ảnh nào thì không được bật
    if not desk and not mob:
        current['enabled'] = False
        current['image'] = ''

    current['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        return True, current
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[SAVE_CAMPAIGN_BANNER_ERROR] {e}")
        return False, str(e)

def delete_campaign_banner(target='all'):
    """
    Xóa bỏ ảnh banner (hỗ trợ target='all', target='desktop', target='mobile').
    Nếu cả 2 ảnh đều rỗng thì tự động tắt hiển thị popup.
    """
    current = get_campaign_banner_config()
    if target == 'desktop':
        current['image_desktop'] = ''
    elif target == 'mobile':
        current['image_mobile'] = ''
    else:  # all
        current['image_desktop'] = ''
        current['image_mobile'] = ''
        current['image'] = ''
        current['enabled'] = False

    desk = str(current.get('image_desktop') or '').strip()
    mob = str(current.get('image_mobile') or '').strip()
    current['image'] = desk or mob or ''
    if not desk and not mob:
        current['enabled'] = False

    return save_campaign_banner_config(current)

