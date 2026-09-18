import os
from flask_sqlalchemy import SQLAlchemy
from core.config import BASE_DIR

db = SQLAlchemy()

def get_database_uri():
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url:
        # Render specifies postgres:// which SQLAlchemy 2.0 requires as postgresql://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    
    # Local fallback SQLite database
    sqlite_path = os.path.join(BASE_DIR, 'tagluxe.db')
    return f"sqlite:///{sqlite_path}"

def seed_initial_data():
    from core.models import PriceTier, Product, Quote, DemoRequest
    from core.config import DATA_FILE
    import json

    # 1. Seed Price Tiers if empty
    if PriceTier.query.count() == 0:
        tiers_data = [
            # Lanyard: 13 tiers + above 5k
            ('lanyard', 10, 21, 28000),
            ('lanyard', 22, 31, 26000),
            ('lanyard', 32, 45, 25000),
            ('lanyard', 46, 70, 20000),
            ('lanyard', 71, 120, 19000),
            ('lanyard', 121, 200, 18000),
            ('lanyard', 201, 320, 17000),
            ('lanyard', 321, 420, 16500),
            ('lanyard', 421, 530, 16000),
            ('lanyard', 531, 710, 15000),
            ('lanyard', 711, 1000, 14000),
            ('lanyard', 1001, 3000, 13000),
            ('lanyard', 3001, 5000, 12500),
            ('lanyard', 5001, 9999999, 12000),

            # PVC 5.4x8.6cm (Chuẩn thẻ ngân hàng / ATM) - Mặc định 'pvc' và 'pvc_5.4x8.6'
            ('pvc', 10, 20, 18000),
            ('pvc', 21, 50, 15000),
            ('pvc', 51, 100, 12000),
            ('pvc', 101, 200, 10000),
            ('pvc', 201, 500, 8000),
            ('pvc', 501, 1000, 7000),
            ('pvc', 1001, 9999999, 6000),

            ('pvc_5.4x8.6', 10, 20, 18000),
            ('pvc_5.4x8.6', 21, 50, 15000),
            ('pvc_5.4x8.6', 51, 100, 12000),
            ('pvc_5.4x8.6', 101, 200, 10000),
            ('pvc_5.4x8.6', 201, 500, 8000),
            ('pvc_5.4x8.6', 501, 1000, 7000),
            ('pvc_5.4x8.6', 1001, 9999999, 6000),

            # PVC 7x11cm
            ('pvc_7x11', 10, 20, 23000),
            ('pvc_7x11', 21, 50, 18000),
            ('pvc_7x11', 51, 100, 17000),
            ('pvc_7x11', 101, 200, 16000),
            ('pvc_7x11', 201, 500, 14000),
            ('pvc_7x11', 501, 1000, 13000),
            ('pvc_7x11', 1001, 9999999, 12000),

            # PVC 9x12cm
            ('pvc_9x12', 10, 20, 25000),
            ('pvc_9x12', 21, 50, 22000),
            ('pvc_9x12', 51, 100, 20000),
            ('pvc_9x12', 101, 200, 19000),
            ('pvc_9x12', 201, 500, 17000),
            ('pvc_9x12', 501, 1000, 15000),
            ('pvc_9x12', 1001, 9999999, 13000),

            # Holder (Vỏ đựng thẻ nhựa ABS - Nhận in từ 20 cái, đồng giá đứng/ngang)
            # 1. In ấn theo thiết kế yêu cầu (Bảng giá 7 bậc)
            ('holder', 20, 50, 35000),
            ('holder', 51, 100, 30000),
            ('holder', 101, 200, 28000),
            ('holder', 201, 400, 26000),
            ('holder', 401, 500, 25000),
            ('holder', 501, 1000, 23000),
            ('holder', 1001, 9999999, 20000),

            # 2. Vỏ nhựa ABS màu trơn không in (Đồng giá cố định 7.000 đ/cái cho mọi số lượng từ 20 cái)
            ('holder_plain', 20, 9999999, 7000),

            # 3. Vỏ silicon dẻo trong suốt (Đồng giá cố định 3.000 đ/cái cho mọi số lượng từ 20 cái)
            ('holder_silicone', 20, 9999999, 3000),

            # Combo
            ('combo', 10, 29, 48000),
            ('combo', 30, 49, 40000),
            ('combo', 50, 99, 33000),
            ('combo', 100, 299, 27000),
            ('combo', 300, 499, 23000),
            ('combo', 500, 9999999, 19000),
        ]
        for cat, q_min, q_max, price in tiers_data:
            db.session.add(PriceTier(category=cat, min_qty=q_min, max_qty=q_max, unit_price=price))
        db.session.commit()

    # 2. Seed Products & Quotes from data.json if products empty
    if os.path.exists(DATA_FILE) and Product.query.count() == 0:
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)

            for p in d.get('products', []):
                prod = Product(
                    id=p.get('id'),
                    name=p.get('name'),
                    category=p.get('category', 'lanyard'),
                    description=p.get('description', ''),
                    images_json=json.dumps(p.get('images', []), ensure_ascii=False),
                    width=p.get('width', ''),
                    material=p.get('material', ''),
                    min_order=p.get('min_order', 10),
                    price_type=p.get('price_type', 'contact'),
                    price=p.get('price', 0),
                    featured=p.get('featured', True),
                    visible=p.get('visible', True)
                )
                db.session.merge(prod)

            for q in d.get('quotes', []):
                acc = q.get('accessories', [])
                acc_str = json.dumps(acc, ensure_ascii=False) if isinstance(acc, list) else str(acc)
                quote_obj = Quote(
                    id=q.get('id') or q.get('quote_id'),
                    customer_name=q.get('customer_name', 'Khách hàng'),
                    phone=q.get('phone', ''),
                    category=q.get('category', 'Dây đeo thẻ'),
                    quantity=q.get('quantity', 10),
                    specs=q.get('specs') or q.get('width', ''),
                    accessories=acc_str,
                    unit_price=q.get('unit_price', 0),
                    total_price=q.get('total_price', 0),
                    notes=q.get('notes', ''),
                    status=q.get('status', 'Mới')
                )
                db.session.merge(quote_obj)

            for r in d.get('demo_requests', []):
                req_obj = DemoRequest(
                    id=r.get('id'),
                    created_at=r.get('created_at', ''),
                    phone=r.get('phone', ''),
                    customer_name=r.get('customer_name', ''),
                    product_category=r.get('product_category', 'lanyard'),
                    quantity_range=r.get('quantity_range', '10-20'),
                    notes=r.get('notes', ''),
                    file_path=r.get('file_path'),
                    original_filename=r.get('original_filename'),
                    status=r.get('status', 'Chờ gửi demo')
                )
                db.session.merge(req_obj)

            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            print(f"[DB_SEED_ERROR] {ex}")

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        from core import models  # noqa
        db.create_all()

        # Tự động bổ sung các cột mới nếu đã có bảng trước đó (Safe migration)
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                for col_sql in [
                    "ALTER TABLE quotes ADD COLUMN include_vat BOOLEAN DEFAULT 0",
                    "ALTER TABLE quotes ADD COLUMN vat_amount INTEGER DEFAULT 0"
                ]:
                    try:
                        conn.execute(text(col_sql))
                        conn.commit()
                    except Exception:
                        pass
        except Exception:
            pass

        seed_initial_data()

