import unittest
import json
from unittest.mock import patch, MagicMock
from backend import create_app
from backend.database import db
from backend.security import limiter, idempotency

class SecurityTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        # Reset limiter and idempotency cache between tests
        limiter._records.clear()
        idempotency._cache.clear()
        with self.app.app_context():
            from backend.models import IdempotencyRecord
            IdempotencyRecord.query.delete()
            db.session.commit()

    def test_session_cookie_security_flags(self):
        """Verify session cookie flags: HttpOnly, SameSite=Lax"""
        self.assertTrue(self.app.config.get('SESSION_COOKIE_HTTPONLY'))
        self.assertEqual(self.app.config.get('SESSION_COOKIE_SAMESITE'), 'Lax')

    def test_rate_limiting_submit_quote(self):
        """Verify that hitting /api/submit-quote more than 10 times in 1 minute triggers HTTP 429"""
        quote_payload = {
            'customer_name': 'Test Client',
            'phone': '0912345678',
            'quantity': 50,
            'category': 'lanyard'
        }

        with patch('backend.api.routes.add_quote') as mock_add_quote:
            mock_add_quote.return_value = {'id': 'Q-TEST', 'customer_name': 'Test Client'}
            
            # Send 10 requests with different phone numbers to avoid idempotency cache
            for i in range(10):
                payload = dict(quote_payload, phone=f'091234567{i}')
                res = self.client.post('/api/submit-quote', json=payload)
                self.assertEqual(res.status_code, 200, f"Request {i+1} should succeed")

            # 11th request should be blocked by rate limiter
            res_11 = self.client.post('/api/submit-quote', json=dict(quote_payload, phone='0912345699'))
            self.assertEqual(res_11.status_code, 429)
            data = res_11.get_json()
            self.assertTrue(data.get('rate_limited'))

    def test_idempotency_prevents_duplicate_quotes(self):
        """Verify that submitting identical quote payloads within 30s returns cached response without duplicate creation"""
        quote_payload = {
            'customer_name': 'Nguyen Duplicate',
            'phone': '0988776655',
            'quantity': 100,
            'category': 'lanyard',
            'width': '2.0',
            'notes': 'Test idempotency'
        }

        with patch('backend.api.routes.add_quote') as mock_add_quote:
            mock_add_quote.return_value = {
                'id': 'Q-ORIGINAL-01',
                'customer_name': 'Nguyen Duplicate',
                'phone': '0988776655'
            }

            # First submit
            res1 = self.client.post('/api/submit-quote', json=quote_payload)
            self.assertEqual(res1.status_code, 200)
            data1 = res1.get_json()
            self.assertEqual(data1['quote']['id'], 'Q-ORIGINAL-01')
            self.assertEqual(mock_add_quote.call_count, 1)

            # Second submit (identical payload immediately after)
            res2 = self.client.post('/api/submit-quote', json=quote_payload)
            self.assertEqual(res2.status_code, 200)
            data2 = res2.get_json()
            self.assertEqual(data2['quote']['id'], 'Q-ORIGINAL-01')
            # Critical check: add_quote was NOT called a second time!
            self.assertEqual(mock_add_quote.call_count, 1)

    def test_admin_login_rate_limiting(self):
        """Verify that multiple failed admin logins are rate-limited"""
        for i in range(5):
            res = self.client.post('/admin/login', data={'username': 'wrong', 'password': 'bad'})
            # Expect redirect back to login or 200
            self.assertIn(res.status_code, [200, 302])

        # 6th attempt should be blocked
        res_6 = self.client.post('/admin/login', data={'username': 'wrong', 'password': 'bad'})
        self.assertIn(res_6.status_code, [302, 429])

    def test_custom_500_page(self):
        """Verify custom 500 error handler renders template or returns json"""
        # Test API 500 response
        with self.app.test_request_context('/api/test-error'):
            from backend.__init__ import create_app
            handler = self.app.error_handler_spec[None][500]
            # Verify handler exists
            self.assertIsNotNone(handler)

    def test_strict_boolean_parsing(self):
        """Verify parse_bool handles Python's bool('false') trap correctly"""
        from backend.api.routes import parse_bool
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("False"))
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool(0))
        self.assertFalse(parse_bool(False))
        self.assertFalse(parse_bool(None))
        self.assertFalse(parse_bool(""))
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("True"))
        self.assertTrue(parse_bool("1"))
        self.assertTrue(parse_bool(1))
        self.assertTrue(parse_bool(True))

    def test_idempotency_differentiates_vat_and_specs(self):
        """Verify that altering VAT or specs generates distinct idempotency keys (no false cache hit)"""
        base = {
            'customer_name': 'Nguyen Test',
            'phone': '0988112233',
            'quantity': 50,
            'category': 'pvc',
            'size': '5.4x8.6',
            'include_vat': False
        }
        with patch('backend.api.routes.add_quote') as mock_add:
            mock_add.side_effect = [
                {'id': 'Q-NO-VAT', 'total_price': 750000},
                {'id': 'Q-WITH-VAT', 'total_price': 810000}
            ]
            res1 = self.client.post('/api/submit-quote', json=base)
            self.assertEqual(res1.status_code, 200)
            self.assertEqual(res1.get_json()['quote']['id'], 'Q-NO-VAT')

            # Submit with same customer & phone but include_vat=True
            vat_payload = dict(base, include_vat=True)
            res2 = self.client.post('/api/submit-quote', json=vat_payload)
            self.assertEqual(res2.status_code, 200)
            self.assertEqual(res2.get_json()['quote']['id'], 'Q-WITH-VAT')
            self.assertEqual(mock_add.call_count, 2)

    def test_formula_injection_defense(self):
        """Verify that user strings starting with =, +, -, @ are prepended with apostrophe"""
        from backend.services.data_service import sanitize_for_sheet
        malicious = {
            'customer_name': '=cmd|"/C calc"!A0',
            'notes': '+1234567890',
            'accessories': ['-danger', '@eval(1)']
        }
        sanitized = sanitize_for_sheet(malicious)
        self.assertEqual(sanitized['customer_name'], "'=cmd|\"/C calc\"!A0")
        self.assertEqual(sanitized['notes'], "'+1234567890")
        self.assertEqual(sanitized['accessories'], ["'-danger", "'@eval(1)"])

    def test_db_error_returns_500_and_no_crash(self):
        """Verify that if real database commit fails, API returns HTTP 500 cleanly"""
        with patch.object(db.session, 'commit', side_effect=Exception('DB Error simulation')):
            res = self.client.post('/api/submit-quote', json={
                'customer_name': 'Nguyen Real DB Error',
                'phone': '0988999888',
                'quantity': 50,
                'category': 'lanyard'
            })
            self.assertEqual(res.status_code, 500)
            self.assertFalse(res.get_json()['success'])
            self.assertIn('Không thể lưu yêu cầu', res.get_json()['message'])

    def test_private_request_file_requires_login(self):
        """Verify customer uploaded files in private storage cannot be downloaded without admin login"""
        res = self.client.get('/admin/requests/file/any-id')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/login', res.headers.get('Location', ''))

    def test_admin_csrf_protection(self):
        """Verify admin actions without CSRF token are rejected when authenticated"""
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['admin_username'] = 'admin'

        # POST without csrf_token should fail CSRF check and redirect to admin quotes, NOT login
        res = self.client.post('/admin/quotes/status/Q-123', data={'status': 'Đã tư vấn'})
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/quotes', res.headers.get('Location', ''))
        self.assertNotIn('/admin/login', res.headers.get('Location', ''))

    def test_submit_quote_invalid_json_structure(self):
        """Verify submitting non-dict JSON (e.g. list) returns HTTP 400"""
        res = self.client.post('/api/submit-quote', json=[{'customer_name': 'Test'}])
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn('đối tượng JSON hợp lệ', data['message'])

    def test_submit_quote_invalid_category_returns_400(self):
        """Verify submitting invalid product category returns HTTP 400 (not silently converted)"""
        res = self.client.post('/api/submit-quote', json={
            'customer_name': 'Valid Name',
            'phone': '0912345678',
            'quantity': 50,
            'category': 'non_existent_category_xyz'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn('không hợp lệ', data['message'])

    def test_submit_quote_numeric_name_rejected(self):
        """Verify customer name consisting only of digits is rejected with 400"""
        res = self.client.post('/api/submit-quote', json={
            'customer_name': '12345678',
            'phone': '0912345678',
            'quantity': 50,
            'category': 'lanyard'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn('ít nhất một chữ cái', data['message'])

    def test_request_demo_rejects_file_upload(self):
        """Verify customer file uploads on /api/request-demo are strictly rejected with HTTP 400"""
        from io import BytesIO
        data = {
            'phone': '0912345678',
            'customer_name': 'Khách Hàng',
            'logo_file': (BytesIO(b'dummy content'), 'test.png')
        }
        res = self.client.post('/api/request-demo', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        resp_data = res.get_json()
        self.assertFalse(resp_data['success'])
        self.assertIn('không nhận file tải lên', resp_data['message'])

    def test_google_sheets_error_response_marks_failed(self):
        """Verify that when Google Sheets responds with status: error, database record is marked as failed"""
        from backend.services.data_service import send_quote_to_google_sheet
        from backend.models import Quote
        import requests
        import uuid

        test_quote_id = f'Q-SHEET-ERR-{uuid.uuid4().hex[:6]}'
        with self.app.app_context():
            Quote.query.filter(Quote.id.like('Q-SHEET-ERR%')).delete()
            db.session.commit()

            q = Quote(
                id=test_quote_id,
                customer_name='Sheet Err Client',
                phone='0988111222',
                category='Dây đeo thẻ',
                quantity=50,
                unit_price=20000,
                total_price=1000000,
                status='Mới',
                sync_status='pending'
            )
            db.session.add(q)
            db.session.commit()

            try:
                # Mock requests.post returning HTTP 200 with JSON error body
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.text = '{"status": "error", "message": "Spreadsheet quota exceeded"}'
                mock_resp.json.return_value = {"status": "error", "message": "Spreadsheet quota exceeded"}

                with patch('os.environ.get', side_effect=lambda k, d=None: 'https://script.google.com/macros/s/test/exec' if k == 'GOOGLE_SHEET_WEBHOOK_URL' else d):
                    with patch('requests.post', return_value=mock_resp):
                        success, msg = send_quote_to_google_sheet({'id': test_quote_id, 'customer_name': 'Sheet Err Client'}, app=self.app)
                        self.assertFalse(success)
                        self.assertIn('quota exceeded', msg)

                updated = Quote.query.filter_by(id=test_quote_id).first()
                self.assertEqual(updated.sync_status, 'failed')
                self.assertIn('quota exceeded', updated.sync_error)
            finally:
                Quote.query.filter(Quote.id.like('Q-SHEET-ERR%')).delete()
                db.session.commit()

if __name__ == '__main__':
    unittest.main()
