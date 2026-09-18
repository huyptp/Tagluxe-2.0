import json
from datetime import datetime
from backend.database import db

class PriceTier(db.Model):
    __tablename__ = 'price_tiers'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True) # lanyard, pvc, holder, combo
    min_qty = db.Column(db.Integer, nullable=False)
    max_qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'min_qty': self.min_qty,
            'max_qty': self.max_qty,
            'unit_price': self.unit_price
        }

class Quote(db.Model):
    __tablename__ = 'quotes'

    id = db.Column(db.String(32), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False, default='Dây đeo thẻ')
    quantity = db.Column(db.Integer, nullable=False)
    specs = db.Column(db.String(255), nullable=True)
    accessories = db.Column(db.Text, nullable=True) # JSON list or string
    unit_price = db.Column(db.Integer, nullable=False, default=0)
    total_price = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Mới')
    include_vat = db.Column(db.Boolean, nullable=True, default=False)
    vat_amount = db.Column(db.Integer, nullable=True, default=0)
    sync_status = db.Column(db.String(20), nullable=False, default='pending') # pending, synced, failed
    sync_error = db.Column(db.Text, nullable=True)

    def to_dict(self):
        accs = []
        if self.accessories:
            try:
                accs = json.loads(self.accessories) if self.accessories.startswith('[') else [a.strip() for a in self.accessories.split(',') if a.strip()]
            except Exception:
                accs = [self.accessories]

        vat_amt = getattr(self, 'vat_amount', 0) or 0
        has_vat = bool(getattr(self, 'include_vat', False))
        subtotal = (self.total_price - vat_amt) if has_vat else self.total_price

        return {
            'id': self.id,
            'quote_id': self.id,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M:%S') if self.created_at else '',
            'customer_name': self.customer_name,
            'phone': self.phone,
            'category': self.category,
            'quantity': self.quantity,
            'width': self.specs,
            'specs': self.specs,
            'accessories': accs,
            'unit_price': self.unit_price,
            'subtotal': subtotal,
            'include_vat': has_vat,
            'vat_rate': 8 if has_vat else 0,
            'vat_amount': vat_amt,
            'total_price': self.total_price,
            'notes': self.notes or '',
            'status': self.status
        }

class DemoRequest(db.Model):
    __tablename__ = 'demo_requests'

    id = db.Column(db.String(32), primary_key=True)
    created_at = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    customer_name = db.Column(db.String(120), nullable=True)
    product_category = db.Column(db.String(50), nullable=False, default='lanyard')
    quantity_range = db.Column(db.String(50), nullable=False, default='10-20')
    notes = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    original_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Chờ gửi demo')
    sync_status = db.Column(db.String(20), nullable=False, default='pending') # pending, synced, failed
    sync_error = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at,
            'phone': self.phone,
            'customer_name': self.customer_name,
            'product_category': self.product_category,
            'quantity_range': self.quantity_range,
            'notes': self.notes,
            'file_path': self.file_path,
            'original_filename': self.original_filename,
            'status': self.status,
            'sync_status': self.sync_status
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    admin_user = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(80), nullable=False) # e.g. update_status, update_price, delete_product, delete_request
    target_type = db.Column(db.String(50), nullable=False) # quote, product, demo_request
    target_id = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, nullable=True) # JSON or descriptive string
    ip_address = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%d/%m/%Y %H:%M:%S') if self.timestamp else '',
            'admin_user': self.admin_user,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': self.details or '',
            'ip_address': self.ip_address or ''
        }

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    images_json = db.Column(db.Text, nullable=True)
    width = db.Column(db.String(100), nullable=True)
    material = db.Column(db.String(100), nullable=True)
    min_order = db.Column(db.Integer, default=10)
    price_type = db.Column(db.String(50), default='contact')
    price = db.Column(db.Integer, default=0)
    featured = db.Column(db.Boolean, default=True)
    visible = db.Column(db.Boolean, default=True)

    @property
    def images(self):
        if self.images_json:
            try:
                return json.loads(self.images_json)
            except Exception:
                return []
        return []

    @images.setter
    def images(self, val):
        self.images_json = json.dumps(val, ensure_ascii=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'images': self.images,
            'image': self.images[0] if self.images else '',
            'width': self.width,
            'material': self.material,
            'min_order': self.min_order,
            'price_type': self.price_type,
            'price': self.price,
            'featured': self.featured,
            'visible': self.visible
        }
