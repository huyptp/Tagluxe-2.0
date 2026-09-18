import json
import os
import re
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

import app as website


class SeoTests(unittest.TestCase):
    def setUp(self):
        self.client = website.app.test_client()

    def jsonld(self, html):
        return [json.loads(s) for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]

    def test_live_catalog_pages_have_parseable_metadata_and_no_invented_ratings(self):
        paths = ['/'] + ['/product/' + p['id'] for p in website.load_data()['products'] if p.get('visible', True)]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertTrue(self.jsonld(html))
                self.assertNotIn('aggregateRating', html)
                self.assertNotIn('X-Robots-Tag', response.headers)
                self.assertIn('href="https://tagluxe.onrender.com' + path + '"', html)

    def test_product_json_escapes_quotes_and_quote_mode_has_no_offer(self):
        p = dict(website.load_data()['products'][0], name='Dây "Đỏ" & Xanh', description='Dòng 1\nDòng 2 </script>', price_type='contact', price=0)
        with patch.object(website, 'load_data', return_value={'products': [p]}):
            html = self.client.get('/product/' + p['id']).get_data(as_text=True)
        product = next(s for s in self.jsonld(html) if s.get('@type') == 'Product')
        self.assertEqual(product['name'], p['name'])
        self.assertEqual(product['description'], p['description'])
        self.assertNotIn('offers', product)
        self.assertNotIn('itemprop="offers"', html)

    def test_fixed_price_is_actual_catalog_price(self):
        p = dict(website.load_data()['products'][0], price_type='fixed', price=32100)
        self.assertEqual(website.product_schema(p)['offers']['price'], 32100)

    def test_sitemap_handles_special_filenames_and_hidden_products(self):
        p = dict(website.load_data()['products'][0], images=['a & b.jpg', '', 'a & b.jpg'])
        hidden = dict(p, id='hidden-product', visible=False)
        with patch.object(website, 'load_data', return_value={'products': [p, hidden]}):
            response = self.client.get('/sitemap.xml')
        root = ET.fromstring(response.data)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'i': 'http://www.google.com/schemas/sitemap-image/1.1'}
        self.assertEqual(len(root.findall('s:url', ns)), 2)
        self.assertEqual(len(root.findall('.//i:image', ns)), 1)
        self.assertNotIn(b'lastmod', response.data)
        self.assertIn(b'a%20%26%20b.jpg', response.data)
        self.assertNotIn(b'hidden-product', response.data)

    def test_future_domain_is_consistent(self):
        with patch.dict(os.environ, {'SITE_URL': 'https://example.com/'}):
            html = self.client.get('/').get_data(as_text=True)
            self.assertNotIn('https://tagluxe.onrender.com', html)
            self.assertIn('https://example.com/', html)
            self.assertIn(b'https://example.com/sitemap.xml', self.client.get('/robots.txt').data)
            self.assertIn(b'https://example.com/', self.client.get('/sitemap.xml').data)
            self.jsonld(html)

    def test_admin_health_and_missing_pages_are_not_indexable(self):
        for path in ['/admin', '/admin/login', '/ping', '/product/missing', '/not-a-real-page']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).headers['X-Robots-Tag'], 'noindex, nofollow')
        self.assertEqual(self.client.get('/product/missing').status_code, 404)

    def test_removed_lanyard_routes_redirect_301(self):
        for old_id in ['lan-2', 'lan-3']:
            with self.subTest(old_id=old_id):
                res = self.client.get(f'/product/{old_id}')
                self.assertEqual(res.status_code, 301)
                self.assertTrue(res.headers['Location'].endswith('/product/lan-1'))


    def test_google_tag_manager_rendered(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('https://www.googletagmanager.com/gtm.js?id=', html)
        self.assertIn('https://www.googletagmanager.com/ns.html?id=', html)
        self.assertIn('GTM-T22MFFG9', html)

    def test_google_analytics_rendered(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('https://www.googletagmanager.com/gtag/js?id=G-KY6VE15P5L', html)
        self.assertIn("gtag('config', 'G-KY6VE15P5L')", html)



if __name__ == '__main__':
    unittest.main()
