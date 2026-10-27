-- ====================================================================
-- SismoWatch: Creación de Tablas, Índices y Relaciones
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. CAPA RAW (BRONCE)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.usgs_earthquakes_raw (
    id BIGSERIAL PRIMARY KEY,
    source_url VARCHAR(500) NOT NULL,
    payload_hash VARCHAR(64) UNIQUE NOT NULL,
    event_count INT NOT NULL DEFAULT 0,
    raw_payload JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_ingested_at ON raw.usgs_earthquakes_raw (ingested_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_payload_hash ON raw.usgs_earthquakes_raw (payload_hash);

-- --------------------------------------------------------------------
-- 2. CAPA STAGING (PLATA)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.earthquake_events_staging (
    id VARCHAR(64) PRIMARY KEY,
    mag NUMERIC(4, 2),
    place TEXT,
    time TIMESTAMPTZ NOT NULL,
    updated TIMESTAMPTZ,
    tz INT,
    url TEXT,
    detail TEXT,
    felt INT,
    cdi NUMERIC(4, 2),
    mmi NUMERIC(4, 2),
    alert VARCHAR(20),
    status VARCHAR(30),
    tsunami INT DEFAULT 0,
    sig INT,
    net VARCHAR(20),
    code VARCHAR(50),
    ids TEXT,
    sources TEXT,
    types TEXT,
    nst INT,
    dmin NUMERIC(8, 4),
    rms NUMERIC(6, 3),
    gap NUMERIC(6, 2),
    mag_type VARCHAR(20),
    type VARCHAR(50),
    title TEXT,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    depth_km DOUBLE PRECISION NOT NULL,
    raw_reference_id BIGINT REFERENCES raw.usgs_earthquakes_raw(id) ON DELETE SET NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_time ON staging.earthquake_events_staging (time DESC);
CREATE INDEX IF NOT EXISTS idx_staging_mag ON staging.earthquake_events_staging (mag DESC);

-- --------------------------------------------------------------------
-- 3. CAPA CURATED (ORO)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curated.earthquake_events (
    id VARCHAR(64) PRIMARY KEY,
    mag NUMERIC(4, 2) NOT NULL,
    place TEXT NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    updated TIMESTAMPTZ,
    tz INT,
    url TEXT,
    detail TEXT,
    felt INT,
    cdi NUMERIC(4, 2),
    mmi NUMERIC(4, 2),
    alert VARCHAR(20),
    status VARCHAR(30) NOT NULL,
    tsunami INT NOT NULL DEFAULT 0,
    sig INT,
    net VARCHAR(20),
    code VARCHAR(50),
    ids TEXT,
    sources TEXT,
    types TEXT,
    nst INT,
    dmin NUMERIC(8, 4),
    rms NUMERIC(6, 3),
    gap NUMERIC(6, 2),
    mag_type VARCHAR(20),
    type VARCHAR(50),
    title TEXT,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    depth_km DOUBLE PRECISION NOT NULL,
    is_updated BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_curated_time ON curated.earthquake_events (time DESC);
CREATE INDEX IF NOT EXISTS idx_curated_mag ON curated.earthquake_events (mag DESC);
CREATE INDEX IF NOT EXISTS idx_curated_coords ON curated.earthquake_events (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_curated_tsunami ON curated.earthquake_events (tsunami) WHERE tsunami = 1;

-- --------------------------------------------------------------------
-- 4. CALIDAD DE DATOS Y AUDITORÍA
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curated.data_quality_runs (
    id BIGSERIAL PRIMARY KEY,
    dag_run_id VARCHAR(120),
    rule_name VARCHAR(100) NOT NULL,
    records_evaluated INT NOT NULL DEFAULT 0,
    records_passed INT NOT NULL DEFAULT 0,
    records_failed INT NOT NULL DEFAULT 0,
    score_pct NUMERIC(5, 2) NOT NULL DEFAULT 100.0,
    status VARCHAR(20) NOT NULL, -- 'PASSED', 'WARNING', 'FAILED'
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_runs_at ON curated.data_quality_runs (executed_at DESC);

-- --------------------------------------------------------------------
-- 5. ANALÍTICA DE ANOMALÍAS
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curated.seismic_anomalies (
    id BIGSERIAL PRIMARY KEY,
    anomaly_type VARCHAR(50) NOT NULL, -- 'SEISMIC_SWARM', 'MAGNITUDE_OUTLIER', 'DEPTH_OUTLIER'
    region TEXT NOT NULL,
    event_count INT NOT NULL,
    mean_magnitude NUMERIC(4, 2) NOT NULL,
    max_magnitude NUMERIC(4, 2) NOT NULL,
    z_score NUMERIC(6, 2) NOT NULL,
    description TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomalies_at ON curated.seismic_anomalies (detected_at DESC);

-- --------------------------------------------------------------------
-- 6. REPORTES Y REGISTRO DE EJECUCIÓN DE IA
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curated.ai_executive_reports (
    id BIGSERIAL PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    summary_text TEXT NOT NULL,
    top_regions JSONB NOT NULL,
    metrics_snapshot JSONB NOT NULL,
    generated_by_model VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_date ON curated.ai_executive_reports (report_date DESC);

CREATE TABLE IF NOT EXISTS curated.ai_execution_logs (
    id BIGSERIAL PRIMARY KEY,
    report_id BIGINT REFERENCES curated.ai_executive_reports(id) ON DELETE SET NULL,
    model_name VARCHAR(100) NOT NULL,
    prompt_version VARCHAR(50) NOT NULL,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    latency_ms INT NOT NULL,
    estimated_cost_usd NUMERIC(8, 6) DEFAULT 0.0,
    status VARCHAR(30) NOT NULL, -- 'SUCCESS', 'FALLBACK_GENERATED', 'ERROR'
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_logs_at ON curated.ai_execution_logs (executed_at DESC);

-- --------------------------------------------------------------------
-- 7. USUARIOS DE PLATAFORMA (RBAC)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curated.users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(150),
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON curated.users (username);
