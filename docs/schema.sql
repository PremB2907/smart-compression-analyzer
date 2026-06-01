-- SecureArchive AI — PostgreSQL schema (also created via SQLAlchemy metadata)

CREATE TYPE user_role AS ENUM ('admin', 'researcher', 'viewer');
CREATE TYPE upload_status AS ENUM ('pending', 'processing', 'completed', 'failed');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role user_role DEFAULT 'researcher',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE uploads (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    user_id INTEGER REFERENCES users(id) NOT NULL,
    original_filename VARCHAR(512) NOT NULL,
    storage_key VARCHAR(1024) NOT NULL,
    mime_type VARCHAR(128),
    size_bytes INTEGER NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    status upload_status DEFAULT 'pending',
    celery_task_id VARCHAR(64),
    error_message VARCHAR(2048),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER UNIQUE REFERENCES uploads(id),
    reference_storage_key VARCHAR(1024) NOT NULL,
    width INTEGER DEFAULT 1000,
    height INTEGER DEFAULT 1414,
    ground_truth_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE stego_payloads (
    id SERIAL PRIMARY KEY,
    image_id INTEGER UNIQUE REFERENCES images(id),
    uuid VARCHAR(32) NOT NULL,
    timestamp VARCHAR(25) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    payload_bits INTEGER DEFAULT 968,
    embedding_psnr FLOAT,
    stego_storage_key VARCHAR(1024) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE compression_runs (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER REFERENCES uploads(id),
    format VARCHAR(32) NOT NULL,
    compressed_storage_key VARCHAR(1024) NOT NULL,
    reconstructed_storage_key VARCHAR(1024),
    encode_time_ms FLOAT,
    decode_time_ms FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    compression_run_id INTEGER UNIQUE REFERENCES compression_runs(id),
    file_size_bytes INTEGER,
    compression_ratio FLOAT,
    mse FLOAT,
    psnr FLOAT,
    ssim FLOAT,
    ocr_accuracy FLOAT,
    cer FLOAT,
    ber FLOAT,
    payload_recovery_pct FLOAT,
    throughput_mbps FLOAT,
    embedding_psnr FLOAT
);

CREATE TABLE ocr_results (
    id SERIAL PRIMARY KEY,
    compression_run_id INTEGER UNIQUE REFERENCES compression_runs(id),
    reference_text TEXT,
    recovered_text TEXT,
    diff_json TEXT,
    confidence_avg FLOAT
);

CREATE TABLE recovered_payloads (
    id SERIAL PRIMARY KEY,
    compression_run_id INTEGER UNIQUE REFERENCES compression_runs(id),
    recovered_uuid VARCHAR(32),
    recovered_timestamp VARCHAR(25),
    recovered_checksum VARCHAR(64),
    recovery_pct FLOAT,
    ber FLOAT,
    corrupted_bits INTEGER,
    bit_damage_json TEXT
);

CREATE TABLE benchmarks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255),
    dataset_path VARCHAR(1024),
    results_json TEXT,
    tables_json TEXT,
    status VARCHAR(32) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id INTEGER,
    ip_address VARCHAR(45),
    details TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
