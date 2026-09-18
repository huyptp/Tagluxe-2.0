import os
import shutil
import logging
from datetime import datetime
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)

def backup_sqlite_db(db_uri, base_dir):
    """Safely backup SQLite database before applying migrations with timestamped versioning"""
    if 'sqlite:///' in db_uri:
        sqlite_path = db_uri.replace('sqlite:///', '')
        if os.path.isabs(sqlite_path) and os.path.isfile(sqlite_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{sqlite_path}.{timestamp}.bak"
            standard_bak = f"{sqlite_path}.bak"
            try:
                shutil.copy2(sqlite_path, backup_path)
                shutil.copy2(sqlite_path, standard_bak)
                logger.info(f"[MIGRATION_BACKUP] SQLite database backed up to {backup_path}")
                return backup_path
            except Exception as e:
                logger.warning(f"[MIGRATION_BACKUP_WARNING] Could not backup SQLite: {e}")
    return None

def run_migrations(app, db):
    """
    Executes versioned migrations safely with dialect detection, column inspection,
    and atomic transactions for both PostgreSQL and SQLite.
    """
    with app.app_context():
        engine = db.engine
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        base_dir = app.config.get('BASE_DIR', '')

        # 1. Backup SQLite database if applicable
        backup_sqlite_db(db_uri, base_dir)

        is_postgres = 'postgres' in engine.url.drivername.lower()
        bool_default = "FALSE" if is_postgres else "0"
        sync_task_pk = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        dt_type = "TIMESTAMP"

        # 2. Ensure schema_migrations table exists
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            applied_versions = {
                row[0] for row in conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
            }

        logger.info(f"[MIGRATION] Currently applied versions: {applied_versions}")

        def column_exists(conn, table_name, column_name):
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                return False
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            return column_name in columns

        migrations = [
            (
                "v002_add_vat_and_sync",
                [
                    ("quotes", "include_vat", f"ALTER TABLE quotes ADD COLUMN include_vat BOOLEAN DEFAULT {bool_default}"),
                    ("quotes", "vat_amount", "ALTER TABLE quotes ADD COLUMN vat_amount INTEGER DEFAULT 0"),
                    ("quotes", "sync_status", "ALTER TABLE quotes ADD COLUMN sync_status VARCHAR(20) DEFAULT 'pending'"),
                    ("quotes", "sync_error", "ALTER TABLE quotes ADD COLUMN sync_error TEXT"),
                    ("demo_requests", "sync_status", "ALTER TABLE demo_requests ADD COLUMN sync_status VARCHAR(20) DEFAULT 'pending'"),
                    ("demo_requests", "sync_error", "ALTER TABLE demo_requests ADD COLUMN sync_error TEXT"),
                ]
            ),
            (
                "v003_add_punched_hole_and_retry",
                [
                    ("quotes", "punched_hole", "ALTER TABLE quotes ADD COLUMN punched_hole VARCHAR(20) DEFAULT 'none'"),
                    ("quotes", "retry_count", "ALTER TABLE quotes ADD COLUMN retry_count INTEGER DEFAULT 0"),
                    ("demo_requests", "retry_count", "ALTER TABLE demo_requests ADD COLUMN retry_count INTEGER DEFAULT 0"),
                ]
            ),
            (
                "v004_create_idempotency_table",
                [
                    (
                        "idempotency_records",
                        None,
                        """
                        CREATE TABLE IF NOT EXISTS idempotency_records (
                            key VARCHAR(64) PRIMARY KEY,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            response_json TEXT NOT NULL
                        )
                        """
                    )
                ]
            ),
            (
                "v005_sync_tasks_and_idempotency_upgrade",
                [
                    ("idempotency_records", "request_id", "ALTER TABLE idempotency_records ADD COLUMN request_id VARCHAR(64)"),
                    ("idempotency_records", "content_hash", "ALTER TABLE idempotency_records ADD COLUMN content_hash VARCHAR(64)"),
                    ("idempotency_records", "status", "ALTER TABLE idempotency_records ADD COLUMN status VARCHAR(20) DEFAULT 'COMPLETED'"),
                    ("quotes", "idempotency_key", "ALTER TABLE quotes ADD COLUMN idempotency_key VARCHAR(64)"),
                    ("demo_requests", "idempotency_key", "ALTER TABLE demo_requests ADD COLUMN idempotency_key VARCHAR(64)"),
                    ("demo_requests", "created_at_dt", f"ALTER TABLE demo_requests ADD COLUMN created_at_dt {dt_type}"),
                    (
                        "sync_tasks",
                        None,
                        f"""
                        CREATE TABLE IF NOT EXISTS sync_tasks (
                            id {sync_task_pk},
                            event_key VARCHAR(64) UNIQUE NOT NULL,
                            record_type VARCHAR(20) NOT NULL,
                            record_id VARCHAR(50) NOT NULL,
                            payload TEXT NOT NULL,
                            status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                            attempt_count INTEGER DEFAULT 0 NOT NULL,
                            next_retry_at {dt_type},
                            last_error TEXT,
                            lease_until {dt_type},
                            worker_id VARCHAR(64),
                            created_at {dt_type} DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            updated_at {dt_type} DEFAULT CURRENT_TIMESTAMP NOT NULL
                        )
                        """
                    )
                ]
            )
        ]

        for version, tasks in migrations:
            if version in applied_versions:
                continue

            logger.info(f"[MIGRATION] Applying migration: {version}")
            try:
                with engine.begin() as conn:
                    for table_name, col_name, sql in tasks:
                        if col_name is not None:
                            if not column_exists(conn, table_name, col_name):
                                logger.info(f"[MIGRATION] Adding column {col_name} to {table_name}")
                                conn.execute(text(sql))
                        else:
                            conn.execute(text(sql))

                    conn.execute(
                        text("INSERT INTO schema_migrations (version, applied_at) VALUES (:v, :t)"),
                        {"v": version, "t": datetime.now()}
                    )
                logger.info(f"[MIGRATION] Successfully applied: {version}")
            except Exception as e:
                logger.error(f"[MIGRATION_FAILED] Migration {version} failed: {e}")
                raise RuntimeError(f"Database migration failed at {version}: {e}")

        return True
