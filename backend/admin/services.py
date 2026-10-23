"""
Admin domain services:
Handles administrative operations, reporting, analytics, and synchronization.
"""
import io
import csv
from datetime import datetime, timedelta
from backend.services.data_service import (
    get_all_products, get_product_by_id, add_product, update_product, delete_product,
    get_demo_requests, update_demo_request_status, delete_demo_request,
    get_quotes, update_quote_status, delete_quote,
    get_all_accessories
)


def _parse_quote_datetime(q_dict, raw_dt=None):
    """Safely extracts a datetime object from a Quote model or dict."""
    if isinstance(raw_dt, datetime):
        return raw_dt
    created_str = (q_dict.get('created_at') or '').strip()
    if created_str:
        for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(created_str, fmt)
            except ValueError:
                continue
    return None


def _classify_category_group(category_str):
    """Maps a quote category string to one of the main product lines."""
    c = (category_str or '').lower()
    if 'pvc' in c or 'thẻ nhựa' in c or 'the nhua' in c:
        return 'Thẻ nhựa PVC'
    if 'vỏ' in c or 'vo ' in c or 'holder' in c or 'bao thẻ' in c:
        return 'Vỏ đựng thẻ'
    if 'combo' in c:
        return 'Combo trọn bộ'
    return 'Dây đeo thẻ'


def get_quotes_summary_stats(quotes_list):
    """Computes quick summary metrics for a list of quote dicts (used on /admin/quotes)."""
    items = quotes_list or []
    total_count = len(items)
    new_or_consulting = 0
    closed_or_done = 0
    cancelled_count = 0
    total_value = 0
    closed_value = 0
    failed_sync = 0

    for q in items:
        st = (q.get('status') or 'Mới').strip()
        price = int(q.get('total_price') or 0)
        sync_st = (q.get('sync_status') or 'pending').strip()

        if st in ('Mới', 'Đang tư vấn', 'Đã tư vấn', 'pending', 'chờ xử lý', 'chưa liên hệ'):
            new_or_consulting += 1
        if st in ('Đã chốt', 'Đã xong'):
            closed_or_done += 1
            closed_value += price
        if st == 'Đã hủy':
            cancelled_count += 1
        else:
            total_value += price

        if sync_st == 'failed':
            failed_sync += 1

    return {
        'total_count': total_count,
        'new_or_consulting': new_or_consulting,
        'closed_or_done': closed_or_done,
        'cancelled_count': cancelled_count,
        'total_value': total_value,
        'closed_value': closed_value,
        'failed_sync': failed_sync
    }


def get_admin_dashboard_stats():
    """
    Aggregates comprehensive administrative metrics, time-series chart data
    (7d, 30d, 12m), status/category distributions, and recent AuditLog entries.
    """
    from backend.models import Quote, PriceTier, AuditLog

    quotes_models = Quote.query.order_by(Quote.created_at.desc(), Quote.id.desc()).all()
    quotes = [q.to_dict() for q in quotes_models]
    quote_dt_pairs = [(q.to_dict(), q.created_at) for q in quotes_models]

    products = get_all_products()
    accessories = get_all_accessories()

    try:
        total_price_tiers = PriceTier.query.count()
    except Exception:
        total_price_tiers = 0

    try:
        total_audit_logs = AuditLog.query.count()
        recent_logs_models = AuditLog.query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(10).all()
        recent_audit_logs = [log.to_dict() for log in recent_logs_models]
    except Exception:
        total_audit_logs = 0
        recent_audit_logs = []

    total_quotes = len(quotes)
    pending_quotes = len([
        q for q in quotes
        if q.get('status') in ['Mới', 'Đang tư vấn', 'pending', 'chờ xử lý', 'chưa liên hệ']
    ])

    status_keys = ['Mới', 'Đang tư vấn', 'Đã tư vấn', 'Đang chốt', 'Đã chốt', 'Đã xong', 'Đã hủy']
    status_counts = {k: 0 for k in status_keys}

    category_map = {
        'Dây đeo thẻ': {'count': 0, 'revenue': 0, 'quantity': 0},
        'Thẻ nhựa PVC': {'count': 0, 'revenue': 0, 'quantity': 0},
        'Vỏ đựng thẻ': {'count': 0, 'revenue': 0, 'quantity': 0},
        'Combo trọn bộ': {'count': 0, 'revenue': 0, 'quantity': 0}
    }

    sync_summary = {'synced': 0, 'pending': 0, 'failed': 0}

    total_revenue = 0
    closed_revenue = 0
    new_quotes_count = 0
    in_progress_quotes_count = 0
    completed_quotes_count = 0
    cancelled_quotes_count = 0

    for q in quotes:
        st = (q.get('status') or 'Mới').strip()
        price = int(q.get('total_price') or 0)
        qty = int(q.get('quantity') or 0)
        sync_st = (q.get('sync_status') or 'pending').strip()

        if st in status_counts:
            status_counts[st] += 1
        else:
            status_counts[st] = status_counts.get(st, 0) + 1

        if st == 'Mới':
            new_quotes_count += 1
        elif st in ('Đang tư vấn', 'Đã tư vấn', 'Đang chốt'):
            in_progress_quotes_count += 1
        elif st in ('Đã chốt', 'Đã xong'):
            completed_quotes_count += 1
            closed_revenue += price
        elif st == 'Đã hủy':
            cancelled_quotes_count += 1

        if st != 'Đã hủy':
            total_revenue += price

        cat_group = _classify_category_group(q.get('category'))
        if cat_group not in category_map:
            category_map[cat_group] = {'count': 0, 'revenue': 0, 'quantity': 0}
        category_map[cat_group]['count'] += 1
        if st != 'Đã hủy':
            category_map[cat_group]['revenue'] += price
            category_map[cat_group]['quantity'] += qty

        if sync_st in sync_summary:
            sync_summary[sync_st] += 1
        else:
            sync_summary['pending'] += 1

    conversion_rate = round((completed_quotes_count / total_quotes) * 100, 1) if total_quotes > 0 else 0.0

    # Time-series chart construction (7 days, 30 days, 12 months)
    now = datetime.now()
    today_date = now.date()

    # 1. 7 days series (daily)
    series_7d = []
    map_7d = {}
    for i in range(6, -1, -1):
        d = today_date - timedelta(days=i)
        key = d.strftime('%Y-%m-%d')
        bucket = {'key': key, 'label': d.strftime('%d/%m'), 'count': 0, 'revenue': 0}
        series_7d.append(bucket)
        map_7d[key] = bucket

    # 2. 30 days series (10 buckets of 3 days for clean table/bar layout, plus daily accuracy)
    series_30d = []
    for b_idx in range(9, -1, -1):
        end_d = today_date - timedelta(days=b_idx * 3)
        start_d = end_d - timedelta(days=2)
        label = f"{start_d.strftime('%d/%m')}-{end_d.strftime('%d/%m')}"
        series_30d.append({
            'start_date': start_d,
            'end_date': end_d,
            'label': label,
            'count': 0,
            'revenue': 0
        })

    # 3. Full rolling 12 months.
    series_12m = []
    map_12m = {}
    curr_year = today_date.year
    curr_month = today_date.month
    for m_offset in range(11, -1, -1):
        m = curr_month - m_offset
        y = curr_year
        while m <= 0:
            m += 12
            y -= 1
        m_key = f"{y:04d}-{m:02d}"
        m_bucket = {'key': m_key, 'label': f"T{m}/{str(y)[2:]}", 'count': 0, 'revenue': 0}
        series_12m.append(m_bucket)
        map_12m[m_key] = m_bucket

    for q_dict, raw_dt in quote_dt_pairs:
        dt = _parse_quote_datetime(q_dict, raw_dt)
        if not dt:
            continue
        q_date = dt.date()
        st = (q_dict.get('status') or 'Mới').strip()
        price = int(q_dict.get('total_price') or 0) if st != 'Đã hủy' else 0

        d_key = q_date.strftime('%Y-%m-%d')
        if d_key in map_7d:
            map_7d[d_key]['count'] += 1
            map_7d[d_key]['revenue'] += price

        for b in series_30d:
            if b['start_date'] <= q_date <= b['end_date']:
                b['count'] += 1
                b['revenue'] += price
                break

        m_key = q_date.strftime('%Y-%m')
        if m_key in map_12m:
            map_12m[m_key]['count'] += 1
            map_12m[m_key]['revenue'] += price

    from backend.admin.workspace_services import filtered_quotes, quote_filters
    due_count = filtered_quotes(quote_filters({'follow_up': 'due'})).count()

    # Clean non-JSON-serializable date objects from series_30d
    clean_30d = [
        {'label': b['label'], 'count': b['count'], 'revenue': b['revenue']}
        for b in series_30d
    ]

    return {
        'total_quotes': total_quotes,
        'pending_quotes': pending_quotes,
        'follow_up_due': due_count,
        'sync_failures': sync_summary['failed'],
        'total_products': len(products),
        'total_accessories': len(accessories),
        'total_price_tiers': total_price_tiers,
        'total_audit_logs': total_audit_logs,
        'total_revenue': total_revenue,
        'closed_revenue': closed_revenue,
        'new_quotes_count': new_quotes_count,
        'in_progress_quotes_count': in_progress_quotes_count,
        'completed_quotes_count': completed_quotes_count,
        'cancelled_quotes_count': cancelled_quotes_count,
        'conversion_rate': conversion_rate,
        'status_counts': status_counts,
        'category_breakdown': category_map,
        'sync_summary': sync_summary,
        'chart_series': {
            '7d': series_7d,
            '30d': clean_30d,
            '12m': series_12m
        },
        'recent_quotes': quotes[:5],
        'recent_audit_logs': recent_audit_logs
    }


def generate_quotes_csv_bytes(status=None, search=None, items=None):
    """
    Generates UTF-8 with BOM CSV bytes of quotes matching status & search filters
    so Microsoft Excel opens Vietnamese characters cleanly without garbling.
    """
    quotes = items if items is not None else get_quotes(status=status, search=search)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Mã Báo Giá',
        'Thời Gian Tạo',
        'Tên Khách Hàng',
        'Số Điện Thoại',
        'Dòng Sản Phẩm',
        'Quy Cách / Kích Thước',
        'Đục Lỗ',
        'Phụ Kiện Kèm Theo',
        'Số Lượng',
        'Đơn Giá (VNĐ)',
        'VAT 8%',
        'Tiền VAT (VNĐ)',
        'Tổng Thành Tiền (VNĐ)',
        'Trạng Thái Xử Lý',
        'Đồng Bộ Google Sheets',
        'Ghi Chú'
    ])

    for q in quotes:
        accs = q.get('accessories') or []
        if isinstance(accs, list):
            accs_str = ', '.join(str(a) for a in accs)
        else:
            accs_str = str(accs)

        hole = q.get('punched_hole') or 'none'
        if hole == 'round':
            hole_str = 'Lỗ tròn'
        elif hole == 'capsule':
            hole_str = 'Lỗ con nhộng'
        else:
            hole_str = 'Không'

        writer.writerow([safe_csv_cell(value) for value in [
            q.get('id', ''),
            q.get('created_at', ''),
            q.get('customer_name', ''),
            f"'{q.get('phone', '')}" if q.get('phone') else '',
            q.get('category', ''),
            q.get('specs') or q.get('width') or '',
            hole_str,
            accs_str,
            q.get('quantity', 0),
            q.get('unit_price', 0),
            'Có (8%)' if q.get('include_vat') else 'Không',
            q.get('vat_amount', 0),
            q.get('total_price', 0),
            q.get('status', ''),
            q.get('sync_status', ''),
            q.get('notes', '')
        ]])

    csv_text = output.getvalue()
    return b'\xef\xbb\xbf' + csv_text.encode('utf-8')


def safe_csv_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
        return "'" + value
    return value
