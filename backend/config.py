import os
import secrets
import logging
from urllib.parse import urlsplit
from datetime import timedelta

# Base Directory: root repo
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Load .env file if present (local dev)
_env_path = os.path.join(BASE_DIR, '.env')
if os.path.isfile(_env_path):
    try:
        with open(_env_path, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    _k = _k.strip()
                    _v = _v.strip().strip("'").strip('"')
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
    except Exception:
        pass

DATA_FILE = os.path.join(BASE_DIR, 'data.json')

# Frontend Paths
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
STOREFRONT_TEMPLATES = os.path.join(FRONTEND_DIR, 'storefront', 'templates')
ADMIN_TEMPLATES = os.path.join(FRONTEND_DIR, 'admin', 'templates')
STOREFRONT_STATIC = os.path.join(FRONTEND_DIR, 'storefront', 'static')
ADMIN_STATIC = os.path.join(FRONTEND_DIR, 'admin', 'static')

# Fallback root paths for backward compatibility if needed
LEGACY_TEMPLATES = os.path.join(BASE_DIR, 'templates')
LEGACY_STATIC = os.path.join(BASE_DIR, 'static')

# Upload & Storage Folders
UPLOAD_FOLDER = os.path.join(STOREFRONT_STATIC, 'uploads')
# Private storage for client uploaded files (completely outside public static directory)
PRIVATE_STORAGE_FOLDER = os.path.join(BASE_DIR, 'storage', 'private_requests')
UPLOAD_REQUESTS_FOLDER = PRIVATE_STORAGE_FOLDER  # Alias for compatibility

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PRIVATE_STORAGE_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
# Disallow SVG and active formats to prevent stored XSS vulnerabilities
ALLOWED_REQUEST_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf', 'ai', 'psd', 'zip', 'rar'}

FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
RENDER = os.environ.get('RENDER', '')
IS_PRODUCTION = bool(RENDER or FLASK_ENV == 'production')

# Credentials are supplied by local .env or hosting environment variables.
# A temporary session key keeps the storefront available if SECRET_KEY is missing.
SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '')

if IS_PRODUCTION:
    if not os.environ.get('SECRET_KEY'):
        logging.warning('SECRET_KEY is not configured; sessions reset when the process restarts.')
    if not ADMIN_PASSWORD and not ADMIN_PASSWORD_HASH:
        logging.warning('Admin login is disabled until ADMIN_PASSWORD or ADMIN_PASSWORD_HASH is configured.')

MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit

FACEBOOK_PIXEL_ID = os.environ.get('FACEBOOK_PIXEL_ID', '')
GOOGLE_SITE_VERIFICATION = os.environ.get('GOOGLE_SITE_VERIFICATION', '')
GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID', 'G-KY6VE15P5L')
GOOGLE_TAG_MANAGER_ID = os.environ.get('GOOGLE_TAG_MANAGER_ID', 'GTM-T22MFFG9')

GOOGLE_SHEET_WEBHOOK_URL = os.environ.get('GOOGLE_SHEET_WEBHOOK_URL', '')
GOOGLE_SHEET_SECRET = os.environ.get('GOOGLE_SHEET_SECRET', '')
MEDIA_STORAGE = os.environ.get('MEDIA_STORAGE', 'local').strip().lower()
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_SECRET_KEY = os.environ.get('SUPABASE_SECRET_KEY', '')
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'tagluxe-media')
ADMIN_NOTIFICATION_EMAIL = os.environ.get('ADMIN_NOTIFICATION_EMAIL', 'Dhuy5585@gmail.com')

# Session & Cookie Security Hardening
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = bool(IS_PRODUCTION)
PERMANENT_SESSION_LIFETIME = timedelta(days=7)


def site_origin():
    value = os.environ.get('SITE_URL', 'https://tagluxe.onrender.com').rstrip('/')
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        return 'https://tagluxe.onrender.com'
    return value

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def allowed_request_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_REQUEST_EXTENSIONS
