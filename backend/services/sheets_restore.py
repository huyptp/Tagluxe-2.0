"""Read missing quotes from the shop's authenticated Sheets bridge; never overwrite local work."""
import json
import re
from datetime import datetime
import requests
from sqlalchemy.exc import IntegrityError
from backend.database import db
from backend.models import Quote


class SheetsRestoreError(Exception):
    pass


def parse_sheet_quote(row):
    if not isinstance(row, dict):
        raise ValueError('Invalid record')
    def text(key, limit, required=False):
        value = str(row.get(key) or '').strip()
        if len(value) > limit or (required and not value):
            raise ValueError('Invalid field')
        return value
    identifier = text('id', 32, True)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
        raise ValueError('Invalid identifier')
    quantity = int(row['quantity'])
    total = int(row['total_price'])
    if not 1 <= quantity <= 10000000 or not 0 <= total <= 2147483647:
        raise ValueError('Invalid amount')
    created = text('created_at', 50, True)
    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y, %H:%M:%S', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            created_at = datetime.strptime(created, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError('Invalid date')
    unit_price = int(row.get('unit_price') or 0)
    vat_amount = int(row.get('vat_amount') or 0)
    if not 0 <= unit_price <= 2147483647 or not 0 <= vat_amount <= total:
        raise ValueError('Invalid pricing metadata')
    hole = row.get('punched_hole') or 'none'
    if hole not in ('none', 'round', 'capsule'):
        raise ValueError('Invalid punched hole')
    status = text('status', 50) or 'Mới'
    if status not in ('Mới', 'Đang tư vấn', 'Đã tư vấn', 'Đang chốt', 'Đã chốt', 'Đã xong', 'Đã hủy'):
        raise ValueError('Invalid status')
    return Quote(id=identifier, customer_name=text('customer_name', 120, True),
        phone=text('phone', 20, True).lstrip("'"), category=text('category', 50) or 'Dây đeo thẻ',
        created_at=created_at, quantity=quantity, total_price=total,
        unit_price=unit_price, include_vat=row.get('include_vat') is True,
        vat_amount=vat_amount, punched_hole=hole, specs=text('specs', 255),
        accessories=json.dumps(row.get('accessories') or [], ensure_ascii=False),
        notes=text('notes', 10000), status=status, sync_status='synced')


def restore_missing_quotes():
    from backend.config import GOOGLE_SHEET_WEBHOOK_URL, GOOGLE_SHEET_SECRET
    if not GOOGLE_SHEET_WEBHOOK_URL or not GOOGLE_SHEET_SECRET:
        raise SheetsRestoreError('Cần cấu hình kết nối và khóa xác thực Google Sheets để lấy lại báo giá.')
    inserted = skipped = invalid = 0
    try:
        # Old Apps Script interprets any POST as a new quote. A read-only handshake
        # MUST succeed before sending the new export action to avoid creating junk rows.
        probe = requests.get(GOOGLE_SHEET_WEBHOOK_URL, timeout=(5, 10))
        probe.raise_for_status()
        if probe.json().get('protocol') != 'tagluxe-quotes-read-v1':
            raise SheetsRestoreError('Cần cập nhật Apps Script để bật chức năng đọc lại báo giá từ Google Sheets.')
        if db.engine.dialect.name == 'sqlite':
            connection = db.session.connection()
            if not connection.connection.driver_connection.in_transaction:
                connection.exec_driver_sql('BEGIN')
        cursor = 2
        for _ in range(25):
            response = requests.post(GOOGLE_SHEET_WEBHOOK_URL, json={
                'action': 'export_quotes', 'secret': GOOGLE_SHEET_SECRET, 'cursor': cursor}, timeout=(5, 10))
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or data.get('status') != 'success' or data.get('protocol') != 'tagluxe-quotes-read-v1' or not isinstance(data.get('quotes'), list):
                raise SheetsRestoreError('Bảng tính chưa hỗ trợ đọc dữ liệu hoặc khóa xác thực chưa khớp.')
            for row in data['quotes']:
                try:
                    quote = parse_sheet_quote(row)
                except (ValueError, TypeError, KeyError, OverflowError):
                    invalid += 1
                    continue
                if db.session.get(Quote, quote.id):
                    skipped += 1
                    continue
                try:
                    with db.session.begin_nested():
                        db.session.add(quote)
                        db.session.flush()
                    inserted += 1
                except IntegrityError:
                    skipped += 1
            next_cursor = data.get('next_cursor')
            if next_cursor is None:
                db.session.commit()
                return {'inserted': inserted, 'skipped': skipped, 'invalid': invalid}
            if type(next_cursor) is not int or next_cursor <= cursor:
                raise SheetsRestoreError('Bảng tính trả về phân trang không hợp lệ.')
            cursor = next_cursor
        raise SheetsRestoreError('Bảng tính quá lớn để lấy lại trong một lần. Cần chia nhỏ dữ liệu trước khi thử lại.')
    except SheetsRestoreError:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        # Network exceptions may contain the private webhook URL; never expose them.
        raise SheetsRestoreError('Chưa đọc được Google Sheets. Hãy kiểm tra kết nối và phiên bản Apps Script rồi thử lại.') from None
