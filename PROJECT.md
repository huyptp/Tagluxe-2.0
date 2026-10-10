# Project: TAGLUXE Comprehensive Deep Testing & Auto-Repair

## Architecture
- **Backend**: Flask 3.1.3 modular application with application factory (`create_app`), Blueprint routing (`storefront_bp`, `api_bp`, `admin_bp`), Flask-SQLAlchemy 3.1.1 ORM, and Gunicorn 26.2.0 WSGI server.
- **Database**: SQLite (`tagluxe.db`) for local development; PostgreSQL for production on Render with dynamic connection string adaptation (`postgresql://`).
- **Data Flow**:
  - Storefront Client (Vanilla JS/CSS, HTML5 `<picture>`, CSS Grid/Flexbox, Piecewise Quantity Slider)
  - RESTful AJAX APIs (`/api/calculate-price`, `/api/submit-quote`, `/api/request-demo`, `/api/pricing/*`)
  - Admin Dashboard (`/admin/*`) guarded by session auth, CSRF token validation, IP sliding window rate limiting, and persistent audit logging.
  - Background Workers: Google Sheets asynchronous sync task worker with exponential backoff; Render keep-alive ping daemon.
- **Repository Setup**:
  - Worktree: `C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe` (Branch: `continue_developing_tagluxe`)
  - Primary Repository: `D:\Antigravity\TAGLUXE` (Branch: `main`)
  - Strict Rule: NEVER run `git push` under any circumstance.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Public Routes & HTTP 200 | Verify HTTP 200 OK for `/`, `/product/<id>`, `/sitemap.xml`, `/robots.txt`, `/ping` | M1 | R1, survey |
| 2 | Error Handling & SEO Headers | Custom 404/500 error pages, automatic DB rollback on 500, `noindex, nofollow` headers | M1 | R1, survey |
| 3 | Lanyard Price Calculation | 13 base tiers (10-5000+), width adjustments (1.5, 2.0, 2.5cm), accessories (+2.5k), min_quantity constraint | M1 | R1, survey |
| 4 | PVC Card Price Calculation | 7 tiers, 3 sizes (5.4x8.6, 7x11, 9x12), matte/textured/glossy 0đ, hole punching (none/capsule/round) 0đ | M1 | R1, survey |
| 5 | Card Holder Price Calculation | 3 materials (silicone 3-7k, plain ABS 7k, custom UV ABS 20-35k), orientation vertical/horizontal 0đ | M1 | R1, survey |
| 6 | Combo & VAT Calculation | Combo pricing logic, VAT 8% calculation (`round(subtotal * 0.08)`), shipping promotions | M1 | R1, survey |
| 7 | User Interaction Flows | Fast quote submission (`/api/submit-quote`), sample kit request (`/api/request-demo`), Zalo 1-touch hotline button | M1 | R1, survey |
| 8 | Product Showcase Galleries | Lanyards dual reverse marquee (pause on hover); PVC Cards & Card Holders 1-row manual horizontal scroll box with drag | M1 | R1, survey, user clarification |
| 9 | Admin Access Control & Session | Strict HTTP 302 redirect for unauthorized `/admin/*` to `/admin/login`, secure session cookies, 7-day lifetime | M2 | R2, survey |
| 10 | Admin CSRF & Rate Limiting | Constant-time CSRF validation on all POST routes, sliding window limiter (5 attempts/min on login) | M2 | R2, survey |
| 11 | Audit Logging | Persistent logging of all admin mutations (IP, action, target, timestamp) to `audit_logs` | M2 | R2, survey |
| 12 | Accessories & Pricing Admin | `/admin/accessories` unit prices, bulk tier updates, CRUD accessories, `min_quantity` flag | M2 | R2, survey |
| 13 | Demo Images Admin | `/admin/demo-images` 3 tabs (lanyards, PVC hole punch, card cases) with 1-touch AJAX upload | M2 | R2, survey |
| 14 | Campaign Banner Admin | `/admin/campaign-banner` Desktop (16:9) & Mobile (4:5) upload, live preview, instant toggle, individual/all delete | M2 | R2, survey |
| 15 | File Upload & Magic Bytes | Dual validation: extension whitelist + 512-byte magic header verification, reject malicious fake files with HTTP 400 | M3 | R3, survey |
| 16 | Responsive Popup Banner | HTML5 `<picture>` tag: desktop `>=768px` (16:9), mobile `<768px` (4:5), [X] close button, safe constraint (never show if empty) | M3 | R3, survey |
| 17 | Auto-Repair & Sync to Primary Repo | Repair any discovered bugs, sync all modified files from worktree to `D:\Antigravity\TAGLUXE`, clean temp files | M4 | R4, survey |
| 18 | E2E Testing Suite (Tiers 1-4) | Comprehensive opaque-box E2E test suite covering routes, pricing, security, magic bytes, responsive markup | E2E | Dual Track |
| 19 | Final E2E Pass & Adversarial Hardening | Pass 100% E2E test suite (Phase 1) + White-box adversarial testing (Phase 2) | M5 | Final Milestone |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Design and implement complete opaque-box E2E test suite (Tiers 1-4), publish `TEST_READY.md` | none | IN_PROGRESS |
| M1 | Storefront, Pricing & Showcase | Verify & auto-repair public routes, 3-category pricing calculator, quote/demo flows, dual marquee & 1-row scroll layouts | none | IN_PROGRESS |
| M2 | Admin Security & Module Management | Verify & auto-repair admin auth redirects, CSRF, rate limit, audit logs, accessories/pricing CRUD, demo images 3 tabs, banner CRUD | none | PLANNED |
| M3 | Image Magic Bytes & Responsive Popup | Verify & auto-repair 512-byte magic byte image verification and HTML5 `<picture>` responsive banner popup display & safe dismissal | M1, M2 | PLANNED |
| M4 | Auto-Repair, Sync & Cleanup | Verify worktree health, synchronize all updated files to primary repository `D:\Antigravity\TAGLUXE`, clean temp files | M1, M2, M3 | PLANNED |
| M5 | Final E2E Pass & Adversarial Hardening | Execute full E2E test suite (Phase 1: 100% pass) + Adversarial coverage hardening (Phase 2: Tier 5) | E2E, M4 | PLANNED |

## Interface Contracts
### Storefront & API ↔ Pricing Engine
- `POST /api/calculate-price`:
  - Request JSON: `{"category": str, "quantity": int, "width": str, "accessories": list, "finish": str, "punched_hole": str, "holder_type": str, "orientation": str, "printed_logo": str, "include_vat": bool}`
  - Response JSON: `{"success": true, "data": {"unit_price": int, "subtotal": int, "vat_amount": int, "total_price": int}}`
- `POST /api/submit-quote`:
  - Request JSON/Form: Quote input + `customer_name`, `phone`, `notes`
  - Response JSON: `{"success": true, "quote_id": str, "zalo_link": str}`
- `POST /api/request-demo`:
  - Request JSON/Form: Demo input + `customer_name`, `phone`, `notes`
  - Response JSON: `{"success": true, "message": str}` (Rejects file uploads with 400)

### Admin ↔ Security & File Storage
- `validate_csrf()`: Requires `session['_admin_csrf_token']` matching form `csrf_token` or header `X-CSRF-Token`.
- `is_valid_image_file(file_storage)`: Checks extension in `{'png', 'jpg', 'jpeg', 'webp', 'gif'}` and verifies binary magic signature (`\x89PNG`, `\xff\xd8\xff`, `GIF8`, `RIFF...WEBP`).

## Code Layout
- Worktree Root: `C:\Users\dinhq\.gemini\antigravity\worktrees\TAGLUXE\continue_developing_tagluxe`
  - `app.py`: WSGI entry point
  - `backend/`:
    - `__init__.py`: App factory, error handlers, security headers, keep-alive worker
    - `config.py`: Environment configuration, secret keys, rate limit rules
    - `database.py`: Database connection resolver, initial data seeding
    - `models.py`: SQLAlchemy models
    - `migrations.py`: Schema migrations (v002 - v010)
    - `security.py`: Rate limiting and request sanitization
    - `validators.py`: Input validation functions
    - `storefront/routes.py`: Public views
    - `api/routes.py`: Public JSON APIs
    - `admin/routes.py`: Admin views and mutations
    - `services/data_service.py`: Core pricing calculations and catalog management
    - `services/sync_worker.py`: Background Google Sheets sync queue worker
  - `frontend/storefront/templates/`: Storefront HTML templates (`base.html`, `index.html`, `product.html`, `404.html`, `500.html`)
  - `frontend/admin/templates/`: Admin HTML templates (`accessories.html`, `demo_images.html`, `campaign_banner.html`, `products.html`, `quotes.html`, `requests.html`, `login.html`)
  - `templates/components/price_calculator.html`: Online price calculator template and client script
  - `storage/`: `demo_images.json`, `campaign_banner.json`, backups
  - `tests/`: E2E and unit test suites
- Primary Repository: `D:\Antigravity\TAGLUXE` (Mirror of all production files)
