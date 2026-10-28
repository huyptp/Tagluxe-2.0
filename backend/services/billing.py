"""Local VietQR generation. No account or customer data leaves the application."""
import binascii
import hashlib
import io
import json
import re
from pathlib import Path
import qrcode
from qrcode.image.svg import SvgPathImage
from backend.services.settings_storage import read_setting


def banks():
    return json.loads(Path(__file__).with_name('payment_banks.json').read_text(encoding='utf-8'))


def tlv(tag, value):
    if len(value.encode('ascii')) > 99:
        raise ValueError('Trường QR quá dài.')
    return tag + f'{len(value):02d}' + value


def fields(payload):
    result = {}
    offset = 0
    while offset < len(payload):
        head = payload[offset:offset + 4]
        if len(head) != 4 or not head.isdigit():
            raise ValueError('Dữ liệu QR không hợp lệ.')
        tag, length = head[:2], int(head[2:])
        value = payload[offset + 4:offset + 4 + length]
        if len(value) != length or tag in result:
            raise ValueError('Dữ liệu QR không hợp lệ.')
        result[tag] = value
        offset += 4 + length
    return result


def parse_source_qr(payload):
    if len(payload) > 1000 or not payload.isascii():
        raise ValueError('QR gốc không hợp lệ.')
    parsed = fields(payload)
    if (not payload.endswith('6304' + parsed.get('63', '')) or
            len(parsed.get('63', '')) != 4 or
            f'{binascii.crc_hqx(payload[:-4].encode(), 0xffff):04X}' != parsed['63'].upper()):
        raise ValueError('Mã kiểm tra QR gốc không đúng.')
    merchant = fields(parsed.get('38', ''))
    beneficiary = fields(merchant.get('01', ''))
    if (parsed.get('00') != '01' or parsed.get('53') != '704' or parsed.get('58') != 'VN' or
            merchant.get('00') != 'A000000727' or merchant.get('02') != 'QRIBFTTA' or
            not re.fullmatch(r'\d{6}', beneficiary.get('00', '')) or
            not re.fullmatch(r'[A-Za-z0-9]{1,19}', beneficiary.get('01', ''))):
        raise ValueError('Chỉ hỗ trợ QR chuyển khoản tài khoản VietQR bằng VND.')
    return parsed, beneficiary


def validate_payment_settings(form):
    value = {key: form.get(key, '').strip() for key in
             ('bank_bin', 'account_number', 'account_name', 'source_qr')}
    value['account_number'] = re.sub(r'\s+', '', value['account_number'])
    value['account_name'] = value['account_name'].upper()
    if value['bank_bin'] not in {b['bin'] for b in banks()}:
        raise ValueError('Vui lòng chọn ngân hàng nhận tiền.')
    if not re.fullmatch(r'[A-Za-z0-9]{1,19}', value['account_number']):
        raise ValueError('Số tài khoản cần gồm 1–19 chữ hoặc số, không có ký tự đặc biệt.')
    if not 2 <= len(value['account_name']) <= 80 or any(ord(c) < 32 for c in value['account_name']):
        raise ValueError('Tên chủ tài khoản cần từ 2–80 ký tự.')
    if value['source_qr']:
        _, beneficiary = parse_source_qr(value['source_qr'])
        if beneficiary['00'] != value['bank_bin']:
            raise ValueError('Ngân hàng đã chọn không trùng với ngân hàng trong QR gốc.')
    return value


def payment_settings():
    raw = read_setting('payments')
    try:
        value = validate_payment_settings(raw)
    except ValueError:
        return None
    value['bank_name'] = next(b['shortName'] for b in banks() if b['bin'] == value['bank_bin'])
    return value


def payment_reference(quote_id):
    # VietQR purpose is capped at 25 characters; hash long IDs rather than truncate.
    clean = re.sub(r'[^A-Za-z0-9]', '', quote_id).upper()
    if not clean or len(clean) > 32:
        raise ValueError('Mã báo giá không hợp lệ để tạo nội dung chuyển khoản.')
    return 'TL' + (clean if len(clean) <= 23 else hashlib.sha256(quote_id.encode()).hexdigest()[:20].upper())


def vietqr_payload(settings, amount, reference):
    if type(amount) is not int or not 0 < amount <= 9999999999999:
        raise ValueError('Số tiền trên bill phải lớn hơn 0 và tối đa 13 chữ số.')
    if not re.fullmatch(r'[A-Z0-9]{1,25}', reference):
        raise ValueError('Nội dung chuyển khoản không hợp lệ.')
    if settings.get('source_qr'):
        source, _ = parse_source_qr(settings['source_qr'])
        # Preserve bank merchant extensions (e.g. Techcombank tags 83/84).
        source = {k:v for k,v in source.items() if k not in ('63','54','62')}
    else:
        beneficiary = tlv('00', settings['bank_bin']) + tlv('01', settings['account_number'])
        merchant = tlv('00', 'A000000727') + tlv('01', beneficiary) + tlv('02', 'QRIBFTTA')
        source = {'00':'01', '01':'12', '38':merchant, '53':'704', '58':'VN'}
    source['01'] = '12'
    source['54'] = str(amount)
    source['62'] = tlv('08', reference)
    body = ''.join(tlv(k,v) for k,v in sorted(source.items())) + '6304'
    return body + f'{binascii.crc_hqx(body.encode("ascii"), 0xffff):04X}'


def qr_svg(payload):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    output = io.BytesIO()
    qr.make_image(image_factory=SvgPathImage).save(output)
    return output.getvalue()
