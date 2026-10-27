-- ====================================================================
-- SismoWatch: Semilla de Datos Inicial (Usuarios y Eventos Base)
-- ====================================================================

-- 1. Usuarios del Sistema (Admin y Viewer)
INSERT INTO curated.users (username, hashed_password, full_name, role, is_active)
VALUES
    ('admin', '$2b$12$YbXl2Vjeft5ROWS0DonkQO09WdPuIwdFrahlvrcX5i5cJYNOv7Fle', 'Administrador SismoWatch', 'admin', TRUE),
    ('viewer', '$2b$12$szQFfpvstw4M16UNH6ecJ.CmS3BLUQrV2hU0w6pH6fQnuUtKCetPK', 'Operador de Riesgo', 'viewer', TRUE)
ON CONFLICT (username) DO NOTHING;

-- 2. Eventos Sísmicos Iniciales de Referencia (Validados y Georreferenciados)
INSERT INTO curated.earthquake_events (
    id, mag, place, time, updated, tz, url, status, tsunami, sig, mag_type, type, title, longitude, latitude, depth_km, is_updated
)
VALUES
    ('us7000m1a1', 6.8, '125 km ENE of Sendai, Japan', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour', 0, 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000m1a1', 'reviewed', 1, 750, 'mww', 'earthquake', 'M 6.8 - 125 km ENE of Sendai, Japan', 142.15, 38.35, 35.4, FALSE),
    ('us7000m1a2', 5.4, '45 km SW of Ovalle, Chile', NOW() - INTERVAL '4 hours', NOW() - INTERVAL '3 hours', 0, 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000m1a2', 'reviewed', 0, 480, 'mww', 'earthquake', 'M 5.4 - 45 km SW of Ovalle, Chile', -71.50, -30.85, 48.2, FALSE),
    ('us7000m1a3', 4.7, 'Southern California, USA', NOW() - INTERVAL '6 hours', NOW() - INTERVAL '5 hours', 0, 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000m1a3', 'automatic', 0, 320, 'ml', 'earthquake', 'M 4.7 - Southern California, USA', -116.45, 33.72, 12.1, FALSE),
    ('us7000m1a4', 3.2, 'Northern Italy', NOW() - INTERVAL '8 hours', NOW() - INTERVAL '7 hours', 0, 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000m1a4', 'reviewed', 0, 160, 'md', 'earthquake', 'M 3.2 - Northern Italy', 11.25, 44.15, 8.5, FALSE),
    ('us7000m1a5', 5.9, 'South Sandwich Islands region', NOW() - INTERVAL '10 hours', NOW() - INTERVAL '9 hours', 0, 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000m1a5', 'reviewed', 0, 560, 'mwb', 'earthquake', 'M 5.9 - South Sandwich Islands region', -26.85, -58.45, 115.0, FALSE),
    ('us7000m1a6', 4.1, 'Off the coast of Oaxaca, Mexico', NOW() - INTERVAL '12 hours', NOW() - INTERVAL '11 hours', 0, 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000m1a6', 'automatic', 0, 240, 'mb', 'earthquake', 'M 4.1 - Off the coast of Oaxaca, Mexico', -97.10, 15.65, 22.0, FALSE)
ON CONFLICT (id) DO NOTHING;

-- 3. Métricas de Calidad de Datos Iniciales
INSERT INTO curated.data_quality_runs (dag_run_id, rule_name, records_evaluated, records_passed, records_failed, score_pct, status)
VALUES
    ('init_run_bootstrap', 'Esquema y Tipos de Datos (Pandera)', 6, 6, 0, 100.0, 'PASSED'),
    ('init_run_bootstrap', 'Rangos Geográficos Coordenadas [-90/90, -180/180]', 6, 6, 0, 100.0, 'PASSED'),
    ('init_run_bootstrap', 'Rangos Físicos Plausibles (Mag & Depth)', 6, 6, 0, 100.0, 'PASSED'),
    ('init_run_bootstrap', 'Unicidad de ID e Idempotencia', 6, 6, 0, 100.0, 'PASSED'),
    ('init_run_bootstrap', 'Control de Frescura (Freshness < 30m)', 6, 6, 0, 100.0, 'PASSED');

-- 4. Reporte Ejecutivo con IA Inicial de Referencia
INSERT INTO curated.ai_executive_reports (report_date, title, summary_text, top_regions, metrics_snapshot, generated_by_model)
VALUES
    (CURRENT_DATE, 'Reporte Ejecutivo Global de Actividad Sísmica', 
     'Durante las últimas 24 horas se registraron 6 eventos sísmicos significativos a nivel global. El evento de mayor magnitud correspondió a un sismo M 6.8 a 125 km ENE de Sendai, Japón, el cual generó una alerta preventiva de tsunami y requirió atención prioritaria de gestión de riesgos. La magnitud promedio calculada fue de 5.02, con una profundidad media de 40.2 km. La actividad telúrica en el Cinturón de Fuego del Pacífico (Japón, Chile, México y California) concentró el 83.3% de los sismos monitoreados.',
     '[{"region": "Japan", "count": 1, "max_mag": 6.8}, {"region": "Chile", "count": 1, "max_mag": 5.4}, {"region": "South Sandwich Islands", "count": 1, "max_mag": 5.9}, {"region": "USA", "count": 1, "max_mag": 4.7}]',
     '{"total_events": 6, "max_magnitude": 6.8, "avg_magnitude": 5.02, "tsunami_alerts": 1, "avg_depth_km": 40.2, "quality_score": 100.0}',
     'qwen2.5')
ON CONFLICT (report_date) DO NOTHING;

-- 5. Registro de Ejecución de IA Inicial
INSERT INTO curated.ai_execution_logs (report_id, model_name, prompt_version, prompt_tokens, completion_tokens, total_tokens, latency_ms, estimated_cost_usd, status)
VALUES
    (1, 'qwen2.5', 'v1.0.0', 380, 142, 522, 1250, 0.000000, 'SUCCESS');
