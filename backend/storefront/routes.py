from xml.etree import ElementTree as ET
from urllib.parse import quote
from flask import Blueprint, render_template, Response, redirect, url_for, request, abort
from backend.services.data_service import (
    get_visible_products, get_product_by_id, get_lanyard_photos,
    get_showcase_items, product_schema, get_demo_images_config, get_accessories_catalog
)
from backend.config import site_origin

from backend.storefront.urls import product_path, SLUG_PRODUCTS

storefront_bp = Blueprint('storefront', __name__)
PAGES = {
    'products': ('/san-pham', 'Sản phẩm', 'Khám phá dây đeo thẻ, thẻ nhựa PVC và vỏ đựng thẻ in theo yêu cầu tại TAGLUXE.'),
    'calculator': ('/bao-gia', 'Báo giá in ấn', 'Chọn sản phẩm và số lượng để tính chi phí in dự kiến, sau đó gửi yêu cầu tư vấn.'),
    'process': ('/quy-trinh', 'Quy trình đặt in', 'Từ tư vấn, thiết kế và duyệt mẫu đến sản xuất, giao hàng.'),
    'faq': ('/cau-hoi-thuong-gap', 'Câu hỏi thường gặp', 'Giải đáp về số lượng đặt in, thiết kế, thời gian sản xuất và giao hàng.'),
    'contact': ('/lien-he', 'Liên hệ TAGLUXE', 'Liên hệ tư vấn qua Zalo hoặc các kênh chính thức của TAGLUXE bên dưới. Phục vụ tại TP.HCM, Hà Nội và giao hàng toàn quốc.'),
}


@storefront_bp.context_processor
def public_paths():
    return {'product_path': product_path}


@storefront_bp.before_request
def normalize_public_slash():
    if request.method in ('GET', 'HEAD') and request.path != '/' and request.path.endswith('/'):
        suffix = '?' + request.query_string.decode('ascii', errors='ignore') if request.query_string else ''
        return redirect(request.path.rstrip('/') + suffix, code=301)


@storefront_bp.route('/')
def index(page='home'):
    products = get_visible_products()
    lanyards = [p for p in products if p.get('category') == 'lanyard']
    accessories = [p for p in products if p.get('category') == 'accessory']
    pvc_product = next((p for p in accessories if 'pvc' in (p.get('name') or '').lower() or p.get('id') == 'acc-1'), None)
    holder_product = next((p for p in accessories if 'vỏ' in (p.get('name') or '').lower() or 'holder' in (p.get('name') or '').lower() or p.get('id') == 'acc-2'), None)
    lanyard_photos = get_lanyard_photos(lanyards)
    hero_images = [photo['img'] for photo in lanyard_photos[:12]]
    showcase_items = get_showcase_items(lanyards, accessories)

    demo_cfg = get_demo_images_config()
    holder_demo_cards = []
    holder_keys = [
        'holder_custom_vertical', 'holder_custom_horizontal',
        'holder_plain_vertical', 'holder_plain_horizontal',
        'holder_silicone_vertical', 'holder_silicone_horizontal'
    ]
    for k in holder_keys:
        item = demo_cfg.get(k)
        if item and item.get('image') and '/uploads/' in item.get('image'):
            holder_demo_cards.append({
                'image_url': item['image'],
                'name': item.get('pill') or item.get('title') or (holder_product.get('name') if holder_product else 'Vỏ đựng thẻ in theo yêu cầu')
            })

    path, title, description = PAGES.get(page, ('/', None, None))
    return render_template('index.html', page_section=page, page_path=path, page_title=title, page_description=description,
                           accessory_catalog=get_accessories_catalog() if page in ('home', 'calculator') else {},
                           lanyards=lanyards,
                           accessories=accessories,
                           pvc_product=pvc_product,
                           holder_product=holder_product,
                           lanyard_photos=lanyard_photos,
                           hero_images=hero_images,
                           showcase_items=showcase_items,
                           holder_demo_cards=holder_demo_cards)

for page_key, (path, _, _) in PAGES.items():
    storefront_bp.add_url_rule(path, endpoint='page_' + page_key, view_func=index,
                               defaults={'page': page_key}, strict_slashes=False)


@storefront_bp.route('/product/<id>')
def product_detail(id):
    canonical_id = 'lan-1' if id in ('lan-2', 'lan-3') else id
    if not get_product_by_id(canonical_id, visible_only=True):
        abort(404)
    suffix = '?' + request.query_string.decode('ascii', errors='ignore') if request.query_string else ''
    return redirect(product_path(canonical_id) + suffix, code=301)


@storefront_bp.route('/san-pham/<slug>', strict_slashes=False)
def product_page(slug):
    id = SLUG_PRODUCTS.get(slug, slug)
    product = get_product_by_id(id, visible_only=True)
    if not product:
        abort(404)
    if request.path != product_path(product):
        return redirect(product_path(product), code=301)
    related_products = [p for p in get_visible_products() if p.get('id') != id]
    return render_template('product.html', product=product, related_products=related_products,
        accessories=related_products, product_jsonld=product_schema(product))

@storefront_bp.route('/sitemap.xml')
def sitemap():
    products = get_visible_products()
    origin = site_origin()
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    image_ns = 'http://www.google.com/schemas/sitemap-image/1.1'
    ET.register_namespace('', ns)
    ET.register_namespace('image', image_ns)
    root = ET.Element(f'{{{ns}}}urlset')
    home = ET.SubElement(root, f'{{{ns}}}url')
    ET.SubElement(home, f'{{{ns}}}loc').text = origin + '/'
    for path, _, _ in PAGES.values():
        page_entry = ET.SubElement(root, f'{{{ns}}}url')
        ET.SubElement(page_entry, f'{{{ns}}}loc').text = origin + path
    for product in products:
        entry = ET.SubElement(root, f'{{{ns}}}url')
        ET.SubElement(entry, f'{{{ns}}}loc').text = origin + product_path(product)
        images = product.get('images') or ([product['image']] if product.get('image') else [])
        for filename in dict.fromkeys(img for img in images if img):
            image = ET.SubElement(entry, f'{{{image_ns}}}image')
            ET.SubElement(image, f'{{{image_ns}}}loc').text = origin + '/static/uploads/' + quote(filename, safe='')
    return Response(ET.tostring(root, encoding='utf-8', xml_declaration=True), mimetype='application/xml')

@storefront_bp.route('/robots.txt')
def robots():
    site_url = site_origin()
    txt = f'User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /admin/*\nSitemap: {site_url}/sitemap.xml\n'
    return Response(txt, mimetype='text/plain')

@storefront_bp.route('/ping')
def ping():
    """Health check endpoint used by keep-alive thread"""
    return 'OK', 200

@storefront_bp.route('/<filename>')
def google_verification_file(filename):
    import re
    if re.fullmatch(r'google[a-zA-Z0-9]+\.html', filename):
        return f"google-site-verification: {filename}", 200, {'Content-Type': 'text/html; charset=utf-8'}
    from flask import abort
    abort(404)

