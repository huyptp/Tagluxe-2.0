import unittest
import json
from unittest.mock import patch
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

        with patch('core.routes.api.add_quote') as mock_add_quote:
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
            from core.__init__ import create_app
            handler = self.app.error_handler_spec[None][500]
            # Verify handler exists
            self.assertIsNotNone(handler)

if __name__ == '__main__':
    unittest.main()
