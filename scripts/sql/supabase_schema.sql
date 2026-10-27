-- TAGLUXE: additive schema only. No DROP, DELETE or TRUNCATE.

BEGIN;


CREATE TABLE IF NOT EXISTS accessories (
	id VARCHAR(50) NOT NULL,
	name VARCHAR(255) NOT NULL,
	category VARCHAR(50) NOT NULL,
	price INTEGER NOT NULL,
	image VARCHAR(255),
	description TEXT,
	title VARCHAR(255),
	sort_order INTEGER,
	visible BOOLEAN,
	min_quantity INTEGER NOT NULL,
	PRIMARY KEY (id)
)

;

ALTER TABLE public.accessories ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS audit_logs (
	id SERIAL NOT NULL,
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	admin_user VARCHAR(80) NOT NULL,
	action VARCHAR(80) NOT NULL,
	target_type VARCHAR(50) NOT NULL,
	target_id VARCHAR(80) NOT NULL,
	details TEXT,
	ip_address VARCHAR(50),
	PRIMARY KEY (id)
)

;

CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs (timestamp);

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS demo_requests (
	id VARCHAR(32) NOT NULL,
	created_at VARCHAR(50) NOT NULL,
	created_at_dt TIMESTAMP WITHOUT TIME ZONE,
	phone VARCHAR(20) NOT NULL,
	customer_name VARCHAR(120),
	product_category VARCHAR(50) NOT NULL,
	quantity_range VARCHAR(50) NOT NULL,
	notes TEXT,
	file_path VARCHAR(255),
	original_filename VARCHAR(255),
	status VARCHAR(50) NOT NULL,
	sync_status VARCHAR(20) NOT NULL,
	sync_error TEXT,
	retry_count INTEGER NOT NULL,
	idempotency_key VARCHAR(64),
	PRIMARY KEY (id)
)

;

CREATE INDEX IF NOT EXISTS ix_demo_requests_created_at_dt ON demo_requests (created_at_dt);

CREATE UNIQUE INDEX IF NOT EXISTS ix_demo_requests_idempotency_key ON demo_requests (idempotency_key);

ALTER TABLE public.demo_requests ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS idempotency_records (
	key VARCHAR(64) NOT NULL,
	request_id VARCHAR(64),
	content_hash VARCHAR(64),
	created_at TIMESTAMP WITHOUT TIME ZONE,
	status VARCHAR(20) NOT NULL,
	response_json TEXT,
	PRIMARY KEY (key)
)

;

CREATE INDEX IF NOT EXISTS ix_idempotency_records_created_at ON idempotency_records (created_at);

CREATE INDEX IF NOT EXISTS ix_idempotency_records_request_id ON idempotency_records (request_id);

ALTER TABLE public.idempotency_records ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS price_tiers (
	id SERIAL NOT NULL,
	category VARCHAR(50) NOT NULL,
	min_qty INTEGER NOT NULL,
	max_qty INTEGER NOT NULL,
	unit_price INTEGER NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE INDEX IF NOT EXISTS ix_price_tiers_category ON price_tiers (category);

ALTER TABLE public.price_tiers ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS products (
	id VARCHAR(50) NOT NULL,
	name VARCHAR(255) NOT NULL,
	category VARCHAR(50) NOT NULL,
	description TEXT,
	images_json TEXT,
	width VARCHAR(100),
	material VARCHAR(100),
	min_order INTEGER,
	price_type VARCHAR(50),
	price INTEGER,
	featured BOOLEAN,
	visible BOOLEAN,
	badge VARCHAR(255),
	specs_json TEXT,
	PRIMARY KEY (id)
)

;

ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS quotes (
	id VARCHAR(32) NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	customer_name VARCHAR(120) NOT NULL,
	phone VARCHAR(20) NOT NULL,
	category VARCHAR(80) NOT NULL,
	quantity INTEGER NOT NULL,
	specs VARCHAR(255),
	accessories TEXT,
	unit_price INTEGER NOT NULL,
	total_price INTEGER NOT NULL,
	notes TEXT,
	status VARCHAR(50) NOT NULL,
	include_vat BOOLEAN,
	vat_amount INTEGER,
	punched_hole VARCHAR(20),
	sync_status VARCHAR(20) NOT NULL,
	sync_error TEXT,
	retry_count INTEGER NOT NULL,
	idempotency_key VARCHAR(64),
	PRIMARY KEY (id)
)

;

CREATE UNIQUE INDEX IF NOT EXISTS ix_quotes_idempotency_key ON quotes (idempotency_key);

CREATE INDEX IF NOT EXISTS ix_quotes_phone ON quotes (phone);

ALTER TABLE public.quotes ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS schema_migrations (
	version VARCHAR(50) NOT NULL,
	applied_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (version)
)

;

ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS site_settings (
	key VARCHAR(80) NOT NULL,
	value_json TEXT NOT NULL,
	PRIMARY KEY (key)
)

;

ALTER TABLE public.site_settings ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS sync_tasks (
	id SERIAL NOT NULL,
	event_key VARCHAR(64) NOT NULL,
	record_type VARCHAR(20) NOT NULL,
	record_id VARCHAR(50) NOT NULL,
	payload TEXT NOT NULL,
	status VARCHAR(20) NOT NULL,
	attempt_count INTEGER NOT NULL,
	next_retry_at TIMESTAMP WITHOUT TIME ZONE,
	last_error TEXT,
	lease_until TIMESTAMP WITHOUT TIME ZONE,
	worker_id VARCHAR(64),
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE UNIQUE INDEX IF NOT EXISTS ix_sync_tasks_event_key ON sync_tasks (event_key);

CREATE INDEX IF NOT EXISTS ix_sync_tasks_lease_until ON sync_tasks (lease_until);

CREATE INDEX IF NOT EXISTS ix_sync_tasks_next_retry_at ON sync_tasks (next_retry_at);

CREATE INDEX IF NOT EXISTS ix_sync_tasks_record_id ON sync_tasks (record_id);

CREATE INDEX IF NOT EXISTS ix_sync_tasks_status ON sync_tasks (status);

ALTER TABLE public.sync_tasks ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS quote_admin_states (
	quote_id VARCHAR(32) NOT NULL,
	internal_notes TEXT NOT NULL,
	owner VARCHAR(80) NOT NULL,
	priority VARCHAR(20) NOT NULL,
	follow_up_on DATE,
	version INTEGER NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_by VARCHAR(80) NOT NULL,
	PRIMARY KEY (quote_id),
	FOREIGN KEY(quote_id) REFERENCES quotes (id) ON DELETE CASCADE
)

;

CREATE INDEX IF NOT EXISTS ix_quote_admin_states_follow_up_on ON quote_admin_states (follow_up_on);

CREATE INDEX IF NOT EXISTS ix_quote_admin_states_priority ON quote_admin_states (priority);

ALTER TABLE public.quote_admin_states ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS admin_users (
	id SERIAL NOT NULL,
	username VARCHAR(50) NOT NULL,
	display_name VARCHAR(100) NOT NULL,
	email VARCHAR(254) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	role VARCHAR(20) NOT NULL,
	active BOOLEAN NOT NULL,
	receive_notifications BOOLEAN NOT NULL,
	auth_epoch VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (username)
)

;
ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS quote_deletions (
	quote_id VARCHAR(32) NOT NULL,
	deleted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	deleted_by VARCHAR(80) NOT NULL,
	PRIMARY KEY (quote_id)
)

;
ALTER TABLE public.quote_deletions ENABLE ROW LEVEL SECURITY;

COMMIT;
