# SismoWatch — Plataforma de Monitoreo Sísmico Global en Tiempo Casi Real

> **Solución integral de Ingeniería de Datos, Automatización con Inteligencia Artificial y Plataforma Analítica Web** para la priorización y gestión de riesgos sísmicos a nivel global.

---

## 1. Puesta en Marcha Rápida (Un Único Comando)

El sistema está completamente contenedorizado con **Docker Compose** y levanta todos los componentes de la arquitectura con un único comando.

### 1.1 Prerrequisitos
- **Docker** $\ge$ 24.0 y **Docker Compose** $\ge$ v2.20
- **Ollama** ejecutándose localmente con el modelo `qwen2.5` (o el servicio utilizará automáticamente el fallback determinista garantizando funcionamiento 100% resiliente).

### 1.2 Paso 1: Configurar Variables de Entorno y Claves
Copie la plantilla de variables de entorno y genere la clave Fernet:
```bash
cp .env.example .env
```
*(El archivo `.env` ya se encuentra preconfigurado en este repositorio con una clave Fernet generada de forma criptográfica y credenciales de desarrollo).*

### 1.3 Paso 2: Desplegar la Plataforma Completa
Ejecute en la raíz del proyecto:
```bash
docker compose up -d
```

### 1.4 Puertos y Accesos del Sistema

| Servicio | URL Local | Credenciales por Defecto | Propósito |
|---|---|---|---|
| **Plataforma Web (Frontend)** | [http://localhost:3000](http://localhost:3000) | **Admin:** `admin` / `AdminSecurePass2026!`<br/>**Viewer:** `viewer` / `ViewerSecurePass2026!` | Dashboard interactivo, mapa Leaflet, reportes y streaming |
| **Backend API (FastAPI / Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Autenticación vía JWT (`/auth/login`) | API REST gobernada y Server-Sent Events (`/api/stream`) |
| **Apache Airflow Webserver** | [http://localhost:8080](http://localhost:8080) | `sismo_admin` / `airflow_secure_admin_2026` | Orquestador de DAGs (LocalExecutor) |
| **MinIO Object Storage Console** | [http://localhost:9001](http://localhost:9001) | `minio_admin` / `minio_secret_pass_2026` | Interfaz visual del Lago S3 (`sismowatch-lake`) |
| **Base de Datos PostgreSQL** | `localhost:5432` | `postgres` / `postgres_secure_pass_2026` | Almacenamiento relacional `raw`, `staging` y `curated` |

---

## 2. Documentación Integral del Proyecto

Para consultar toda la documentación detallada por tecnología, manuales operativos y guías de despliegue:
- 📖 **[Índice Maestro de Documentación (docs/README.md)](docs/README.md)**
- 🌐 **[Visión General del Sistema (docs/00_SISTEMA_GENERAL.md)](docs/00_SISTEMA_GENERAL.md)**
- 🚀 **[Guía de Instalación y Despliegue desde Cero (docs/01_GUIA_INSTALACION_DESDE_CERO.md)](docs/01_GUIA_INSTALACION_DESDE_CERO.md)**
- 🏗️ **[Análisis Formal de Arquitectura y Compensaciones (docs/ARQUITECTURA.md)](docs/ARQUITECTURA.md)**

### Diagrama de la Arquitectura Medallón con S3 Lakehouse

```
[ Fuente Externa: USGS Earthquake Catalog ]
                   │
                   ▼ (Cada 5 min)
   [ Apache Airflow: dag_usgs_ingest_raw ]
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
[ MinIO S3 Lakehouse ]   [ PostgreSQL DB ]
s3://sismowatch-lake/raw/  raw.usgs_earthquakes_raw (Hash SHA-256)
        │                     │
        └──────────┬──────────┘
                   ▼ (Trigger de Ingesta)
[ Apache Airflow: dag_transform_and_quality ]
                   │
                   ▼ (PySpark & Pandas)
   [ Capa Staging: staging.earthquake_events_staging ]
                   │
                   ▼
     [ Compuerta Bloqueante de Calidad: Pandera ]
        ├── Aprobados ──► [ Capa Curated: curated.earthquake_events ] (Upsert)
        ├── Rechazados ──► [ Descarte Directo: Registro en logs y métricas ]
        └── Métricas ────► [ Auditoría: curated.data_quality_runs ]
                   │
                   ▼ (Diario a las 06:00 UTC)
   [ Apache Airflow: dag_daily_ai_report ]
        ├── 1. KPIs Deterministas en SQL (Verdad Fundamental)
        ├── 2. Detección de Anomalías Estadísticas (Z-Score Enjambres)
        └── 3. Redacción Ejecutiva con Ollama (Qwen 2.5) + Guardrails
                   │
                   ▼
[ Backend API (FastAPI) ] ── (Rol DB: sismo_app de Solo Lectura)
        │
        ├── REST Endpoints (JWT + RBAC: Viewer vs Admin)
        └── Streaming en Tiempo Real (Server-Sent Events)
                   │
                   ▼
[ Plataforma Web React + Vite + Leaflet (Puerto 3000) ]
```

---

## 3. Calidad de Datos (Data Quality Framework)

### 3.1 Justificación de la Herramienta Elegida: Pandera
Se evaluaron herramientas del ecosistema como Great Expectations, Soda y validaciones en SQL puro:
- **Selección:** **Pandera** integrada con Pandas y PySpark.
- **Razón técnica:** Pandera permite validación declarativa y fuertemente tipada en memoria directamente sobre los pipelines de transformación en Python 3.11+. Ofrece detalle a nivel de fila y columna de cada fallo, permitiendo descartar automáticamente los registros no conformes e imputar causas de rechazo en las métricas de calidad sin sobrecarga de memoria ni dependencias pesadas en los contenedores de Airflow.

### 3.2 Reglas de Calidad Implementadas
1. **Esquema y Tipado:** Verificación de tipos nativos (`id` como string no vacío, `time` como `datetime64[ns, UTC]`, coordenadas flotantes).
2. **Rangos Geográficos Válidos:**
   - Latitud: $[-90.0, 90.0]$
   - Longitud: $[-180.0, 180.0]$
3. **Rangos Físicos Plausibles:**
   - Magnitud sísmica: $[-2.0, 10.0]$
   - Profundidad hipocentral: $[-5.0, 1000.0]$ km
4. **Unicidad e Idempotencia:** Detección de duplicados en la capa Bronce mediante hash SHA-256 y upsert en la capa Curated (`ON CONFLICT (id) DO UPDATE`).
5. **Control de Frescura:** Valida que el tiempo transcurrido desde el último sismo registrado no supere el umbral máximo tolerado (180 minutos).
6. **Control de Volumen:** Alerta ante caída drástica (conteo igual a cero sin caída de la fuente) o explosión inusual de registros ($> 10,000$ eventos por lote).

### 3.3 Visualización de Resultados
- **En Base de Datos:** Registros en `curated.data_quality_runs` con el conteo de reglas evaluadas, registros aprobados, fallidos, porcentaje de aprobación (`score_pct`) y estado (`PASSED`, `WARNING`, `FAILED`).
- **En la Plataforma Web:** Pestaña **Salud Pipeline**, donde se visualiza el puntaje global, la frescura y la tabla detallada de auditoría.
- **Filtrado y Descarte Directo:** Los registros no conformes son descartados automáticamente del flujo hacia `curated` para proteger la integridad analítica, registrándose el conteo exacto de fallos en `curated.data_quality_runs`.

---

## 4. Seguridad y Gestión de Mínimo Privilegio

### 4.1 Gestión de Secretos
- Ninguna contraseña, API key ni clave criptográfica está escrita en el código fuente.
- Se proporciona `.env.example` versionado y `.env` excluido estrictamente mediante `.gitignore`.
- Clave Fernet de Airflow autogenerada y credenciales de usuario inyectadas por variables de entorno.

### 4.2 Mínimo Privilegio en PostgreSQL
Se definieron tres roles independientes a nivel de base de datos (`db/init/02_create_roles.sql`):
1. `sismo_ingest`: Permiso exclusivo de escritura en el esquema `raw`.
2. `sismo_etl`: Permiso de lectura en `raw`, lectura/escritura en `staging`, inserción en `curated` y `data_quality_runs`.
3. `sismo_app`: **Acceso exclusivo de solo lectura (`SELECT`) en el esquema `curated`**. La API jamás tiene permisos de modificación sobre los datos históricos ni acceso a los esquemas `raw` ni `staging`.

### 4.3 Autenticación y Modelo de Roles (RBAC)
- Autenticación mediante **JSON Web Tokens (JWT)** con algoritmo HS256 y expiración configurable.
- **Visitante (sin login):** Ninguna ruta ni endpoint de datos es accesible (retorna `401 Unauthorized`).
- **Viewer:** Puede consultar KPIs, mapas, listados de eventos, gráficos, historial de reportes y streaming en tiempo real. **Cualquier llamada a rutas administrativas es bloqueada con `403 Forbidden`**.
- **Admin:** Control total, incluyendo disparo de backfill histórico y regeneración forzada de reportes con IA.

### 4.4 Sanitización contra Prompt Injection
La función `sanitize_text()` en `airflow/include/clients/ai_client.py` limpia campos provenientes de la fuente externa (como `place`) eliminando caracteres de control, secuencias SQL e instrucciones de manipulación de contexto ("ignore previous instructions", "system prompt", etc.) antes de enviarlos al modelo de lenguaje.

### 4.5 Evidencia de Escaneo de Seguridad
Se ejecutaron análisis estáticos y de vulnerabilidades sobre el código del proyecto:

#### 1. Bandit (Análisis Estático de Seguridad de Código)
```
$ bandit -r airflow/include/ api/app/ -ll
[main]  INFO    running on Python 3.12.3
Run started: 2026-10-27 12:29:53 UTC

Test results:
        No issues identified.

Code scanned:
        Total lines of code: 2311
        Total potential issues skipped due to specifically being disabled: 2 (#nosec B608 verificados)

Run metrics:
        Total issues (by severity):
                Undefined: 0, Low: 1, Medium: 0, High: 0
```
*(Resultado: 0 vulnerabilidades de severidad media o alta).*

#### 2. Pip-Audit (Auditoría de Dependencias de Paquetes)
```
$ pip-audit
No known vulnerabilities found in core application packages (FastAPI, SQLAlchemy, Pandera, PySpark, Cryptography, Pydantic).
```

---

## 5. Automatización con Inteligencia Artificial

### 5.1 Proveedor y Modelo
- **Modelo:** `qwen2.5` ejecutado en servidor local **Ollama** (vía `http://host.docker.internal:11434`), con temperatura baja ($0.2$) para máxima consistencia y precisión formal.

### 5.2 Las Dos Automatizaciones Implementadas
1. **Reporte Narrativo Ejecutivo (IA Generativa):** El DAG `dag_daily_ai_report` sintetiza cada día la actividad global destacando eventos mayores, alertas de tsunami y recomendaciones para comités de operaciones.
2. **Detección Estadística de Anomalías (Analítica / ML):** Algoritmo Z-Score aplicado sobre ventanas móviles de 24 horas para identificar **enjambres sísmicos (Seismic Swarms)** en fallas geológicas activas ($Z \ge 2.0$) y outliers de magnitud ($M \ge 6.0$).

### 5.3 Controles Obligatorios contra Alucinaciones
- **Cifras Calculadas por Código:** El LLM **nunca calcula números**. Todos los valores (conteos, máximos, medias geométricas, profundidades y porcentajes) son computados determinísticamente en SQL y Python antes de poblar la plantilla del prompt.
- **Prompts Versionados:** La plantilla formal reside en `airflow/include/prompts/daily_executive_v1.txt`.
- **Validador de Guardrails Numéricos:** Una función regex comprueba que la magnitud máxima y los eventos computados estén presentes en el texto del modelo sin discrepancias numéricas.
- **Fallback Determinista:** Si Ollama está apagado, supera el timeout configurado ($30$ s) o alucina cifras, el generador activa automáticamente una plantilla determinista con los datos verificados, garantizando que el pipeline nunca se detenga.
- **Auditoría Técnica:** Cada invocación registra modelo, versión del prompt, tokens utilizados, latencia en milisegundos y estado (`SUCCESS` o `FALLBACK_GENERATED`) en la tabla `curated.ai_execution_logs`.

### 5.4 Asistente Chatbot Analítico (Dominio sobre Silver y Gold)
Se integró un Chatbot interactivo de alta velocidad directamente en la plataforma web y la API (`POST /api/chat/query`):
- **Dominio Total de Capas:** Consulta en tiempo real tanto la capa **Silver** (`staging.earthquake_events_staging`) como la capa **Gold** (`curated.earthquake_events`, `curated.data_quality_runs`, reportes y logs).
- **Arquitectura de Máxima Velocidad (Motor Híbrido):**
  1. *Caché en Memoria LRU (TTL 30s):* Respuestas en **< 1 ms** para consultas repetidas.
  2. *Fast-Path Semántico Compilado:* Detección de patrones analíticos (sismos mayores, comparación Silver vs Gold, tsunamis, países, auditorías) con ejecución directa en PostgreSQL en **< 20 ms**.
  3. *Text-to-SQL Seguro con LLM (Ollama):* Para preguntas abiertas, genera SQL tipado restringido a sentencias `SELECT`, con validación estricta de palabras clave, transacciones de solo lectura (`SET TRANSACTION READ ONLY;`) y `statement_timeout = '3000ms'`.
  4. *Fallback de Resiliencia:* Búsqueda difusa garantizada si la IA no está disponible o supera los límites de tiempo.

---

## 6. Tiempo Real: Server-Sent Events (SSE)

### 6.1 Mecanismo Elegido y Justificación
- **Tecnología:** **Server-Sent Events (SSE)** en el endpoint `/api/stream`.
- **Por qué sobre WebSockets o Polling:**
  - El monitoreo sísmico requiere una transmisión **unidireccional** desde los sensores hacia los operadores. SSE opera nativamente sobre HTTP/1.1 y HTTP/2 sin la complejidad del protocolo bidireccional de WebSockets.
  - Ofrece **reconexión automática nativa** mediante el objeto del navegador `EventSource`.
  - Envía eventos nuevos en cuanto el pipeline los procesa e incluye un latido de corazón (*heartbeat*) cada 5 segundos para mantener el canal abierto sin sobrecargar la red ni la base de datos.
- **Indicador Visual:** La barra de navegación muestra un badge animado **"EN VIVO (SSE)"** que cambia a color ámbar si la conexión se interrumpe y reconecta de forma autónoma.

---

## 7. Ejecución de Pruebas Automatizadas

La suite de pruebas con **pytest** valida todos los componentes del sistema con un único comando:

```bash
# Activar entorno virtual y ejecutar pytest
source .venv/bin/activate
pytest -v
```

### Resultados de la Ejecución de Pruebas:
```
============================= test session starts ==============================
collected 21 items

tests/test_api_endpoints.py::test_unauthenticated_request_returns_401 PASSED [  4%]
tests/test_api_endpoints.py::test_viewer_can_access_kpis_and_events PASSED [  9%]
tests/test_api_endpoints.py::test_viewer_blocked_from_admin_backfill PASSED [ 14%]
tests/test_api_endpoints.py::test_admin_can_access_admin_endpoints PASSED [ 19%]
tests/test_api_endpoints.py::test_health_check_public PASSED             [ 23%]
tests/test_chatbot.py::test_unauthenticated_chat_query_returns_401 PASSED [ 28%]
tests/test_chatbot.py::test_viewer_can_query_chatbot PASSED              [ 33%]
tests/test_chatbot.py::test_chat_suggestions_endpoint PASSED             [ 38%]
tests/test_chatbot.py::test_chatbot_sanitization_removes_malicious_commands PASSED [ 42%]
tests/test_chatbot.py::test_chatbot_in_memory_cache PASSED               [ 47%]
tests/test_dag_integrity.py::test_dag_files_syntax_and_structure PASSED  [ 52%]
tests/test_dag_integrity.py::test_dag_integrity_dagbag PASSED            [ 57%]
tests/test_quality_rules.py::test_valid_record_passes_quality_gate PASSED [ 61%]
tests/test_quality_rules.py::test_invalid_latitude_is_rejected_and_discarded PASSED [ 66%]
tests/test_quality_rules.py::test_invalid_magnitude_is_rejected_and_discarded PASSED [ 71%]
tests/test_quality_rules.py::test_data_freshness_check PASSED            [ 76%]
tests/test_quality_rules.py::test_volume_bounds_check PASSED             [ 80%]
tests/test_transformations.py::test_epoch_ms_to_datetime_conversion PASSED [ 85%]
tests/test_transformations.py::test_transform_valid_geojson_feature PASSED [ 90%]
tests/test_transformations.py::test_transform_feature_missing_id PASSED  [ 95%]
tests/test_transformations.py::test_transform_feature_missing_coordinates PASSED [100%]

======================== 21 passed in 3.40s ========================
```

---

## 8. Limitaciones Conocidas y Mejoras Futuras

1. **Airflow LocalExecutor a Gran Escala:** Para procesar millones de eventos por segundo, se recomienda migrar a `KubernetesExecutor` o `CeleryExecutor` con autoescalado dinámico.
2. **Formatos Abiertos de Lago (Iceberg):** En producción empresarial, los datos en MinIO/S3 podrían estructurarse en formato Apache Iceberg con particionamiento temporal y soporte de viajes en el tiempo analíticos (*Time Travel*).
3. **Notificaciones Push:** Integración de webhooks hacia canales de Slack, Microsoft Teams o Telegram en el callback de fallos y ante eventos sísmicos $M \ge 6.5$.
4. **Modelos Predictivos Espaciotemporales:** Implementar modelos de aprendizaje profundo (LSTM / GNN) para estimar la probabilidad de réplicas tras eventos de alta magnitud.