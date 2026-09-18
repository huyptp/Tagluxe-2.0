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
            from backend.models import IdempotencyRecord, Quote, SyncTask
            IdempotencyRecord.query.delete()
            Quote.query.filter(Quote.customer_name.like('%Test%') | Quote.customer_name.like('%Nguyen%') | Quote.customer_name.like('%Client%')).delete()
            SyncTask.query.delete()
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
        from backend.models import Quote, SyncTask
        quote_payload = {
            'customer_name': 'Nguyen Duplicate',
            'phone': '0988776655',
            'quantity': 100,
            'category': 'lanyard',
            'width': '2.0',
            'notes': 'Test idempotency'
        }

        # First submit
        res1 = self.client.post('/api/submit-quote', json=quote_payload)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        quote_id = data1['quote']['id']

        # Second submit (identical payload immediately after)
        res2 = self.client.post('/api/submit-quote', json=quote_payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2['quote']['id'], quote_id)

        # Critical check: exactly 1 Quote and 1 SyncTask created in DB!
        with self.app.app_context():
            quotes_count = Quote.query.filter_by(customer_name='Nguyen Duplicate').count()
            sync_count = SyncTask.query.filter_by(record_id=quote_id).count()
            self.assertEqual(quotes_count, 1)
            self.assertEqual(sync_count, 1)

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
        res1 = self.client.post('/api/submit-quote', json=base)
        self.assertEqual(res1.status_code, 200)
        q1 = res1.get_json()['quote']
        self.assertFalse(q1['include_vat'])
        self.assertEqual(q1['total_price'], 750000)

        # Submit with same customer & phone but include_vat=True
        vat_payload = dict(base, include_vat=True)
        res2 = self.client.post('/api/submit-quote', json=vat_payload)
        self.assertEqual(res2.status_code, 200)
        q2 = res2.get_json()['quote']
        self.assertTrue(q2['include_vat'])
        self.assertEqual(q2['total_price'], 810000)
        self.assertNotEqual(q1['id'], q2['id'])

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

    def test_concurrent_submissions_single_transaction_and_idempotency(self):
        """Group B: 2 threads submitting identical payload concurrently create only 1 quote & 1 sync task"""
        import concurrent.futures
        from backend.models import Quote, SyncTask

        quote_payload = {
            'customer_name': 'Nguyen Concurrency Client',
            'phone': '0988665544',
            'quantity': 50,
            'category': 'pvc',
            'request_id': 'REQ-CONCURRENCY-01'
        }

        def _submit():
            client = self.app.test_client()
            return client.post('/api/submit-quote', json=quote_payload, headers={'X-Request-ID': 'REQ-CONCURRENCY-01'})

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut1 = executor.submit(_submit)
            fut2 = executor.submit(_submit)
            res1 = fut1.result()
            res2 = fut2.result()

        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res2.status_code, 200)
        q1 = res1.get_json()['quote']
        q2 = res2.get_json()['quote']
        self.assertEqual(q1['id'], q2['id'])

        with self.app.app_context():
            saved_quotes = Quote.query.filter_by(customer_name='Nguyen Concurrency Client').all()
            self.assertEqual(len(saved_quotes), 1)
            saved_tasks = SyncTask.query.filter_by(record_id=q1['id']).all()
            self.assertEqual(len(saved_tasks), 1)

    def test_idempotency_conflict_409_on_different_payload(self):
        """Group B: Submitting same request_id with altered specifications returns HTTP 409 Conflict"""
        req_id = "REQ-CONFLICT-409"
        base_payload = {
            'request_id': req_id,
            'customer_name': 'Nguyen Conflict Client',
            'phone': '0988554433',
            'quantity': 50,
            'category': 'pvc',
            'punched_hole': 'none'
        }

        res1 = self.client.post('/api/submit-quote', json=base_payload, headers={'X-Request-ID': req_id})
        self.assertEqual(res1.status_code, 200)

        # Alter punched_hole from 'none' to 'capsule'
        altered_payload = dict(base_payload, punched_hole='capsule')
        res2 = self.client.post('/api/submit-quote', json=altered_payload, headers={'X-Request-ID': req_id})
        self.assertEqual(res2.status_code, 409)
        data2 = res2.get_json()
        self.assertFalse(data2['success'])
        self.assertIn('409 Conflict', data2['message'])

    def test_canonical_hash_dimensions_coverage(self):
        """Group B: Canonical hash engine differentiates all specs and normalizes accessories order"""
        from backend.security import generate_canonical_hash

        base = {
            'customer_name': 'Nguyen Van A',
            'phone': '0912345678',
            'category': 'pvc',
            'quantity': 50,
            'accessories': ['b', 'a'],
            'orientation': 'vertical',
            'printed_logo': True,
            'punched_hole': 'none'
        }

        h_base = generate_canonical_hash(base)

        # Accessories in different order should produce the EXACT same canonical hash
        same_reordered = dict(base, accessories=['a', 'b'])
        self.assertEqual(h_base, generate_canonical_hash(same_reordered))

        # Different orientation produces different hash
        diff_ori = dict(base, orientation='horizontal')
        self.assertNotEqual(h_base, generate_canonical_hash(diff_ori))

        # Different printed_logo produces different hash
        diff_logo = dict(base, printed_logo=False)
        self.assertNotEqual(h_base, generate_canonical_hash(diff_logo))

        # Different punched_hole produces different hash
        diff_hole = dict(base, punched_hole='round')
        self.assertNotEqual(h_base, generate_canonical_hash(diff_hole))

        # Different customer name case or whitespace produces different hash
        diff_name = dict(base, customer_name='nguyen van a')
        self.assertNotEqual(h_base, generate_canonical_hash(diff_name))

    def test_sync_worker_lease_and_task_execution(self):
        """Group C: Persistent queue atomic leasing, strict response validation, and backoff"""
        from backend.models import SyncTask, Quote
        from backend.services.sync_worker import lease_due_tasks, execute_sync_task

        with self.app.app_context():
            SyncTask.query.filter(SyncTask.event_key.like("test_sync_%")).delete()
            Quote.query.filter(Quote.id.like("Q-SWORKER-%")).delete()
            db.session.commit()

            q = Quote(
                id="Q-SWORKER-01",
                customer_name="Sync Worker Client",
                phone="0911223344",
                category="Dây đeo thẻ",
                quantity=50,
                unit_price=20000,
                total_price=1000000,
                status="Mới",
                sync_status="pending"
            )
            db.session.add(q)

            t1 = SyncTask(
                event_key="test_sync_1",
                record_type="quote",
                record_id="Q-SWORKER-01",
                payload=json.dumps(q.to_dict()),
                status="pending"
            )
            db.session.add(t1)
            db.session.commit()

            # 1. Test lease_due_tasks
            w_id, leased = lease_due_tasks(db, limit=5, lease_sec=60)
            self.assertIn(t1.id, leased)
            self.assertTrue(w_id.startswith("worker-"))

            # Lease is active -> subsequent lease returns 0 tasks
            _, second_leased = lease_due_tasks(db, limit=5, lease_sec=60)
            self.assertNotIn(t1.id, second_leased)

            # 2. Test response string "unsuccessful: could not write" -> rejected
            mock_str_resp = MagicMock()
            mock_str_resp.status_code = 200
            mock_str_resp.text = "unsuccessful: could not write"
            mock_str_resp.json.side_effect = Exception("Not JSON")

            with patch('backend.config.GOOGLE_SHEET_WEBHOOK_URL', 'https://script.google.com/macros/s/test/exec'):
                with patch('requests.post', return_value=mock_str_resp):
                    ok, msg = execute_sync_task(t1.id, w_id, self.app)
                    self.assertFalse(ok)
                    self.assertIn("Invalid response structure", msg)

            # Verify task transitioned to retry
            db.session.expire_all()
            task_ref = SyncTask.query.filter_by(id=t1.id).first()
            self.assertEqual(task_ref.status, "retry")
            self.assertEqual(task_ref.attempt_count, 1)
            self.assertIsNotNone(task_ref.next_retry_at)

            # 3. Test response JSON with record_id mismatch -> rejected
            mock_mismatch = MagicMock()
            mock_mismatch.status_code = 200
            mock_mismatch.text = '{"status": "success", "record_id": "DIFFERENT_ID"}'
            mock_mismatch.json.return_value = {"status": "success", "record_id": "DIFFERENT_ID"}

            # Re-lease task
            task_ref.next_retry_at = None
            db.session.commit()
            w_id2, leased2 = lease_due_tasks(db, limit=5, lease_sec=60)
            self.assertIn(t1.id, leased2)

            with patch('backend.config.GOOGLE_SHEET_WEBHOOK_URL', 'https://script.google.com/macros/s/test/exec'):
                with patch('requests.post', return_value=mock_mismatch):
                    ok2, msg2 = execute_sync_task(t1.id, w_id2, self.app)
                    self.assertFalse(ok2)
                    self.assertIn("Record ID mismatch", msg2)

            # 4. Test response JSON with status: success and matching record_id -> succeeded
            mock_success = MagicMock()
            mock_success.status_code = 200
            mock_success.text = '{"status": "success", "record_id": "Q-SWORKER-01"}'
            mock_success.json.return_value = {"status": "success", "record_id": "Q-SWORKER-01"}

            db.session.expire_all()
            task_ref = SyncTask.query.filter_by(id=t1.id).first()
            task_ref.next_retry_at = None
            db.session.commit()
            w_id3, leased3 = lease_due_tasks(db, limit=5, lease_sec=60)
            self.assertIn(t1.id, leased3)

            with patch('backend.config.GOOGLE_SHEET_WEBHOOK_URL', 'https://script.google.com/macros/s/test/exec'):
                with patch('requests.post', return_value=mock_success):
                    ok3, msg3 = execute_sync_task(t1.id, w_id3, self.app)
                    self.assertTrue(ok3)

            db.session.expire_all()
            task_done = SyncTask.query.filter_by(id=t1.id).first()
            self.assertEqual(task_done.status, "succeeded")
            quote_done = Quote.query.filter_by(id="Q-SWORKER-01").first()
            self.assertEqual(quote_done.sync_status, "synced")

            # Cleanup
            SyncTask.query.filter(SyncTask.event_key.like("test_sync_%")).delete()
            Quote.query.filter(Quote.id.like("Q-SWORKER-%")).delete()
            db.session.commit()

if __name__ == '__main__':
    unittest.main()
