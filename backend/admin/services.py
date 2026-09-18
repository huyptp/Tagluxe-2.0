"""
Admin domain services:
Handles administrative operations, reporting, and synchronization.
"""
from backend.services.data_service import (
    get_all_products, get_product_by_id, add_product, update_product, delete_product,
    get_demo_requests, update_demo_request_status, delete_demo_request,
    get_quotes, update_quote_status, delete_quote
)

def get_admin_dashboard_stats():
    quotes = get_quotes()
    requests = get_demo_requests()
    products = get_all_products()
    return {
        'total_quotes': len(quotes),
        'pending_quotes': len([q for q in quotes if q.get('status') in ['pending', 'chờ xử lý', 'chưa liên hệ']]),
        'total_requests': len(requests),
        'total_products': len(products)
    }
