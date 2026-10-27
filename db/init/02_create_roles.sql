-- ====================================================================
-- SismoWatch: Modelo de Mínimo Privilegio (RBAC en Base de Datos)
-- ====================================================================

-- 1. Rol de Ingesta: Únicamente escribe en el schema 'raw'
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sismo_ingest') THEN
        CREATE ROLE sismo_ingest WITH LOGIN PASSWORD 'ingest_secret_pass_2026';
    END IF;
END $$;

GRANT USAGE ON SCHEMA raw TO sismo_ingest;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA raw TO sismo_ingest;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA raw TO sismo_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT, INSERT, UPDATE ON TABLES TO sismo_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT USAGE, SELECT ON SEQUENCES TO sismo_ingest;

-- 2. Rol ETL/Transformación: Lee raw, opera staging, inserta en curated y métricas de calidad
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sismo_etl') THEN
        CREATE ROLE sismo_etl WITH LOGIN PASSWORD 'etl_secret_pass_2026';
    END IF;
END $$;

GRANT USAGE ON SCHEMA raw TO sismo_etl;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO sismo_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA raw GRANT SELECT ON TABLES TO sismo_etl;

GRANT USAGE ON SCHEMA staging TO sismo_etl;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA staging TO sismo_etl;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA staging TO sismo_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging GRANT ALL ON TABLES TO sismo_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging GRANT ALL ON SEQUENCES TO sismo_etl;

GRANT USAGE ON SCHEMA curated TO sismo_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA curated TO sismo_etl;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA curated TO sismo_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA curated GRANT ALL ON TABLES TO sismo_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA curated GRANT ALL ON SEQUENCES TO sismo_etl;

-- 3. Rol de Aplicación (Plataforma Web / FastAPI): SOLO LECTURA en Curated (y sesión si aplica)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sismo_app') THEN
        CREATE ROLE sismo_app WITH LOGIN PASSWORD 'app_readonly_pass_2026';
    END IF;
END $$;

GRANT USAGE ON SCHEMA curated TO sismo_app;
GRANT SELECT ON ALL TABLES IN SCHEMA curated TO sismo_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA curated TO sismo_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT SELECT ON TABLES TO sismo_app;

GRANT USAGE ON SCHEMA staging TO sismo_app;
GRANT SELECT ON ALL TABLES IN SCHEMA staging TO sismo_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT ON TABLES TO sismo_app;

GRANT USAGE ON SCHEMA raw TO sismo_app;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO sismo_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO sismo_app;

-- Revocar accesos por defecto a public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
