import os
import time
import threading
import urllib.request
import jinja2
from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix
from backend.config import (
    BASE_DIR, STOREFRONT_TEMPLATES, ADMIN_TEMPLATES, LEGACY_TEMPLATES,
    STOREFRONT_STATIC, ADMIN_STATIC, LEGACY_STATIC,
    UPLOAD_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY,
    FACEBOOK_PIXEL_ID, GOOGLE_SITE_VERIFICATION, RENDER, site_origin,
    SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE, SESSION_COOKIE_SECURE,
    PERMANENT_SESSION_LIFETIME
)
from backend.storefront.routes import storefront_bp
from backend.admin.routes import admin_bp
from backend.api.routes import api_bp

def _keep_alive_worker():
    """
    Background thread: ping the app's own public URL every 10 minutes
    so Render's free tier never sleeps. Only runs on Render (RENDER env var set).
    """
    site_url = site_origin()
    ping_url = f'{site_url}/ping'
    time.sleep(120)
    while True:
        try:
            with urllib.request.urlopen(ping_url, timeout=15) as resp:
                pass
        except Exception:
            pass
        time.sleep(600)

def create_app(test_config=None):
    app = Flask(
        __name__,
        static_folder=STOREFRONT_STATIC,
        static_url_path='/static'
    )

    # Multi-source Jinja ChoiceLoader for isolated Storefront and Admin templates
    app.jinja_loader = jinja2.ChoiceLoader([
        jinja2.FileSystemLoader(STOREFRONT_TEMPLATES),
        jinja2.PrefixLoader({
            'admin': jinja2.FileSystemLoader(ADMIN_TEMPLATES)
        }),
        jinja2.FileSystemLoader(LEGACY_TEMPLATES)  # fallback
    ])

    app.secret_key = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['FACEBOOK_PIXEL_ID'] = FACEBOOK_PIXEL_ID
    app.config['GOOGLE_SITE_VERIFICATION'] = GOOGLE_SITE_VERIFICATION
    app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
    app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
    app.config['PERMANENT_SESSION_LIFETIME'] = PERMANENT_SESSION_LIFETIME

    # Wrap WSGI app with ProxyFix to safely parse X-Forwarded headers behind reverse proxies (Render, Nginx)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    if test_config:
        app.config.update(test_config)

    # Khởi tạo Database (SQLite cục bộ hoặc PostgreSQL trên Render)
    from backend.database import init_db
    init_db(app)

    # Đăng ký Blueprints
    app.register_blueprint(storefront_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Context processors & middleware
    @app.context_processor
    def seo_context():
        return {'site_url': site_origin()}

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from backend.database import db
        try:
            db.session.rollback()
        except Exception:
            pass
        if request.path.startswith('/api/'):
            return {'success': False, 'message': 'Máy chủ đang bận xử lý. Vui lòng thử lại sau ít giây.'}, 500
        return render_template('500.html'), 500

    @app.after_request
    def add_seo_headers(response):
        if request.path.startswith('/admin') or request.path == '/ping' or response.status_code >= 400:
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        if '/static/' in response.headers.get('Content-Type', '') or request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=2592000'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    if RENDER:
        _t = threading.Thread(target=_keep_alive_worker, daemon=True)
        _t.start()

    return app
