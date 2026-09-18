from xml.etree import ElementTree as ET
from urllib.parse import quote
from flask import Blueprint, render_template, Response, redirect, url_for
from backend.services.data_service import (
    get_visible_products, get_product_by_id, get_lanyard_photos,
    get_showcase_items, product_schema
)
from backend.config import site_origin

storefront_bp = Blueprint('storefront', __name__)

@storefront_bp.route('/')
def index():
    products = get_visible_products()
    lanyards = [p for p in products if p.get('category') == 'lanyard']
    accessories = [p for p in products if p.get('category') == 'accessory']
    lanyard_photos = get_lanyard_photos(lanyards)
    showcase_items = get_showcase_items(lanyards, accessories)
    return render_template('index.html',
                           lanyards=lanyards,
                           accessories=accessories,
                           lanyard_photos=lanyard_photos,
                           showcase_items=showcase_items)

@storefront_bp.route('/product/<id>')
def product_detail(id):
    if id in ('lan-2', 'lan-3'):
        return redirect(url_for('storefront.product_detail', id='lan-1'), code=301)
    product = get_product_by_id(id, visible_only=True)
    if not product:
        return "Sản phẩm không tồn tại hoặc đã bị ẩn", 404
    all_products = get_visible_products()
    related_products = [p for p in all_products if p.get('id') != product.get('id')]
    return render_template('product.html', product=product, related_products=related_products, accessories=related_products, product_jsonld=product_schema(product))

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
    for product in products:
        entry = ET.SubElement(root, f'{{{ns}}}url')
        ET.SubElement(entry, f'{{{ns}}}loc').text = origin + '/product/' + quote(product['id'], safe='')
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
