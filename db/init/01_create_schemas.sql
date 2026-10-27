-- ====================================================================
-- SismoWatch: Inicialización de Esquemas Arquitectura Medallón
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;

COMMENT ON SCHEMA raw IS 'Capa Bronce: Cargas crudas tal como llegan de la API USGS (JSONB inmutable)';
COMMENT ON SCHEMA staging IS 'Capa Plata: Datos aplanados, tipados y estructurados previos a control de calidad';
COMMENT ON SCHEMA curated IS 'Capa Oro: Datos validados, deduplicados, auditorías de calidad, reportes y métricas analíticas';
