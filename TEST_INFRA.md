# Test Infrastructure & Test Suite Specification: TAGLUXE

**Project**: TAGLUXE E-Commerce Platform  
**Target Repository**: `C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe`  
**Primary Mirror**: `D:\Antigravity\TAGLUXE`  
**Environment**: Python 3.11.16, Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLite / PostgreSQL  

---

## 1. Overview & Testing Philosophy

The TAGLUXE test suite provides end-to-end (E2E), integration, security, and unit verification across the entire web application. Testing follows an **opaque-box** and **contract-driven** paradigm:
- The system under test is exercised through HTTP endpoints, public APIs, administrative views, and database state invariants.
- Strict isolation is enforced between test cases: all session states, rate limiter sliding windows, and in-memory idempotency caches are cleared in `setUp()`, and temporary database records are wiped before and after each run.
- Authoritative expected values are derived from mathematical formulas, catalog specification matrices, and business rules documented in `PROJECT.md` and `ORIGINAL_REQUEST.md`.

---

## 2. Environment & Test Runners

### 2.1 Python Runtime
- **Interpreter**: `D:\Antigravity\TAGLUXE\.venv\Scripts\python.exe` (Python 3.11.16)
- **Framework**: Python standard library `unittest` (no external test runner dependencies needed).

### 2.2 Execution Commands

#### Run Full Test Suite (All Discovered Tests)
```powershell
$env:PYTHONPATH="C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe"
& "D:\Antigravity\TAGLUXE\.venv\Scripts\python.exe" -m unittest discover -s "C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe\tests" -v
```

#### Run Comprehensive E2E Test Suite (Tiers 1–4)
```powershell
$env:PYTHONPATH="C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe"
& "D:\Antigravity\TAGLUXE\.venv\Scripts\python.exe" -m unittest tests.test_e2e_comprehensive -v
```

#### Run Domain-Specific Test Modules
- **Pricing & Quote Logic**:
  ```powershell
  $env:PYTHONPATH="C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe"
  & "D:\Antigravity\TAGLUXE\.venv\Scripts\python.exe" -m unittest tests.test_quote -v
  ```
- **Security, CSRF & Rate Limiting**:
  ```powershell
  $env:PYTHONPATH="C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe"
  & "D:\Antigravity\TAGLUXE\.venv\Scripts\python.exe" -m unittest tests.test_security -v
  ```
- **SEO & Metadata**:
  ```powershell
  $env:PYTHONPATH="C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe"
  & "D:\Antigravity\TAGLUXE\.venv\Scripts\python.exe" -m unittest tests.test_seo -v
  ```

---

## 3. Directory Structure & Test Suite Layout

```
tests/
├── __init__.py                   # Package initializer
├── test_e2e_comprehensive.py     # Tiers 1-4 opaque-box E2E test suite
├── test_quote.py                 # Math calculation & quote submission tests
├── test_security.py              # CSRF, rate limit, idempotency & audit tests
└── test_seo.py                   # Metadata, JSON-LD, sitemap & robots.txt tests
```

---

## 4. Test Taxonomy (Tiers 1 to 4)

### Tier 1: Feature Coverage (Smoke & Primary Contracts)
- **Storefront & Public Routing**:
  - `GET /`: Returns HTTP 200, renders hero marquee, showcase items, dynamic products.
  - `GET /product/<id>`: Returns HTTP 200 for valid products (`lan-1`, `acc-1`, `acc-2`); returns HTTP 301 redirect for legacy lanyard URLs (`lan-2`, `lan-3` → `lan-1`); returns HTTP 404 for invalid IDs.
  - `GET /sitemap.xml`: Returns HTTP 200 with `application/xml` content type and valid XML structure.
  - `GET /robots.txt`: Returns HTTP 200, disallowing `/admin` routes.
  - `GET /ping`: Returns HTTP 200 `OK` for Render keep-alive probe.
- **Catalog & Pricing APIs**:
  - `GET /api/pricing/pvc`: Returns HTTP 200 with structured pricing tiers for all 3 PVC sizes.
  - `GET /api/pricing/holder`: Returns HTTP 200 with pricing tiers for ABS & silicone card holders.
  - `GET /api/accessories`: Returns HTTP 200 with accessory list and unit prices.
  - `GET /api/demo-images`: Returns HTTP 200 with active preview image mapping.
  - `GET /api/campaign-banner`: Returns HTTP 200 with current campaign banner configuration.
- **Price Calculation Math**:
  - Lanyards across standard tiers (10-21: 28k, 46-70: 20k, 71-120: 19k, 421-530: 16k) and width adjustments (1.5cm: -1k, 2.5cm: +2.5k).
  - PVC Cards across finishes (matte, textured, glossy at equal unit price; hole punching round/capsule at 0đ).
  - Card Holders across materials (silicone 3k-7k, plain ABS 7k, UV ABS 20k-35k).
- **Admin Access Control**:
  - Strict HTTP 302 redirect to `/admin/login` for unauthenticated requests to `/admin/products`, `/admin/accessories`, `/admin/quotes`, `/admin/requests`, `/admin/demo-images`, `/admin/campaign-banner`.
- **Magic Bytes Verification**:
  - Dual validation via `is_valid_image_file`: verifies file extension whitelist (`png`, `jpg`, `jpeg`, `webp`, `gif`) and checks 512-byte binary magic signatures. Rejects fake/disguised files.
- **Responsive Banner Markup**:
  - HTML5 `<picture>` element with `<source media="(max-width: 767px)">` and `<source media="(min-width: 768px)">`. Modal dismissed when banner is disabled or images are empty.

### Tier 2: Boundary & Corner Cases
- **Quantity Tier Boundaries**:
  - Exact tier transition points: 10, 20, 21, 45, 46, 70, 71, 100, 120, 500, 5000.
  - Minimum quantity enforcement: `quantity < 10` for lanyard/PVC returns HTTP 400; `quantity < 20` for card holder returns HTTP 400.
  - Maximum quantity constraint: `quantity > 1,000,000` returns HTTP 400.
  - Malformed inputs: negative quantities, float/boolean strings, non-numeric strings return HTTP 400.
- **CSRF Token Enforcement**:
  - All mutating admin POST endpoints reject requests without a valid CSRF token with HTTP 400 or redirection flash error.
- **Adversarial File Uploads**:
  - Files disguised with `.png` or `.jpg` extension containing plain text, shell scripts, or executable headers return HTTP 400.
  - 0-byte empty files return HTTP 400.
- **Banner Toggle Constraint**:
  - Toggling banner to active when no image has been uploaded is strictly rejected with HTTP 400.

### Tier 3: Cross-Feature Interactions
- **Quote Calculation → VAT 8% → Zalo Integration**:
  - End-to-end calculation including optional accessories and VAT 8% (`round(subtotal * 0.08)`).
  - Submitting quote creates database record in `quotes`, queues background sync task in `sync_tasks`, and provides compatible URI payload for customer Zalo consultation link (`https://zalo.me/0343019097?text=...`).
- **Banner Upload → Toggle → Storefront Markup**:
  - Admin uploads desktop and mobile banner images.
  - Banner state is saved to `storage/campaign_banner.json`.
  - Storefront homepage dynamically renders responsive `<picture>` tags.
  - Admin toggles banner off -> storefront suppresses modal output.
  - Admin deletes banner images -> state resets to disabled.
- **Admin Authentication → Sliding Window Rate Limiter → Audit Logging**:
  - Failed admin logins increment sliding window attempt counter (5 attempts per 60 seconds).
  - Excessive attempts trigger HTTP 429 rate limit error.
  - Successful logins and sensitive administrative mutations persist structured audit records to the `audit_logs` table (tracking IP, action, target, timestamp).

### Tier 4: Real-World Application Workloads
- **Full Customer Quoting & Ordering Journey**:
  1. Customer visits storefront `/` and views catalog.
  2. Customer fetches PVC card pricing via `/api/pricing/pvc`.
  3. Customer calculates customized quote with VAT 8% via `/api/calculate-price`.
  4. Customer submits quote via `/api/submit-quote`.
  5. System validates idempotency, preventing duplicate order records.
  6. Admin authenticates, reviews quote in `/admin/quotes`, and advances status to 'Đang xử lý'.
- **Admin Catalog & Campaign Lifecycle**:
  1. Admin authenticates with valid credentials.
  2. Admin adds a new custom accessory with minimum quantity constraint via `/admin/accessories/add`.
  3. Storefront API `/api/accessories` exposes the new accessory.
  4. Admin updates campaign banner images and verifies storefront rendering.
  5. Admin toggles and cleans up campaign assets.
- **Sample Kit Request Journey**:
  1. Customer submits sample request via `/api/request-demo`.
  2. Attempting file upload is safely rejected with HTTP 400.
  3. Valid request is queued in `demo_requests` and `sync_tasks`.
  4. Admin inspects demo requests in `/admin/requests` and updates contact status.

---

## 5. Isolation & State Management Patterns

To ensure test repeatability without side effects:
1. **Limiter & Idempotency Reset**:
   ```python
   limiter._records.clear()
   idempotency._cache.clear()
   ```
2. **Database Cleanup**:
   Test fixtures clean up test-prefixed entities (`Q-TEST%`, `Q2%`, `DEMO-TEST%`, `SyncTask`, `IdempotencyRecord`) within `setUp()` and `tearDown()`.
3. **Session Transactions**:
   Admin authorization in test cases uses Flask's `session_transaction`:
   ```python
   with self.client.session_transaction() as sess:
       sess['logged_in'] = True
       sess['admin_username'] = 'admin'
       sess['_admin_csrf_token'] = 'test-token-xyz'
   ```
4. **Mocking External HTTP**:
   Google Sheets synchronization HTTP calls (`requests.post`) are patched via `unittest.mock.patch` to prevent network latency and external dependency failures during local testing.

---

## 6. Authoritative Oracle Sources

Expected outputs are verified against:
- **Price Matrix**: Base tier lookup in `backend/services/data_service.py` (`calculate_lanyard_price`, `calculate_pvc_price`, `calculate_holder_price`).
- **VAT Formula**: `vat_amount = round(subtotal * 0.08)`.
- **Security Rules**: `backend/config.py` and `backend/validators.py`.
- **User Requirements**: `ORIGINAL_REQUEST.md` (R1 to R5) and `PROJECT.md`.
