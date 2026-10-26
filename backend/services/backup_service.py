"""Authenticated migration archive, excluding environment files and credentials."""
import json
import os
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from flask import send_file
from backend import config
from backend.database import db
from backend.services.settings_storage import read_setting


def migration_backup_response():
    folder = tempfile.TemporaryDirectory(prefix='tagluxe-backup-')
    try:
        path = os.path.join(folder.name, 'tagluxe-backup.zip')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as archive:
            if db.engine.dialect.name == 'sqlite':
                snapshot_path = os.path.join(folder.name, 'tagluxe.db')
                source = db.engine.raw_connection()
                try:
                    with closing(sqlite3.connect(snapshot_path)) as snapshot:
                        source.driver_connection.backup(snapshot)
                finally:
                    source.close()
                archive.write(snapshot_path, 'tagluxe.db')
            for key in ('demo_images', 'campaign_banner'):
                archive.writestr('settings/' + key + '.json', json.dumps(read_setting(key), ensure_ascii=False))
            for name in sorted(os.listdir(config.UPLOAD_FOLDER)):
                image = os.path.join(config.UPLOAD_FOLDER, name)
                if os.path.isfile(image) and not os.path.islink(image) and name.rsplit('.', 1)[-1].lower() in config.ALLOWED_IMAGE_EXTENSIONS:
                    archive.write(image, 'uploads/' + name)
            archive.writestr('manifest.json', json.dumps({'format':1, 'database':db.engine.dialect.name,
                'scope':'SQLite snapshot when applicable, public local images, site settings. No environment secrets.',
                'external_images_included':False}, ensure_ascii=False))
        response = send_file(path, as_attachment=True, download_name='tagluxe-migration-backup.zip', mimetype='application/zip')
        response.direct_passthrough = False
        # Keep the temporary files alive until the streaming response closes.
        response.call_on_close(folder.cleanup)
        return response
    except Exception:
        folder.cleanup()
        raise
