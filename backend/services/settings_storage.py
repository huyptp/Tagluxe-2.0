"""Admin settings live with the database, not the deployment's temporary files."""
import json
import os
from backend.database import db
from backend.models import SiteSetting

SETTINGS = {'demo_images', 'campaign_banner', 'notifications', 'payments'}


def read_setting(key):
    if key not in SETTINGS:
        raise ValueError('Unknown site setting')
    row = db.session.get(SiteSetting, key)
    return json.loads(row.value_json) if row else {}


def write_setting(key, value):
    if key not in SETTINGS or not isinstance(value, dict):
        raise ValueError('Invalid site setting')
    row = db.session.get(SiteSetting, key)
    if row is None:
        row = SiteSetting(key=key)
        db.session.add(row)
    row.value_json = json.dumps(value, ensure_ascii=False)
    db.session.commit()


def import_legacy_settings(base_dir):
    """One-time, non-destructive import; an existing database value always wins."""
    for key in ('demo_images', 'campaign_banner'):
        if db.session.get(SiteSetting, key) is not None:
            continue
        path = os.path.join(base_dir, 'storage', key + '.json')
        value = {}
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as source:
                value = json.load(source)
            if not isinstance(value, dict):
                raise ValueError('Invalid legacy settings file: ' + key)
        db.session.add(SiteSetting(key=key, value_json=json.dumps(value, ensure_ascii=False)))
    db.session.commit()
