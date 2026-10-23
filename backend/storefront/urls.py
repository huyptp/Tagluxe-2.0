"""Stable public paths, shared by templates, sitemap and product structured data."""
from urllib.parse import quote

PRODUCT_SLUGS = {'lan-1': 'day-deo-the', 'acc-1': 'the-nhua-pvc', 'acc-2': 'vo-dung-the'}
SLUG_PRODUCTS = {slug: ident for ident, slug in PRODUCT_SLUGS.items()}


def product_path(product):
    ident = str(product.get('id') if isinstance(product, dict) else product)
    if ident in ('lan-2', 'lan-3'):
        ident = 'lan-1'
    return '/san-pham/' + quote(PRODUCT_SLUGS.get(ident, ident), safe='')
