# SismoWatch — Documentación General del Sistema y Arquitectura Integral

## 1. Visión General del Proyecto
**SismoWatch** es una plataforma integral de **Ingeniería de Datos, Automatización con Inteligencia Artificial y Analítica Web en Tiempo Casi Real** diseñada para la ingesta continua, gobernanza, análisis y priorización de riesgos sísmicos a nivel mundial.

El sistema consume el catálogo oficial de eventos sísmicos del **USGS (United States Geological Survey)**, procesa y limpia los datos mediante una **Arquitectura Medallón (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)** con almacenamiento dual (Data Lakehouse S3 en MinIO y Base de Datos Relacional en PostgreSQL), valida rigurosamente los eventos a través de una **compuerta de calidad bloqueante (Pandera)** bajo una política de **Cero Cuarentena**, detecta anomalías estadísticas (Z-score) y genera informes ejecutivos y asistencia conversacional inteligente con modelos locales (**Ollama**).

---

## 2. Diagrama de la Arquitectura End-to-End

```
                           [ FUENTE EXTERNA: USGS EARTHQUAKE API ]
                           https://earthquake.usgs.gov/earthquakes/
                                              │
                                              ▼ (Cada 5 minutos)
                           ┌─────────────────────────────────────┐
                           │ Apache Airflow: dag_usgs_ingest_raw │
                           └──────────────────┬──────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        ┌─────────────────────────┐                       ┌─────────────────────────┐
        │  MINIO S3 DATA LAKE     │                       │     POSTGRESQL DB       │
        │      (Capa Bronze)      │                       │      (Capa Bronze)      │
        │ s3://sismowatch-lake/raw│                       │ raw.usgs_earthquakes_raw│
        │   (GeoJSON Inmutable)   │                       │    (Hash SHA-256)       │
        └────────────┬────────────┘                       └────────────┬────────────┘
                     │                                                 │
                     └────────────────────────┬────────────────────────┘
                                              │
                                              ▼ (Trigger Automático de Ingesta)
                           ┌─────────────────────────────────────┐
                           │Apache Airflow:dag_transform_and_qual│
                           └──────────────────┬──────────────────┘
                                              │
                                              ▼ (PySpark & Pandas)
                           ┌─────────────────────────────────────┐
                           │         POSTGRESQL DB: SILVER       │
                           │   staging.earthquake_events_staging │
                           └──────────────────┬──────────────────┘
                                              │
                                              ▼
                           ┌─────────────────────────────────────┐
                           │   COMPUERTA DE CALIDAD: PANDERA     │
                           │    (Validación Bloqueante 100%)     │
                           └──────────┬──────────────────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼ (Aprobados)                             ▼ (Rechazados)
   ┌───────────────────────────┐             ┌───────────────────────────┐
   │    POSTGRESQL DB: GOLD    │             │     DESCARTE DIRECTO      │
   │  curated.earthquake_events│             │ (Cero Cuarentena: Registro│
   │    (UPSERT Idempotente)   │             │en curated.data_quality_run│
   └─────────────┬─────────────┘             └───────────────────────────┘
                 │
                 ├─────────────────────────────────────────┐
                 ▼ (Diario a las 06:00 UTC)                ▼
   ┌───────────────────────────┐             ┌───────────────────────────┐
   │Airflow:dag_daily_ai_report│             │  BACKEND API (FASTAPI)    │
   │  (SQL + Z-Score + Ollama) │             │ (Rol DB: sismo_app SELECT)│
   └─────────────┬─────────────┘             │  JWT + RBAC + SSE Stream  │
                 │                           └─────────────┬─────────────┘
                 ▼                                         │
   ┌───────────────────────────┐                           │
   │curated.ai_executive_report│                           │
   └─────────────┬─────────────┘                           │
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                      ┌───────────────────────────────┐
                      │    PLATAFORMA WEB REACT       │
                      │(Dashboard, Mapa, Chatbot, OM) │
                      └───────────────────────────────┘
```

---

## 3. Las Capas de la Arquitectura Medallón

| Capa | Almacenamiento | Propósito y Naturaleza de los Datos | Herramienta Clave |
|---|---|---|---|
| **Bronze (Cruda)** | **MinIO S3** (`sismowatch-lake/raw/`) y **PostgreSQL** (`raw.usgs_earthquakes_raw`) | Ingesta inmutable de los GeoJSON originales. Cada evento posee un hash SHA-256 para evitar inserciones duplicadas. Preserva la verdad de origen. | Airflow + MinIO + Postgres |
| **Silver (Limpia)** | **PostgreSQL** (`staging.earthquake_events_staging`) | Datos aplanados y fuertemente tipados. Conversión de coordenadas, extracción de metadatos sismológicos y conversión de fechas a UTC estándar (`TIMESTAMPTZ`). | Pandas / PySpark |
| **Compuerta de Calidad** | En Memoria + **PostgreSQL** (`curated.data_quality_runs`) | Validación estadística y de rangos físicos obligatoria. **Cero Cuarentena:** Registros inválidos son descartados de inmediato y auditados en métricas de calidad. | Pandera |
| **Gold (Curada)** | **PostgreSQL** (`curated.earthquake_events` y `curated.ai_executive_reports`) | Verdad consolidada con claves de idempotencia (`UPSERT`). Consumo directo por la API para analítica, mapas, gráficos, reportes ejecutivos e IA. | PostgreSQL (Índices B-Tree) |
| **Consumo** | **FastAPI** + **React SPA** + **Ollama** | Exposición de servicios REST, streaming de eventos en tiempo real con Server-Sent Events (SSE), asistente conversacional y mapa global interactivo. | FastAPI + React + Ollama |

---

## 4. Cuadro Maestro de Tecnologías, Puertos y Credenciales

| Componente | Rol en el Sistema | URL / Puerto | Credenciales por Defecto |
|---|---|---|---|
| **Plataforma Web (Frontend)** | Dashboard interactivo, mapa Leaflet, reportes y linaje | [http://localhost:3000](http://localhost:3000) | - **Admin:** `admin` / `AdminSecurePass2026!`<br/>- **Viewer:** `viewer` / `ViewerSecurePass2026!` |
| **Backend API (FastAPI)** | API REST gobernada, SSE y Chatbot | [http://localhost:8000](http://localhost:8000)<br/>Swagger: `/docs` | Autenticación JWT (`/auth/login`) |
| **Apache Airflow** | Orquestación de DAGs (LocalExecutor) | [http://localhost:8080](http://localhost:8080) | `sismo_admin` / `airflow_secure_admin_2026` |
| **MinIO S3 Object Storage** | Data Lakehouse Bronze inmutable | Consola: [http://localhost:9001](http://localhost:9001)<br/>API: `http://localhost:9000` | `minio_admin` / `minio_secret_pass_2026` |
| **PostgreSQL 16** | Base de datos relacional Medallón | `localhost:5432` (BD: `sismowatch`) | - Superuser: `postgres` / `postgres_secure_pass_2026`<br/>- Ingesta: `sismo_ingest`<br/>- ETL: `sismo_etl`<br/>- App: `sismo_app` |
| **Ollama** | Motor de LLM local (Reportes y Chatbot) | `http://localhost:11434` (o `11435`) | N/A (Servicio local) |
| **OpenMetadata Stack** | Catálogo de metadatos y linaje corporativo | [http://localhost:8585](http://localhost:8585) | `admin` / `admin` |

---

## 5. Decisiones Clave de Ingeniería y Buenas Prácticas

1. **Principio de Mínimo Privilegio (Least Privilege RBAC):**
   - La API nunca se conecta con el superusuario `postgres`. Utiliza `sismo_app`, que tiene permisos de solo lectura (`SELECT`). Si la API sufriese una vulnerabilidad, es imposible que se borren o alteren registros de la base de datos.
2. **Cero Cuarentena:**
   - Se descartó la creación de tablas de cuarentena para evitar la acumulación de datos zombi. Los registros corruptos se rechazan antes de llegar a la capa Gold y se auditan detalladamente en `data_quality_runs`.
3. **Idempotencia Garantizada:**
   - La ingesta calcula hashes **SHA-256** para evitar eventos repetidos en Bronze.
   - La inserción en Gold utiliza la sintaxis `ON CONFLICT (id) DO UPDATE...` para actualizar magnitudes o coordenadas revisadas por el USGS sin generar duplicados.
4. **Resiliencia de Inteligencia Artificial (Guardrails + Fallback):**
   - El modelo de lenguaje nunca inventa números: los cálculos estadísticos y Z-Scores se generan en SQL determinista. Si Ollama estuviese apagado o saturado en CPU, el sistema activa automáticamente un fallback de redacción determinista sin detener el pipeline.
5. **Enrutador Ultrarrápido de Chatbot (< 10 ms):**
   - Para evitar bloqueos de CPU al conversar con el asistente, un enrutador de intenciones responde en milisegundos a preguntas frecuentes y explicaciones teóricas, reservando la inferencia de lenguaje para consultas de razonamiento abierto con tokens acotados (`num_predict: 50`).

---

## 6. Índice de Documentación por Tecnología

Para profundizar en cada componente específico, consulte sus manuales técnicos dedicados:
- 👉 [01. MinIO Object Storage (S3 Lakehouse)](tecnologias/01_MINIO.md)
- 👉 [02. Apache Airflow (Orquestación de DAGs)](tecnologias/02_AIRFLOW.md)
- 👉 [03. PostgreSQL (Esquemas, Tablas y Roles RBAC)](tecnologias/03_POSTGRESQL.md)
- 👉 [04. FastAPI Backend (Endpoints, Seguridad y SSE)](tecnologias/04_FASTAPI.md)
- 👉 [05. Plataforma Web React (Dashboard, Mapas y Chatbot)](tecnologias/05_REACT_FRONTEND.md)
- 👉 [06. Pandera y Calidad de Datos (Reglas y Cero Cuarentena)](tecnologias/06_PANDERA_CALIDAD.md)
- 👉 [07. Ollama e Inteligencia Artificial (Reportes y Chatbot)](tecnologias/07_OLLAMA_IA.md)
- 👉 [08. OpenMetadata y Linaje de Datos (Catálogo y Persistencia)](tecnologias/08_OPENMETADATA_LINAJE.md)
- 👉 [Guía de Instalación y Despliegue en una Nueva Máquina](01_GUIA_INSTALACION_DESDE_CERO.md)
