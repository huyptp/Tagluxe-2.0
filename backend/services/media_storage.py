"""Public shop images only. Credentials stay on the server."""
import mimetypes
import os
from urllib.parse import quote, urlsplit
import requests
from flask import Blueprint, abort, redirect, send_from_directory
from werkzeug.utils import safe_join
from backend import config

media_bp = Blueprint('media', __name__)


def storage_config():
    url = urlsplit(config.SUPABASE_URL)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.path not in ('', '/') or url.query or url.fragment:
        raise RuntimeError('SUPABASE_URL must be the HTTPS project URL.')
    if not config.SUPABASE_SECRET_KEY:
        raise RuntimeError('SUPABASE_SECRET_KEY is required for external image storage.')
    bucket = config.SUPABASE_STORAGE_BUCKET
    if not bucket or '/' in bucket or bucket in ('.', '..'):
        raise RuntimeError('Invalid image storage bucket.')
    return config.SUPABASE_URL, bucket


def public_image_url(filename):
    origin, bucket = storage_config()
    return f'{origin}/storage/v1/object/public/{quote(bucket, safe="")}/{quote(filename, safe="")}'


def save_public_image(file, path, allow_identical_existing=False):
    path = os.path.abspath(path)
    root = os.path.abspath(config.UPLOAD_FOLDER)
    if os.path.dirname(path) != root:
        raise ValueError('Image must be saved directly inside the uploads directory.')
    name = os.path.basename(path)
    if config.MEDIA_STORAGE == 'local':
        file.save(path)
        return
    if config.MEDIA_STORAGE != 'supabase':
        raise RuntimeError('Unknown MEDIA_STORAGE provider.')
    origin, bucket = storage_config()
    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    file.stream.seek(0)
    try:
        response = requests.post(f'{origin}/storage/v1/object/{quote(bucket, safe="")}/{quote(name, safe="")}',
            headers={'apikey': config.SUPABASE_SECRET_KEY, 'Content-Type': content_type,
                     'x-upsert': 'false', 'Cache-Control': '3600'},
            data=file.stream, timeout=(5, 15), allow_redirects=False)
        if response.status_code not in (200, 201) and allow_identical_existing and response.status_code in (400, 409):
            previous = requests.get(public_image_url(name), timeout=(5, 15), allow_redirects=False)
            file.stream.seek(0)
            if previous.status_code == 200 and previous.content == file.stream.read():
                return
        if response.status_code not in (200, 201):
            raise RuntimeError('Image storage rejected the upload.')
    except Exception:
        # Never fall back to temporary local storage or echo credential-bearing responses.
        raise RuntimeError('Chưa lưu được ảnh vào kho ảnh. Vui lòng kiểm tra kết nối và thử lại.') from None


@media_bp.route('/static/uploads/<path:filename>')
def public_upload(filename):
    # Bundled, existing images remain accessible during migration.
    if not filename or '/' in filename or '\\' in filename or filename in ('.', '..'):
        abort(404)
    local = safe_join(config.UPLOAD_FOLDER, filename)
    if local and os.path.isfile(local):
        return send_from_directory(config.UPLOAD_FOLDER, filename)
    if config.MEDIA_STORAGE == 'supabase':
        response = redirect(public_image_url(filename), code=302)
        response.headers['Cache-Control'] = 'no-store'
        return response
    abort(404)
