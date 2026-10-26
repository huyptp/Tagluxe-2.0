"""One-time copy from a shop SQLite backup to an EMPTY external PostgreSQL database.

Dry run: python scripts/migrate_persistent_data.py --source backup/tagluxe.db
Apply only after preserving a complete source backup and configuring .env locally.
No credentials are accepted as command-line arguments or printed.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, inspect, select, func, text, Integer
from sqlalchemy.engine import make_url
from backend.database import db
from backend import models, config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--uploads', type=Path)
    parser.add_argument('--settings', type=Path, help='Optional settings/ directory from the migration archive')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    source_path = args.source.resolve(strict=True)
    uri = 'file:' + quote(source_path.as_posix(), safe='/:') + '?mode=ro'
    source = create_engine('sqlite://', creator=lambda: sqlite3.connect(uri, uri=True))
    tables = db.metadata.sorted_tables
    existing = set(inspect(source).get_table_names())
    with source.connect() as connection:
        counts = {table.name:connection.execute(select(func.count()).select_from(table)).scalar_one()
                  for table in tables if table.name in existing}
    print('Source tables and row counts:', counts)
    if not args.apply:
        print('Dry run only. No database or images have been written.')
        return
    target_url = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://', 1)
    if not target_url.startswith(('postgresql://', 'postgresql+psycopg2://')):
        raise RuntimeError('Configure PostgreSQL DATABASE_URL in the ignored local .env first.')
    target_url = make_url(target_url).set(drivername='postgresql+psycopg2')
    # Upload public images first. A failed transfer never produces a half-imported DB.
    if args.uploads:
        from werkzeug.datastructures import FileStorage
        from backend.services.media_storage import save_public_image, storage_config
        if config.MEDIA_STORAGE != 'supabase':
            raise RuntimeError('Set MEDIA_STORAGE=supabase before transferring images.')
        storage_config()
    target = create_engine(target_url, connect_args={'sslmode':'require','connect_timeout':10})
    db.metadata.create_all(target)
    with target.begin() as connection:
        for table in tables:
            if connection.execute(select(func.count()).select_from(table)).scalar_one():
                raise RuntimeError('Destination must be empty. Existing records were not changed.')
        # Supabase REST clients must not gain access to private customer tables.
        preparer = target.dialect.identifier_preparer
        for table in tables:
            name = 'public.' + preparer.quote(table.name)
            connection.execute(text('ALTER TABLE ' + name + ' ENABLE ROW LEVEL SECURITY'))
        if args.uploads:
            for path in sorted(args.uploads.resolve(strict=True).iterdir()):
                if path.is_file() and not path.is_symlink() and path.suffix.lower().lstrip('.') in config.ALLOWED_IMAGE_EXTENSIONS:
                    with path.open('rb') as image:
                        save_public_image(FileStorage(stream=image, filename=path.name), os.path.join(config.UPLOAD_FOLDER, path.name), allow_identical_existing=True)
            print('Public image transfer completed.')
        with source.connect() as old:
            for table in tables:
                if table.name not in existing:
                    continue
                rows = [dict(row) for row in old.execute(select(table)).mappings()]
                if table.name == 'sync_tasks':
                    for row in rows:
                        if row['status'] == 'processing':
                            row.update(status='retry', worker_id=None, lease_until=None, next_retry_at=None)
                if rows:
                    connection.execute(table.insert(), rows)
                for column in table.primary_key.columns:
                    if isinstance(column.type, Integer):
                        sequence = connection.execute(text('SELECT pg_get_serial_sequence(:tbl, :col)'),
                            {'tbl':table.name,'col':column.name}).scalar()
                        if sequence:
                            maximum = connection.execute(select(func.max(column))).scalar()
                            if maximum is not None:
                                connection.execute(text('SELECT setval(CAST(:seq AS regclass), :value, true)'),
                                    {'seq':sequence,'value':maximum})
        if args.settings:
            setting_table = models.SiteSetting.__table__
            for key in ('demo_images', 'campaign_banner'):
                path = args.settings.resolve(strict=True) / (key + '.json')
                if path.is_file() and not connection.execute(select(setting_table.c.key).where(setting_table.c.key == key)).first():
                    value = json.loads(path.read_text(encoding='utf-8-sig'))
                    if not isinstance(value, dict):
                        raise RuntimeError('Invalid settings backup.')
                    connection.execute(setting_table.insert().values(key=key,value_json=json.dumps(value,ensure_ascii=False)))
        print('Copied records into the empty PostgreSQL database. Source backup was unchanged.')
    source.dispose()
    target.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # SQLAlchemy exceptions can embed credentials and customer field values.
        print('Migration stopped. No source files were changed. Check configuration, destination emptiness, image transfer and the private backup.', file=sys.stderr)
        sys.exit(1)
