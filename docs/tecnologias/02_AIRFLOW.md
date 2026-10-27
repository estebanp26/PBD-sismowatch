# Apache Airflow — Documentación Técnica y Orquestación de Pipelines

## 1. ¿Qué es Apache Airflow y qué rol cumple en SismoWatch?
**Apache Airflow** es la plataforma líder para la orquestación programática, programación y supervisión de flujos de trabajo (*workflows* de datos). En **SismoWatch**, Airflow actúa como el **cerebro operativo y director de orquesta de todo el pipeline**.

Airflow garantiza que los datos se extraigan periódicamente, se transformen en el orden correcto, cumplan estrictamente las compuertas de calidad (*Data Quality Gates*) y se generen los reportes ejecutivos diarios de forma autónoma, resiliente y auditable.

---

## 2. Credenciales y Parámetros de Conexión

| Parámetro | Valor Local por Defecto | Variable de Entorno | Descripción |
|---|---|---|---|
| **Interfaz Web (Webserver)** | [http://localhost:8080](http://localhost:8080) | `AIRFLOW_WEBSERVER_PORT=8080` | Panel de control de DAGs, ejecuciones y logs |
| **Usuario Administrador** | `sismo_admin` | `_AIRFLOW_WWW_USER_USERNAME` | Usuario con permisos totales en Airflow |
| **Contraseña Administrador** | `airflow_secure_admin_2026` | `_AIRFLOW_WWW_USER_PASSWORD` | Contraseña de acceso a la interfaz web |
| **Ejecutor (*Executor*)** | `LocalExecutor` | `AIRFLOW__CORE__EXECUTOR` | Ejecución en paralelo local sin sobrecarga de Celery/Redis |
| **Clave Fernet** | Generada en `.env` | `AIRFLOW__CORE__FERNET_KEY` | Clave criptográfica para proteger credenciales y variables |
| **Conexión a Metadatos DB** | `postgresql+psycopg2://...` | `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | Base de datos PostgreSQL propia para el estado de Airflow |

---

## 3. Arquitectura y Componentes de Airflow

El despliegue de Airflow en SismoWatch está compuesto por tres servicios clave:

1. **`airflow-init`**:
   - Inicializa la base de datos de metadatos de Airflow (`airflow db migrate`).
   - Crea automáticamente el usuario administrador `sismo_admin` con su rol `Admin`.
   - Verifica que PostgreSQL esté saludable antes de permitir el inicio del resto de componentes.

2. **`airflow-scheduler`**:
   - Monitorea continuamente las definiciones de los DAGs en la carpeta `airflow/dags/`.
   - Planifica las ejecuciones programadas (*schedules*) según las expresiones cron y gestiona dependencias entre tareas.
   - Ejecuta las tareas utilizando el **LocalExecutor** asignando procesos worker dentro de su propio contenedor.

3. **`airflow-webserver`**:
   - Sirve la interfaz gráfica en el puerto `8080`.
   - Permite pausar/activar DAGs, inspeccionar diagramas de árbol (*Grid View* y *Graph View*), ver logs en tiempo real y reintentar tareas fallidas.

---

## 4. Catálogo Detallado de DAGs en SismoWatch

```
                     ┌───────────────────────────┐
                     │    dag_usgs_ingest_raw    │ (Cada 5 minutos)
                     └─────────────┬─────────────┘
                                   │ Trigger automático
                                   ▼
                     ┌───────────────────────────┐
                     │ dag_transform_and_quality │ (Capa Silver + Pandera + Gold)
                     └───────────────────────────┘
                                   │
                                   ▼ (Diario a las 06:00 UTC)
                     ┌───────────────────────────┐
                     │    dag_daily_ai_report    │ (Reportes Ejecutivos IA)
                     └───────────────────────────┘
```

### 4.1 DAG 1: `dag_usgs_ingest_raw` (Ingesta en Capa Bronze)
- **Archivo:** [`airflow/dags/dag_usgs_ingest_raw.py`](file:///home/cohorte5/Escritorio/PBD-sismowatch/airflow/dags/dag_usgs_ingest_raw.py)
- **Frecuencia:** `*/5 * * * *` (Cada 5 minutos).
- **Propósito:**
  1. Conectar a la API del USGS (`https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson`).
  2. Para cada sismo, calcular un hash **SHA-256** único sobre su contenido para garantizar idempotencia.
  3. Almacenar el GeoJSON crudo inmutable en **MinIO S3** (`sismowatch-lake/raw/`).
  4. Registrar la carga en la tabla PostgreSQL `raw.usgs_earthquakes_raw` omitiendo duplicados mediante cláusula `ON CONFLICT DO NOTHING`.
  5. Activar de inmediato la ejecución de la fase de transformación.

### 4.2 DAG 2: `dag_transform_and_quality` (Silver, Pandera y Gold)
- **Archivo:** [`airflow/dags/dag_transform_and_quality.py`](file:///home/cohorte5/Escritorio/PBD-sismowatch/airflow/dags/dag_transform_and_quality.py)
- **Frecuencia:** Activado por el DAG de ingesta o programado cada 10 minutos.
- **Propósito:**
  1. **Transformación (Silver):** Extrae los eventos crudos de `raw`, aplana las propiedades del GeoJSON, convierte los tiempos Unix en milisegundos a marcas de tiempo estándar UTC (`TIMESTAMPTZ`) e inserta en `staging.earthquake_events_staging`.
  2. **Compuerta Bloqueante de Calidad (Pandera Gate):**
     - Aplica validaciones estrictas: límites geográficos $[-90, 90]$ y $[-180, 180]$, magnitudes válidas $[-2.0, 10.0]$, frescura temporal y presencia obligatoria de identificador.
     - **Política de Cero Cuarentena:** Cualquier registro que no supere la validación es rechazado de inmediato y auditado con el motivo exacto en `curated.data_quality_runs`.
  3. **Consolidación Curada (Gold):** Inserta mediante un `UPSERT` idempotente en `curated.earthquake_events`. Si el USGS actualiza la magnitud o ubicación de un evento existente, el registro se actualiza sin duplicarse.

### 4.3 DAG 3: `dag_daily_ai_report` (Generación de Reportes Inteligentes)
- **Archivo:** [`airflow/dags/dag_daily_ai_report.py`](file:///home/cohorte5/Escritorio/PBD-sismowatch/airflow/dags/dag_daily_ai_report.py)
- **Frecuencia:** `0 6 * * *` (Todos los días a las 06:00 UTC).
- **Propósito:**
  1. **Cálculo Determinista en SQL:** Consulta la capa Gold para calcular KPIs matemáticos exactos (total de sismos, promedio de magnitud, sismo más intenso, alertas de tsunami, regiones más activas).
  2. **Detección de Anomalías (Z-Score):** Compara la actividad de las últimas 24 horas frente a la media móvil histórica de los últimos 30 días para identificar posibles enjambres sísmicos.
  3. **Redacción Asistida por IA (Ollama):** Envía el contexto estadístico estructurado al modelo de lenguaje local para generar un resumen ejecutivo en formato Markdown.
  4. **Guardrail y Persistencia:** Verifica que el reporte no contenga alucinaciones ni contradiga los números calculados en SQL y lo almacena en `curated.ai_executive_reports`.

---

## 5. Parámetros de Idempotencia y Manejo Resiliente de Errores

Todos los DAGs aplican las siguientes mejores prácticas de confiabilidad:
- `retries`: 2 reintentos automáticos en caso de cortes de red con la API del USGS.
- `retry_delay`: Espera de 1 minuto entre reintentos.
- `catchup`: Configurado en `False` para evitar que Airflow lance avalanchas de ejecuciones pasadas al encenderse.
- `depends_on_past`: `False`, permitiendo paralelismo controlado sin bloqueos en cadena.

### 5.1 Arquitectura Anti-Ruptura (Try-Catch y Savepoints por Registro)
Para evitar que un dato anómalo, un registro corrupto o un fallo parcial interrumpa o rompa la ejecución del DAG:
1. **Try-Catch a Nivel de Tarea y Registro:** Cada etapa del pipeline (extracción cruda, transformación Spark/Pandas, compuerta Pandera y carga a Curated) está envuelta en bloques `try...except`.
2. **Savepoints Transaccionales en PostgreSQL (`begin_nested`):** La inserción en Staging y Curated utiliza savepoints de base de datos. Si 1 de 100 registros contiene un formato inválido, solo ese registro es aislado y descartado; los 99 registros válidos se guardan exitosamente sin abortar la transacción.
3. **Reporte Transparente en Airflow:** Todo error o descarte queda registrado de inmediato con nivel `logger.error` o `logger.warning` en los logs de la tarea de Airflow y se publica en **XCom** (`quality_failure_alert`, `transform_warnings`), permitiendo a los operadores auditar el fallo desde la interfaz gráfica sin que el DAG quede en estado rojo fallido.

---

## 6. Comandos Operativos Útiles

```bash
# Ver estado de los contenedores de Airflow
docker compose ps | grep airflow

# Ver logs en vivo del Scheduler
docker logs -f sismowatch_airflow_scheduler

# Listar los DAGs reconocidos dentro del contenedor
docker exec -it sismowatch_airflow_scheduler airflow dags list

# Forzar la ejecución manual del DAG de ingesta desde la terminal
docker exec -it sismowatch_airflow_scheduler airflow dags trigger dag_usgs_ingest_raw

# Verificar que no existen errores de sintaxis en los DAGs
docker exec -it sismowatch_airflow_scheduler airflow dags report
```
