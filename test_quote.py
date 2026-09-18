import os
import json
import unittest
from unittest.mock import patch, MagicMock
import app as website
from backend.services.data_service import calculate_lanyard_price, add_quote, get_quotes

class QuoteCalculatorTests(unittest.TestCase):
    def setUp(self):
        self.client = website.app.test_client()
        from backend.security import limiter, idempotency
        from backend.database import db
        limiter._records.clear()
        idempotency._cache.clear()
        with website.app.app_context():
            from backend.models import IdempotencyRecord
            IdempotencyRecord.query.delete()
            db.session.commit()

    def test_pricing_math_tiers_and_addons(self):
        # 1. Base 20 qty (tier 10-21: 28k)
        p20 = calculate_lanyard_price(20, '2.0', [])
        self.assertEqual(p20['unit_price'], 28000)
        self.assertEqual(p20['total_price'], 560000)

        # 2. Base 50 qty (tier 46-70: 20k)
        p50 = calculate_lanyard_price(50, '2.0', [])
        self.assertEqual(p50['unit_price'], 20000)
        self.assertEqual(p50['total_price'], 1000000)

        # 3. 100 qty (tier 71-120: 19k), 1.5cm (-1k), breakaway (+2.5k)
        p100 = calculate_lanyard_price(100, '1.5', ['breakaway'])
        # base: 19000 - 1000 + 2500 = 20500
        self.assertEqual(p100['unit_price'], 20500)
        self.assertEqual(p100['total_price'], 2050000)

        # 4. 500 qty (tier 421-530: 16k), 2.5cm (+2.5k), quick_release (+2.5k), black_hook (+2.5k)
        p500 = calculate_lanyard_price(500, '2.5', ['quick_release', 'black_hook'])
        # base: 16000 + 2500 + 2500 + 2500 = 23500
        self.assertEqual(p500['unit_price'], 23500)
        self.assertEqual(p500['total_price'], 11750000)

    def test_pvc_holder_combo_calculations(self):
        from backend.services.data_service import calculate_pvc_price, calculate_holder_price, calculate_combo_price
        # PVC Chuẩn thẻ ngân hàng (5.4x8.6cm): 50 cái thuộc bậc 21-50 (15k), đồng giá cho cả Mờ, Nhám, Bóng
        pvc_matte = calculate_pvc_price(50, finish='matte')
        self.assertEqual(pvc_matte['unit_price'], 15000)
        self.assertEqual(pvc_matte['total_price'], 750000)
        self.assertEqual(pvc_matte['finish_label'], 'Cán màng mờ')

        pvc_textured = calculate_pvc_price(50, finish='textured')
        self.assertEqual(pvc_textured['unit_price'], 15000)
        self.assertEqual(pvc_textured['finish_label'], 'Cán màng nhám')

        pvc_glossy = calculate_pvc_price(50, finish='glossy')
        self.assertEqual(pvc_glossy['unit_price'], 15000)
        self.assertEqual(pvc_glossy['finish_label'], 'Cán màng bóng')

        # PVC Chuẩn thẻ ngân hàng: 100 cái thuộc bậc 51-100 (12k) = 12.000đ
        pvc_100 = calculate_pvc_price(100, finish='matte')
        self.assertEqual(pvc_100['unit_price'], 12000)

        # PVC 7x11cm: 50 cái thuộc bậc 21-50 (18k)
        pvc_7x11 = calculate_pvc_price(50, size='7x11cm')
        self.assertEqual(pvc_7x11['unit_price'], 18000)

        # PVC 9x12cm: 50 cái thuộc bậc 21-50 (22k)
        pvc_9x12 = calculate_pvc_price(50, size='9x12cm')
        self.assertEqual(pvc_9x12['unit_price'], 22000)

        # PVC Ngoại size: Liên hệ Zalo (0đ)
        pvc_custom = calculate_pvc_price(50, size='custom')
        self.assertEqual(pvc_custom['unit_price'], 0)
        self.assertTrue(pvc_custom['is_custom_size'])

        # PVC Đục lỗ con nhộng (Lỗ dẹt oval - Miễn phí 0đ)
        pvc_capsule = calculate_pvc_price(50, finish='matte', size='5.4x8.6', punched_hole='capsule')
        self.assertEqual(pvc_capsule['unit_price'], 15000) # Vẫn 15.000đ, không phụ phí
        self.assertEqual(pvc_capsule['total_price'], 750000)
        self.assertTrue(pvc_capsule['punched_hole'])
        self.assertEqual(pvc_capsule['hole_type'], 'capsule')
        self.assertIn('Lỗ con nhộng', pvc_capsule['specs'])

        # PVC Đục lỗ tròn (Miễn phí 0đ)
        pvc_round = calculate_pvc_price(50, finish='matte', size='5.4x8.6', punched_hole='round')
        self.assertEqual(pvc_round['unit_price'], 15000) # Vẫn 15.000đ, không phụ phí
        self.assertEqual(pvc_round['total_price'], 750000)
        self.assertTrue(pvc_round['punched_hole'])
        self.assertEqual(pvc_round['hole_type'], 'round')
        self.assertIn('Lỗ tròn', pvc_round['specs'])

        # Holder 100 qty (tier 51-100: 30k), đã gồm in ấn theo thiết kế
        holder = calculate_holder_price(100, 'vertical', True)
        self.assertEqual(holder['unit_price'], 30000)
        self.assertEqual(holder['total_price'], 3000000)

        # Combo 50 qty
        combo = calculate_combo_price(50, '2.0', [])
        self.assertEqual(combo['unit_price'], 33000)
        self.assertEqual(combo['total_price'], 1650000)

    def test_submit_quote_validation_errors(self):
        # Missing name
        res = self.client.post('/api/submit-quote', json={
            'customer_name': '',
            'phone': '0912345678',
            'quantity': 50
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()['success'])

        # Invalid phone
        res = self.client.post('/api/submit-quote', json={
            'customer_name': 'Nguyễn Văn A',
            'phone': '01234',
            'quantity': 50
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()['success'])

        # Quantity < 10
        res = self.client.post('/api/submit-quote', json={
            'customer_name': 'Nguyễn Văn A',
            'phone': '0912345678',
            'quantity': 5
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()['success'])

    def test_submit_quote_success_and_phone_normalization(self):
        from backend.models import Quote
        res = self.client.post('/api/submit-quote', json={
            'customer_name': 'Trần Thị Thu',
            'phone': '+84 987 654 321',
            'quantity': 30,
            'width': '2.0',
            'accessories': ['breakaway'],
            'notes': 'Cần gấp cho sự kiện khai trương'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('quote', data)
        quote = data['quote']
        self.assertEqual(quote['customer_name'], 'Trần Thị Thu')
        self.assertEqual(quote['phone'], '0987654321')
        self.assertEqual(quote['quantity'], 30)

        # Verify in Database
        with website.app.app_context():
            saved = Quote.query.filter_by(id=quote['id']).first()
            self.assertIsNotNone(saved)
            self.assertEqual(saved.phone, '0987654321')
            self.assertEqual(saved.customer_name, 'Trần Thị Thu')

    def test_vat_8_percent_calculation_and_submission(self):
        from backend.services.data_service import calculate_product_price
        # 1. Test calculation with VAT 8%
        # 50 lanyards, base 20.000đ -> subtotal = 1.000.000đ, VAT 8% = 80.000đ, total = 1.080.000đ
        res_vat = calculate_product_price('lanyard', 50, width='2.0', include_vat=True)
        self.assertTrue(res_vat['include_vat'])
        self.assertEqual(res_vat['vat_rate'], 8)
        self.assertEqual(res_vat['subtotal'], 1000000)
        self.assertEqual(res_vat['vat_amount'], 80000)
        self.assertEqual(res_vat['total_price'], 1080000)

        # 2. Test API calculate-price with VAT
        api_res = self.client.post('/api/calculate-price', json={
            'category': 'lanyard',
            'quantity': 50,
            'width': '2.0',
            'include_vat': True
        })
        self.assertEqual(api_res.status_code, 200)
        api_data = api_res.get_json()['data']
        self.assertTrue(api_data['include_vat'])
        self.assertEqual(api_data['total_price'], 1080000)

        # 3. Test API submit-quote with VAT
        sub_res = self.client.post('/api/submit-quote', json={
            'customer_name': 'Công ty ABC',
            'phone': '0901234567',
            'quantity': 50,
            'width': '2.0',
            'include_vat': True,
            'notes': 'Cần xuất hóa đơn VAT'
        })
        self.assertEqual(sub_res.status_code, 200)
        quote = sub_res.get_json()['quote']
        self.assertTrue(quote['include_vat'])
        self.assertEqual(quote['vat_amount'], 80000)
        self.assertEqual(quote['total_price'], 1080000)
        self.assertIn('VAT 8%', quote['notes'])

    def test_homepage_contains_calculator_section(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('id="calculator"', html)
        self.assertIn('Dự Toán Chi Phí', html)
        self.assertIn('/api/submit-quote', html)
        self.assertIn('href="/#calculator"', html)

    def test_quote_status_and_delete_operations(self):
        from backend.services.data_service import update_quote_status, delete_quote
        from backend.models import Quote
        from backend.database import db

        temp_id = 'QTMP-TEST999'
        with website.app.app_context():
            q = Quote(
                id=temp_id,
                customer_name='Tester',
                phone='0999999999',
                category='Dây đeo thẻ',
                quantity=10,
                unit_price=28000,
                total_price=280000,
                status='Mới'
            )
            db.session.add(q)
            db.session.commit()

            # Kiểm thử đổi trạng thái
            update_quote_status(temp_id, 'Đã chốt cọc')
            updated_q = Quote.query.filter_by(id=temp_id).first()
            self.assertIsNotNone(updated_q)
            self.assertEqual(updated_q.status, 'Đã chốt cọc')

            # Kiểm thử xóa sạch
            delete_quote(temp_id)
            deleted_q = Quote.query.filter_by(id=temp_id).first()
            self.assertIsNone(deleted_q)

    def test_holder_min_quantity_validation(self):
        # Holder with qty < 20 should fail
        res = self.client.post('/api/submit-quote', json={
            'customer_name': 'Khách Vỏ Thẻ',
            'phone': '0912345678',
            'category': 'holder',
            'quantity': 15
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()['success'])
        self.assertIn('20', res.get_json()['message'])

        # Holder with qty >= 20 calculation
        from backend.services.data_service import calculate_holder_price
        p20_print = calculate_holder_price(20, 'vertical', True)
        self.assertEqual(p20_print['quantity'], 20)
        self.assertEqual(p20_print['unit_price'], 35000)
        self.assertEqual(p20_print['total_price'], 700000)

        p20_plain = calculate_holder_price(20, 'vertical', False)
        self.assertEqual(p20_plain['quantity'], 20)
        self.assertEqual(p20_plain['unit_price'], 7000)
        self.assertEqual(p20_plain['total_price'], 140000)

    def test_holder_pricing_all_tiers_and_api(self):
        from backend.services.data_service import calculate_holder_price, get_holder_pricing_matrix
        # 1. Kiểm tra 7 bậc giá Vỏ đựng thẻ in theo thiết kế
        tiers_expected = [
            (20, 35000),    # Bậc 20 - 50: 35k
            (50, 35000),
            (51, 30000),    # Bậc 51 - 100: 30k
            (100, 30000),
            (150, 28000),   # Bậc 101 - 200: 28k
            (200, 28000),
            (300, 26000),   # Bậc 201 - 400: 26k
            (400, 26000),
            (450, 25000),   # Bậc 401 - 500: 25k
            (500, 25000),
            (600, 23000),   # Bậc 501 - 1000: 23k
            (1000, 23000),
            (1500, 20000),  # Bậc 1001 - 3000: 20k
            (3000, 20000),
            (5000, 20000),  # > 3000: 20k
        ]
        for qty, expected_price in tiers_expected:
            res = calculate_holder_price(qty, orientation='vertical', printed_logo=True)
            self.assertEqual(res['unit_price'], expected_price, f"Qty {qty} should be {expected_price}, got {res['unit_price']}")
            self.assertEqual(res['total_price'], qty * expected_price)

        # 2. Vỏ đứng và vỏ ngang đồng giá cho in ấn theo thiết kế
        v_res = calculate_holder_price(100, orientation='vertical', printed_logo=True)
        h_res = calculate_holder_price(100, orientation='horizontal', printed_logo=True)
        self.assertEqual(v_res['unit_price'], h_res['unit_price'])

        # 3. Vỏ màu trơn không in: đồng giá 7.000 đ/cái cho mọi số lượng và kiểu dáng
        plain_v = calculate_holder_price(100, orientation='vertical', printed_logo=False)
        plain_h = calculate_holder_price(100, orientation='horizontal', printed_logo=False)
        self.assertEqual(plain_v['unit_price'], 7000)
        self.assertEqual(plain_h['unit_price'], 7000)
        self.assertEqual(plain_v['total_price'], 700000)

        # 4. Vỏ silicon dẻo trong suốt: đồng giá 3.000 đ/cái cho mọi số lượng và kiểu dáng
        sili_20 = calculate_holder_price(20, orientation='vertical', holder_type='silicone')
        self.assertEqual(sili_20['unit_price'], 3000)
        self.assertEqual(sili_20['total_price'], 60000)
        self.assertIn('Vỏ silicon dẻo trong suốt', sili_20['specs'])

        sili_100 = calculate_holder_price(100, orientation='horizontal', holder_type='silicone')
        self.assertEqual(sili_100['unit_price'], 3000)
        self.assertEqual(sili_100['total_price'], 300000)
        self.assertEqual(sili_100['orientation'], 'Vỏ nằm ngang')

        # 5. Test API endpoint /api/pricing/holder
        resp = self.client.get('/api/pricing/holder')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['prices'], [35000, 30000, 28000, 26000, 25000, 23000, 20000])
        self.assertEqual(data['data']['plain_price'], 7000)
        self.assertEqual(data['data']['silicone_price'], 3000)

        # 6. Test API calculate-price với holder_type = silicone
        api_calc = self.client.post('/api/calculate-price', json={
            'category': 'holder',
            'quantity': 50,
            'orientation': 'vertical',
            'holder_type': 'silicone'
        })
        self.assertEqual(api_calc.status_code, 200)
        calc_data = api_calc.get_json()
        self.assertTrue(calc_data['success'])
        self.assertEqual(calc_data['data']['unit_price'], 3000)
        self.assertEqual(calc_data['data']['total_price'], 150000)

    def test_punched_hole_three_cases_end_to_end(self):
        """Verify punched_hole three cases (none, round, capsule) throughout API and Database"""
        from backend.models import Quote
        from backend.database import db

        cases = [
            ('none', 'none', False),
            ('round', 'round', True),
            ('capsule', 'capsule', True)
        ]

        for input_val, expected_code, expected_has_hole in cases:
            res = self.client.post('/api/calculate-price', json={
                'category': 'pvc',
                'quantity': 50,
                'punched_hole': input_val
            })
            self.assertEqual(res.status_code, 200)
            cdata = res.get_json()['data']
            self.assertEqual(cdata['punched_hole'], expected_code)
            self.assertEqual(cdata['has_hole'], expected_has_hole)

            sub_res = self.client.post('/api/submit-quote', json={
                'customer_name': f'Tester {expected_code}',
                'phone': f'0912345{len(expected_code)}00',
                'category': 'pvc',
                'quantity': 50,
                'punched_hole': input_val
            })
            self.assertEqual(sub_res.status_code, 200)
            quote_data = sub_res.get_json()['quote']
            self.assertEqual(quote_data['punched_hole'], expected_code)

            # Verify in Database
            with website.app.app_context():
                saved_quote = Quote.query.filter_by(id=quote_data['id']).first()
                self.assertIsNotNone(saved_quote)
                self.assertEqual(saved_quote.punched_hole, expected_code)
                db.session.delete(saved_quote)
                db.session.commit()

    def test_migrations_runner_idempotent(self):
        """Verify versioned migrations runner executes safely and idempotently"""
        from backend.migrations import run_migrations
        from backend.models import SchemaMigration
        from backend.database import db

        with website.app.app_context():
            success = run_migrations(website.app, db)
            self.assertTrue(success)

            # Check schema_migrations table exists and has entries
            records = SchemaMigration.query.all()
            self.assertGreaterEqual(len(records), 1)

    def test_hidden_and_deleted_product_returns_404_no_json_fallback(self):
        """Group A: Hidden and deleted products return 404 and are excluded from visible catalog"""
        from backend.models import Product
        from backend.database import db
        from backend.services.data_service import get_visible_products, get_product_by_id

        test_prod_id = "test-prod-hidden-404"
        with website.app.app_context():
            # Clean up if existed
            Product.query.filter_by(id=test_prod_id).delete()
            db.session.commit()

            # 1. Create a visible product
            p = Product(
                id=test_prod_id,
                name="Sản phẩm Test Ẩn",
                category="lanyard",
                description="Mô tả sản phẩm test ẩn",
                price=20000,
                visible=True
            )
            db.session.add(p)
            db.session.commit()

            # Verify visible
            vis = get_visible_products()
            self.assertTrue(any(item['id'] == test_prod_id for item in vis))
            prod = get_product_by_id(test_prod_id, visible_only=True)
            self.assertIsNotNone(prod)

            res = self.client.get(f"/product/{test_prod_id}")
            self.assertEqual(res.status_code, 200)

            # 2. Hide the product
            p.visible = False
            db.session.commit()

            # Verify hidden: not in get_visible_products, get_product_by_id returns None, route returns 404
            vis_after = get_visible_products()
            self.assertFalse(any(item['id'] == test_prod_id for item in vis_after))
            prod_hidden = get_product_by_id(test_prod_id, visible_only=True)
            self.assertIsNone(prod_hidden)

            res_hidden = self.client.get(f"/product/{test_prod_id}")
            self.assertEqual(res_hidden.status_code, 404)

            # 3. Delete the product
            db.session.delete(p)
            db.session.commit()

            # Verify deleted returns 404
            res_deleted = self.client.get(f"/product/{test_prod_id}")
            self.assertEqual(res_deleted.status_code, 404)
            self.assertIsNone(get_product_by_id(test_prod_id))

    def test_seed_guard_prevents_reseeding_deleted_catalog(self):
        """Group A: Empty products DB does NOT re-seed when seed_initial_data_v1 migration is present"""
        from backend.models import Product, SchemaMigration
        from backend.database import db, seed_initial_data

        with website.app.app_context():
            # Check migration flag exists
            has_flag = SchemaMigration.query.filter_by(version='seed_initial_data_v1').first()
            self.assertIsNotNone(has_flag)

            # Intentionally delete all products
            all_prods = Product.query.all()
            backup_dicts = [p.to_dict() for p in all_prods]
            try:
                Product.query.delete()
                db.session.commit()
                self.assertEqual(Product.query.count(), 0)

                # Re-run seed_initial_data
                seed_initial_data()

                # Verify products table is STILL EMPTY (seed guard protected it)
                self.assertEqual(Product.query.count(), 0)
            finally:
                # Restore products
                for bd in backup_dicts:
                    bp = Product(
                        id=bd['id'],
                        name=bd['name'],
                        category=bd['category'],
                        description=bd.get('description', ''),
                        images_json=json.dumps(bd.get('images', []), ensure_ascii=False),
                        width=bd.get('width', ''),
                        material=bd.get('material', ''),
                        min_order=bd.get('min_order', 10),
                        price_type=bd.get('price_type', 'contact'),
                        price=bd.get('price', 0),
                        featured=bd.get('featured', True),
                        visible=bd.get('visible', True)
                    )
                    db.session.add(bp)
                db.session.commit()

    def test_database_level_pagination(self):
        """Group D: Verify get_quotes_paginated and get_demo_requests_paginated with LIMIT/OFFSET"""
        from backend.models import Quote, DemoRequest
        from backend.database import db
        from backend.services.data_service import get_quotes_paginated, get_demo_requests_paginated
        from datetime import datetime, timedelta

        with website.app.app_context():
            # Clean up existing test pagination items
            Quote.query.filter(Quote.id.like("Q-PAGE%")).delete()
            DemoRequest.query.filter(DemoRequest.id.like("DM-PAGE%")).delete()
            db.session.commit()

            base_time = datetime(2026, 9, 18, 12, 0, 0)
            # Create 25 test quotes
            for i in range(25):
                t_str = (base_time + timedelta(minutes=i)).strftime('%d/%m/%Y %H:%M:%S')
                q = Quote(
                    id=f"Q-PAGE-{i:02d}",
                    customer_name=f"Khách Page {i}",
                    phone=f"09110000{i:02d}",
                    category="Dây đeo thẻ",
                    quantity=50,
                    unit_price=20000,
                    total_price=1000000,
                    status="Mới",
                    created_at=base_time + timedelta(minutes=i)
                )
                db.session.add(q)

                d = DemoRequest(
                    id=f"DM-PAGE-{i:02d}",
                    customer_name=f"Khách Demo {i}",
                    phone=f"09220000{i:02d}",
                    created_at=t_str,
                    created_at_dt=base_time + timedelta(minutes=i)
                )
                db.session.add(d)
            db.session.commit()

            try:
                # Test quotes pagination: per_page=10
                p1 = get_quotes_paginated(search="Khách Page", page=1, per_page=10)
                self.assertEqual(p1['total_items'], 25)
                self.assertEqual(p1['total_pages'], 3)
                self.assertEqual(len(p1['items']), 10)
                self.assertTrue(p1['has_next'])
                self.assertFalse(p1['has_prev'])
                # Stable sort created_at desc: first item should be Q-PAGE-24
                self.assertEqual(p1['items'][0]['id'], "Q-PAGE-24")

                p2 = get_quotes_paginated(search="Khách Page", page=2, per_page=10)
                self.assertEqual(len(p2['items']), 10)
                self.assertTrue(p2['has_prev'])
                self.assertTrue(p2['has_next'])
                self.assertEqual(p2['items'][0]['id'], "Q-PAGE-14")

                p3 = get_quotes_paginated(search="Khách Page", page=3, per_page=10)
                self.assertEqual(len(p3['items']), 5)
                self.assertTrue(p3['has_prev'])
                self.assertFalse(p3['has_next'])
                self.assertEqual(p3['items'][-1]['id'], "Q-PAGE-00")

                # Test demo requests pagination
                dp1 = get_demo_requests_paginated(search="Khách Demo", page=1, per_page=10)
                self.assertEqual(dp1['total_items'], 25)
                self.assertEqual(dp1['total_pages'], 3)
                self.assertEqual(len(dp1['items']), 10)

                dp3 = get_demo_requests_paginated(search="Khách Demo", page=3, per_page=10)
                self.assertEqual(len(dp3['items']), 5)
            finally:
                Quote.query.filter(Quote.id.like("Q-PAGE%")).delete()
                DemoRequest.query.filter(DemoRequest.id.like("DM-PAGE%")).delete()
                db.session.commit()

if __name__ == '__main__':
    unittest.main()
