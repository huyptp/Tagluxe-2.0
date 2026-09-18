import os
from urllib.parse import urlsplit

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE = os.path.join(BASE_DIR, 'data.json')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
UPLOAD_REQUESTS_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'requests')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_REQUESTS_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
ALLOWED_REQUEST_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf', 'ai', 'psd', 'svg', 'eps', 'zip', 'rar'}

SECRET_KEY = os.environ.get('SECRET_KEY', 'tagluxe_super_secret_key')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit

FACEBOOK_PIXEL_ID = os.environ.get('FACEBOOK_PIXEL_ID', '')
GOOGLE_SITE_VERIFICATION = os.environ.get('GOOGLE_SITE_VERIFICATION', '')
RENDER = os.environ.get('RENDER', '')
from datetime import timedelta

GOOGLE_SHEET_WEBHOOK_URL = os.environ.get('GOOGLE_SHEET_WEBHOOK_URL', '')
ADMIN_NOTIFICATION_EMAIL = os.environ.get('ADMIN_NOTIFICATION_EMAIL', 'Dhuy5585@gmail.com')

# Session & Cookie Security Hardening
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = bool(RENDER)
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
