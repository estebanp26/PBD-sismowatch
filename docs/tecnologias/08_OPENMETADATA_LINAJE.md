# OpenMetadata & Linaje de Datos — Catálogo y Gobernanza End-to-End

## 1. ¿Qué es OpenMetadata y qué rol cumple en SismoWatch?
**OpenMetadata** es la plataforma de código abierto líder para la gobernanza de datos, catálogo unificado, descubrimiento de activos y observabilidad del **linaje de datos (*Data Lineage*)**.

En **SismoWatch**, el linaje de datos responde a tres preguntas operativas fundamentales:
1. **¿De dónde viene cada dato?** Trazabilidad desde el feed GeoJSON del USGS hasta los gráficos del frontend.
2. **¿Qué transformaciones ocurrieron?** Paso por la capa Bronze inmutable (MinIO S3), Silver normalizado (Staging), compuerta bloqueante de Pandera y Gold consolidado (Curated).
3. **¿Cuál es el impacto de un cambio o fallo?** Saber exactamente qué componentes downstream se verán afectados si se interrumpe un DAG o falla una regla de calidad.

---

## 2. Parámetros de Conexión y Arquitectura

| Parámetro | Valor Local por Defecto | Archivo de Configuración | Descripción |
|---|---|---|---|
| **Interfaz Web OpenMetadata** | [http://localhost:8585](http://localhost:8585) | `docker-compose.openmetadata.yml` | Catálogo visual, gráfico de linaje y glosario |
| **Credenciales por Defecto** | `admin` / `admin` | N/A | Acceso administrativo a la consola OpenMetadata |
| **Motor de Búsqueda (OpenSearch)** | `http://localhost:9200` | `docker-compose.openmetadata.yml` | Indexación de metadatos y búsqueda de esquemas |
| **Base de Datos de Metadatos** | MySQL 8.0 (Puerto `3306`) | `docker-compose.openmetadata.yml` | Almacén relacional interno de OpenMetadata |
| **Red Compartida Docker** | `pbd-sismowatch_sismowatch_net` | Ambos Compose | Comunicación directa con Postgres y MinIO |

---

## 3. Estrategia de Despliegue Desacoplado

OpenMetadata junto con su motor OpenSearch y MySQL requiere aproximadamente **4 a 6 GB de memoria RAM**.

Para proteger el rendimiento del equipo de desarrollo y asegurar que Airflow, PostgreSQL, FastAPI y Ollama funcionen con fluidez en máquinas con 8 a 16 GB de RAM, la infraestructura de OpenMetadata se diseñó bajo una **estrategia dual**:

1. **Observabilidad Integrada en la Plataforma Web (Cero Sobrecarga de RAM):**
   - El backend de FastAPI expone el endpoint [`GET /api/metadata/lineage`](file:///home/cohorte5/Escritorio/PBD-sismowatch/api/app/routers/metadata.py).
   - En la pestaña **"Linaje y Flujo"** de la aplicación web (`http://localhost:3000`), dispones inmediatamente de un diagrama interactivo con los conteos reales de registros en cada capa Medallón sin consumir RAM extra.
2. **Servidor Completo OpenMetadata (Bajo Demanda):**
   - Cuando se requiere la experiencia corporativa completa de OpenMetadata (búsqueda facetada, glosarios de términos y linaje visual oficial), se levanta el archivo especializado:
     ```bash
     docker compose -f docker-compose.openmetadata.yml up -d
     ```

---

## 4. Especificación JSON del Linaje de Datos (OpenMetadata Spec 1.3)

La topología del pipeline se formalizó en el archivo:
👉 [`docs/openmetadata/pipeline_metadata.json`](file:///home/cohorte5/Escritorio/PBD-sismowatch/docs/openmetadata/pipeline_metadata.json)

### Topología de los 12 Nodos y 12 Conexiones:
```
[ USGS Earthquake API ] (Fuente Externa)
          │
          ▼
[ Airflow: dag_usgs_ingest_raw ] (Orquestación Ingesta)
    ├──► [ MinIO S3: sismowatch-lake/raw/ ] (Bronze Lakehouse)
    └──► [ PostgreSQL: raw.usgs_earthquakes_raw ] (Bronze DB)
          │
          ▼
[ Airflow: dag_transform_and_quality ] (Orquestación Silver)
          │
          ▼
[ PostgreSQL: staging.earthquake_events_staging ] (Silver Staging)
          │
          ▼
[ Compuerta Bloqueante: Pandera Quality Gate ] (Calidad)
          │
          ▼
[ PostgreSQL: curated.earthquake_events ] (Gold Curated)
    ├──► [ Airflow: dag_daily_ai_report ] ──► [ PostgreSQL: curated.ai_executive_reports ]
    └──► [ FastAPI Backend (sismo_app) ]
                │
                ▼
         [ Plataforma Web React (Puerto 3000) ]
```

---

## 5. Persistencia en Docker Desktop

Los metadatos catalogados en OpenMetadata se conservan en volúmenes independientes:
```yaml
volumes:
  openmetadata_mysql_data:
  openmetadata_opensearch_data:
```

En la pestaña **Volumes** de Docker Desktop, podrás ver organizados los volúmenes del proyecto:
- `postgres_data`: Tablas Medallón del negocio (`raw`, `staging`, `curated`).
- `minio_data`: Archivos GeoJSON crudos inmutables.
- `airflow_logs`: Trazabilidad de ejecuciones de DAGs.
- `openmetadata_mysql_data` y `openmetadata_opensearch_data`: Metadatos y linaje indexados.

---

## 6. Comandos Operativos

```bash
# 1. Iniciar el servidor OpenMetadata
docker compose -f docker-compose.openmetadata.yml up -d

# 2. Verificar el estado de los contenedores
docker compose -f docker-compose.openmetadata.yml ps

# 3. Ver logs del servidor OpenMetadata
docker logs -f openmetadata-server

# 4. Detener OpenMetadata cuando no se esté utilizando (liberando memoria RAM)
docker compose -f docker-compose.openmetadata.yml stop

# 5. Volver a encenderlo preservando todos los metadatos
docker compose -f docker-compose.openmetadata.yml start
```
