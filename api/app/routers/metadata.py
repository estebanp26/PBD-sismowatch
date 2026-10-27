"""
SismoWatch - Router de Metadatos y Linaje de Datos (/api/metadata)
Expone el linaje de datos de punta a punta (Data Lineage), catálogo de esquemas
y compatibilidad con OpenMetadata.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import require_viewer_or_admin
from app.db.session import get_db

router = APIRouter(prefix="/api/metadata", tags=["Linaje y Metadatos"])

class LineageNode(BaseModel):
    id: str
    type: str
    name: str
    layer: str
    description: str
    record_count: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

class LineageEdge(BaseModel):
    from_node: str
    to_node: str

class LineageResponse(BaseModel):
    service_name: str
    description: str
    openmetadata_url: str
    openmetadata_compose_file: str
    nodes: List[LineageNode]
    edges: List[Dict[str, str]]
    last_updated: datetime

@router.get("/lineage", response_model=LineageResponse, summary="Obtener el gráfico de linaje de datos y catálogo")
def get_data_lineage(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_viewer_or_admin)
):
    """
    Retorna el flujo completo de datos Medallion con métricas en tiempo real de cada nodo:
    Fuente USGS -> Airflow Ingest -> MinIO/Raw -> Staging -> Pandera Gate -> Curated -> Consumo.
    """
    # Conteos en vivo
    raw_count = db.execute(text("SELECT COUNT(*) FROM raw.usgs_earthquakes_raw;")).scalar() or 0
    staging_count = db.execute(text("SELECT COUNT(*) FROM staging.earthquake_events_staging;")).scalar() or 0
    curated_count = db.execute(text("SELECT COUNT(*) FROM curated.earthquake_events;")).scalar() or 0
    quality_count = db.execute(text("SELECT COUNT(*) FROM curated.data_quality_runs;")).scalar() or 0
    reports_count = db.execute(text("SELECT COUNT(*) FROM curated.ai_executive_reports;")).scalar() or 0

    nodes = [
        LineageNode(
            id="source_usgs",
            type="api",
            name="USGS Earthquake API",
            layer="Fuente Externa",
            description="Feed GeoJSON público en tiempo real (all_hour.geojson) y consultas históricas fdsnws",
            record_count=None,
            details={"endpoint": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson", "cadence": "Cada 5 min"}
        ),
        LineageNode(
            id="dag_ingest",
            type="pipeline",
            name="Airflow: dag_usgs_ingest_raw",
            layer="Orquestación",
            description="Extracción continua, hash SHA-256 e ingesta idempotente",
            record_count=raw_count,
            details={"schedule": "*/5 * * * *", "executor": "LocalExecutor"}
        ),
        LineageNode(
            id="lake_minio",
            type="datalake",
            name="MinIO S3 (Bronze Lake)",
            layer="Bronze",
            description="Almacenamiento inmutable en bucket s3://sismowatch-lake/raw/ con particionamiento por fecha",
            record_count=raw_count,
            details={"bucket": "sismowatch-lake", "format": "GeoJSON crudo"}
        ),
        LineageNode(
            id="table_raw",
            type="table",
            name="raw.usgs_earthquakes_raw",
            layer="Bronze",
            description="Tabla PostgreSQL con payload original y hash SHA-256 para evitar duplicados",
            record_count=raw_count,
            details={"schema": "raw", "columns": 7}
        ),
        LineageNode(
            id="dag_transform",
            type="pipeline",
            name="Airflow: dag_transform_and_quality",
            layer="Orquestación",
            description="Aplanamiento de GeoJSON, conversión a UTC y compuerta Pandera",
            record_count=staging_count,
            details={"trigger": "Dataset / TriggerDagRun"}
        ),
        LineageNode(
            id="table_staging",
            type="table",
            name="staging.earthquake_events_staging",
            layer="Silver",
            description="Capa limpia y fuertemente tipada con coordenadas [lon, lat, profundidad]",
            record_count=staging_count,
            details={"schema": "staging", "columns": 12}
        ),
        LineageNode(
            id="gate_pandera",
            type="quality_gate",
            name="Compuerta Pandera (Quality Gate)",
            layer="Calidad",
            description="Validación declarativa bloqueante: rangos geográficos, magnitudes plausibles y frescura",
            record_count=quality_count,
            details={"tool": "Pandera", "action_on_failure": "Descarte directo sin ingresar a Curated"}
        ),
        LineageNode(
            id="table_curated",
            type="table",
            name="curated.earthquake_events",
            layer="Gold",
            description="Catálogo consolidado final con upsert idempotente y soporte para eventos actualizados",
            record_count=curated_count,
            details={"schema": "curated", "upsert_key": "id", "columns": 19}
        ),
        LineageNode(
            id="dag_ai_report",
            type="pipeline",
            name="Airflow: dag_daily_ai_report",
            layer="Orquestación",
            description="Cálculo determinista en SQL, Z-score de anomalías y redacción con Ollama",
            record_count=reports_count,
            details={"schedule": "0 6 * * *", "model": "llama3:latest / qwen2.5"}
        ),
        LineageNode(
            id="table_reports",
            type="table",
            name="curated.ai_executive_reports",
            layer="Gold",
            description="Informes ejecutivos diarios de actividad sísmica y zonas críticas",
            record_count=reports_count,
            details={"schema": "curated", "columns": 8}
        ),
        LineageNode(
            id="api_fastapi",
            type="service",
            name="SismoWatch API (FastAPI)",
            layer="Consumo",
            description="API con rol sismo_app de solo lectura, autenticación JWT, RBAC, SSE y Chatbot",
            record_count=None,
            details={"port": 8000, "role": "sismo_app (SELECT)"}
        ),
        LineageNode(
            id="web_platform",
            type="dashboard",
            name="Plataforma Web SismoWatch",
            layer="Consumo",
            description="Dashboard interactivo con mapas Leaflet, analítica, chatbot y streaming en tiempo real",
            record_count=None,
            details={"port": 3000, "stack": "React + Vite + Tailwind"}
        )
    ]

    edges = [
        {"from": "source_usgs", "to": "dag_ingest"},
        {"from": "dag_ingest", "to": "lake_minio"},
        {"from": "dag_ingest", "to": "table_raw"},
        {"from": "table_raw", "to": "dag_transform"},
        {"from": "dag_transform", "to": "table_staging"},
        {"from": "table_staging", "to": "gate_pandera"},
        {"from": "gate_pandera", "to": "table_curated"},
        {"from": "table_curated", "to": "dag_ai_report"},
        {"from": "dag_ai_report", "to": "table_reports"},
        {"from": "table_curated", "to": "api_fastapi"},
        {"from": "table_reports", "to": "api_fastapi"},
        {"from": "api_fastapi", "to": "web_platform"}
    ]

    return LineageResponse(
        service_name="SismoWatch Data Lineage",
        description="Flujo de gobernanza de datos Medallion y linaje end-to-end con OpenMetadata",
        openmetadata_url="http://localhost:8585",
        openmetadata_compose_file="docker-compose.openmetadata.yml",
        nodes=nodes,
        edges=edges,
        last_updated=datetime.now(timezone.utc)
    )
