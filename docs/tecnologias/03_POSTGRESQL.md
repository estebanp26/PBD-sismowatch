# PostgreSQL — Documentación de Base de Datos y Modelo Medallón

## 1. ¿Qué es PostgreSQL y qué rol cumple en SismoWatch?
**PostgreSQL 16** es el sistema de gestión de bases de datos relacional y transaccional principal de **SismoWatch**.

En este proyecto, PostgreSQL alberga la implementación formal de la **Arquitectura Medallón (Medallion Architecture)** organizada en esquemas lógicos independientes (`raw`, `staging` y `curated`), garantizando la segregación de responsabilidades, integridad de datos, rendimiento analítico y seguridad mediante el **principio de mínimo privilegio (RBAC)**.

---

## 2. Parámetros de Conexión y Modelo de Roles (RBAC)

PostgreSQL está expuesto en el puerto **`5432`** y cuenta con cuatro usuarios especializados con privilegios estrictamente acotados:

| Rol / Usuario | Contraseña por Defecto | Permisos y Propósito |
|---|---|---|
| **`postgres`** (Superuser) | `postgres_secure_pass_2026` | Administración de la instancia, creación de esquemas, extensiones y usuarios iniciales. |
| **`sismo_ingest`** | `ingest_secret_pass_2026` | **Solo Capa Cruda:** Permisos de `INSERT` y `SELECT` exclusivamente sobre el esquema `raw`. No tiene acceso a staging ni a curated. |
| **`sismo_etl`** | `etl_secret_pass_2026` | **Pipeline de Transformación:** Lee `raw`, lee/escribe en `staging`, e inserta/actualiza (`UPSERT`) en `curated` y registros de calidad. |
| **`sismo_app`** | `app_readonly_pass_2026` | **Plataforma Web y FastAPI:** Rol de **SOLO LECTURA** (`SELECT`) sobre `curated` y `staging`, y lectura de conteos en `raw` para linaje. Nunca puede modificar ni borrar datos. |

---

## 3. Arquitectura de Esquemas y Tablas

```
┌─────────────────────────────────────────────────────────────┐
│                       BASE DE DATOS                         │
│                        "sismowatch"                         │
└─────────────────────────────────────────────────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
   ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
   │ Esquema: raw  │       │Esquema:staging│       │Esquema:curated│
   │ (Capa Bronze) │       │ (Capa Silver) │       │  (Capa Gold)  │
   └───────────────┘       └───────────────┘       └───────────────┘
```

### 3.1 Esquema `raw` (Capa Bronze)
Almacena el payload JSON completo tal y como proviene de la API externa para garantizar inmutabilidad e idempotencia en la base de datos relacional.
- **Tabla:** `raw.usgs_earthquakes_raw`
  - `id` (VARCHAR(50) PRIMARY KEY): Identificador oficial asignado por el USGS.
  - `sha256_hash` (CHAR(64) UNIQUE): Hash criptográfico calculado sobre el evento para evitar inserciones repetidas.
  - `raw_payload` (JSONB): Contenido GeoJSON original íntegro.
  - `ingested_at` (TIMESTAMPTZ): Fecha y hora exacta de captura.

### 3.2 Esquema `staging` (Capa Silver)
Capa intermedia donde los datos han sido aplanados, fuertemente tipados y normalizados a estándares universales.
- **Tabla:** `staging.earthquake_events_staging`
  - Campos normalizados: `id`, `magnitude`, `place`, `time` (TIMESTAMPTZ UTC), `updated` (TIMESTAMPTZ UTC), `tz`, `url`, `detail`, `felt`, `cdi`, `mmi`, `alert`, `status`, `tsunami` (BOOLEAN), `sig`, `net`, `code`, `ids`, `sources`, `types`, `nst`, `dmin`, `rms`, `gap`, `mag_type`, `type`, `title`.
  - Coordenadas geográficas descompuestas: `longitude` (DECIMAL), `latitude` (DECIMAL), `depth` (DECIMAL).

### 3.3 Esquema `curated` (Capa Gold)
Es la verdad consolidada y optimizada para el consumo de analítica, el dashboard web, el asistente de IA y la generación de reportes.
- **Tabla:** `curated.earthquake_events`
  - Contiene el catálogo final consolidado de eventos sísmicos limpios y verificados por la compuerta de calidad.
  - **Estrategia de Idempotencia:** `UPSERT` basado en `id`. Si un sismo ya existe pero el USGS actualiza su magnitud o profundidad, se actualiza el registro sin generar duplicados.
  - **Índices de Alto Rendimiento:**
    - `idx_curated_time` en `(time DESC)`: Permite búsquedas instantáneas de eventos recientes.
    - `idx_curated_magnitude` en `(magnitude DESC)`: Optimiza filtros de intensidad.
    - `idx_curated_geo` en `(latitude, longitude)`: Búsquedas espaciales y mapas.
    - `idx_curated_tsunami` en `(tsunami)`: Filtro prioritario de emergencias.
- **Tabla:** `curated.data_quality_runs`
  - Auditoría de cada ejecución de validación con Pandera: fecha, total procesado, total aceptado, total rechazado y detalle de motivos de fallo.
- **Tabla:** `curated.ai_executive_reports`
  - Informes diarios redactados por IA con resumen ejecutivo, zonas críticas, métricas agregadas y anomalías detectadas.
- **Tabla:** `curated.users`
  - Gestión de usuarios y credenciales para el acceso al sistema con contraseñas encriptadas mediante **bcrypt** y roles `admin` y `viewer`.

---

## 4. Política de "Cero Cuarentena"

Por decisión de diseño de alto rendimiento y conforme a los requerimientos del proyecto:
- **No existe tabla de cuarentena:** Los eventos que no cumplen las reglas de calidad (ej. latitudes fuera de $[-90, 90]$ o magnitudes físicamente imposibles) son **descartados de inmediato** antes de ingresar a la capa `curated`.
- **Auditoría transparente:** Cada descarte queda registrado con su causa estadística en la tabla `curated.data_quality_runs`, evitando que la base de datos almacene basura o datos contaminados.

---

## 5. Persistencia y Volúmenes en Docker Desktop

Los datos de PostgreSQL se conservan permanentemente en el volumen:
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```
- **Volumen:** `postgres_data`
- Al reiniciar o actualizar la aplicación, no se pierden tablas, usuarios ni datos acumulados.

---

## 6. Comandos Operativos y Consultas Útiles

```bash
# 1. Conectarse a PostgreSQL como administrador
docker exec -it sismowatch_postgres psql -U postgres -d sismowatch

# 2. Consultar el total de registros en cada capa Medallón
SELECT 
    (SELECT COUNT(*) FROM raw.usgs_earthquakes_raw) AS total_raw,
    (SELECT COUNT(*) FROM staging.earthquake_events_staging) AS total_staging,
    (SELECT COUNT(*) FROM curated.earthquake_events) AS total_curated,
    (SELECT COUNT(*) FROM curated.data_quality_runs) AS ejecuciones_calidad,
    (SELECT COUNT(*) FROM curated.ai_executive_reports) AS reportes_ia;

# 3. Consultar los 5 sismos más potentes registrados en Gold
SELECT place, magnitude, depth, time 
FROM curated.earthquake_events 
ORDER BY magnitude DESC 
LIMIT 5;

# 4. Generar un backup completo de la base de datos
docker exec sismowatch_postgres pg_dump -U postgres sismowatch > backup_sismowatch.sql
```
