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
            ),
            (
                "v006_update_pvc_price_tiers_discount_1500",
                [
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 16500 WHERE category IN ('pvc', 'pvc_5.4x8.6') AND min_qty = 10 AND max_qty = 20"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 13500 WHERE category IN ('pvc', 'pvc_5.4x8.6') AND min_qty = 21 AND max_qty = 50"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 10500 WHERE category IN ('pvc', 'pvc_5.4x8.6') AND min_qty = 51 AND max_qty = 100"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 8500 WHERE category IN ('pvc', 'pvc_5.4x8.6') AND min_qty = 101 AND max_qty = 200"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 21500 WHERE category = 'pvc_7x11' AND min_qty = 10 AND max_qty = 20"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 16500 WHERE category = 'pvc_7x11' AND min_qty = 21 AND max_qty = 50"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 15500 WHERE category = 'pvc_7x11' AND min_qty = 51 AND max_qty = 100"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 14500 WHERE category = 'pvc_7x11' AND min_qty = 101 AND max_qty = 200"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 23500 WHERE category = 'pvc_9x12' AND min_qty = 10 AND max_qty = 20"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 20500 WHERE category = 'pvc_9x12' AND min_qty = 21 AND max_qty = 50"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 18500 WHERE category = 'pvc_9x12' AND min_qty = 51 AND max_qty = 100"),
                    ("price_tiers", None, "UPDATE price_tiers SET unit_price = 17500 WHERE category = 'pvc_9x12' AND min_qty = 101 AND max_qty = 200"),
                ]
            ),
            (
                "v007_add_lanyard_photos_to_lan1",
                [
                    (
                        "products",
                        None,
                        """UPDATE products SET images_json = '["media_1789714507972.jpg", "media_1789714507975.jpg", "media_1789714507982.jpg", "media_1789662028575.jpg", "media_1789320576594.jpg", "media_1789662086201.jpg", "media_1789662028590.jpg", "media_1789662086215.jpg", "media_1789662064859.jpg", "media_1789662064871.jpg", "media_1789662064894.jpg", "media_1789662086196.jpg", "media_1789662086207.jpg", "media_1789662028598.jpg", "media_1789662028605.jpg", "media_1789662028584.jpg", "media_1786037379657.jpg", "media_1789285818722.jpg", "media_1789286120138.jpg", "media_1786037379884.jpg", "media_1789285818629.jpg", "media_1789285818730.jpg", "media_1789285818752.jpg", "media_1789285818740.jpg", "media_1786037379878.jpg"]' WHERE id = 'lan-1'"""
                    )
                ]
            ),
            (
                "v008_seed_catalog_products_if_empty",
                [
                    (
                        "products",
                        None,
                        """INSERT INTO products (id, name, category, description, images_json, width, material, min_order, price_type, price, featured, visible)
                        SELECT 'lan-1', 'Dây đeo thẻ in chuyển nhiệt cao cấp', 'lanyard',
                               'Dây đeo thẻ in chuyển nhiệt cao cấp in ấn sắc nét theo yêu cầu riêng. Chất liệu lụa Satin cao cấp mềm mịn, công nghệ in chuẩn màu, chống bong tróc, bền màu tuyệt đối. Phù hợp cho doanh nghiệp, trường học, sự kiện và fandom.',
                               '["media_1789714507972.jpg", "media_1789714507975.jpg", "media_1789714507982.jpg", "media_1789662028575.jpg", "media_1789320576594.jpg", "media_1789662086201.jpg", "media_1789662028590.jpg", "media_1789662086215.jpg", "media_1789662064859.jpg", "media_1789662064871.jpg", "media_1789662064894.jpg", "media_1789662086196.jpg", "media_1789662086207.jpg", "media_1789662028598.jpg", "media_1789662028605.jpg", "media_1789662028584.jpg", "media_1786037379657.jpg", "media_1789285818722.jpg", "media_1789286120138.jpg", "media_1786037379884.jpg", "media_1789285818629.jpg", "media_1789285818730.jpg", "media_1789285818752.jpg", "media_1789285818740.jpg", "media_1786037379878.jpg"]',
                               '1.5 cm / 2.0 cm / 2.5 cm', 'Lụa Satin Cao Cấp', 10, 'contact', 0, 1, 1
                        WHERE NOT EXISTS (SELECT 1 FROM products WHERE id = 'lan-1')"""
                    ),
                    (
                        "products",
                        None,
                        """INSERT INTO products (id, name, category, description, images_json, width, material, min_order, price_type, price, featured, visible)
                        SELECT 'acc-1', 'Thẻ nhựa PVC in theo yêu cầu', 'accessory',
                               'Thẻ nhựa PVC in 2 mặt full màu sắc nét theo thiết kế riêng. Phù hợp cho thẻ nhân viên, thẻ sinh viên, thẻ sự kiện, fandom và câu lạc bộ. Nhận từ 10 thẻ.',
                               '["media_1789319927667.jpg", "media_1789287481499.jpg", "media_1789286065178.jpg", "media_1789286065185.jpg", "media_1789287481503.jpg", "media_1789319983784.jpg"]',
                               'Chuẩn thẻ ATM (86x54mm)', 'Chất liệu PVC', 10, 'contact', 0, 1, 1
                        WHERE NOT EXISTS (SELECT 1 FROM products WHERE id = 'acc-1')"""
                    ),
                    (
                        "products",
                        None,
                        """INSERT INTO products (id, name, category, description, images_json, width, material, min_order, price_type, price, featured, visible)
                        SELECT 'acc-2', 'Vỏ đựng thẻ (Card holder) in theo yêu cầu', 'accessory',
                               'Vỏ đựng thẻ cứng cáp in full màu theo thiết kế riêng, bảo vệ thẻ khỏi trầy xước, cong vênh. Thiết kế sang trọng, có thể in logo nhận diện thương hiệu, nhận in từ 20 cái.',
                               '["media_1789317114085.jpg", "media_1789287073763.jpg", "media_1789286087649.jpg", "media_1789286087652.jpg", "media_1789286087760.jpg", "media_1789320043265.jpg"]',
                               'Vừa thẻ tiêu chuẩn (86x54mm)', 'Chất liệu nhựa ABS', 20, 'contact', 0, 1, 1
                        WHERE NOT EXISTS (SELECT 1 FROM products WHERE id = 'acc-2')"""
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
