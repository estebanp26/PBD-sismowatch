"""
SismoWatch - Esquemas Pydantic
Definición de contratos de entrada y salida tipados para la API REST.
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# Autenticación y Usuarios
# -------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario registrado")
    password: str = Field(..., description="Contraseña en texto plano")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool

# -------------------------------------------------------------
# Eventos Sísmicos
# -------------------------------------------------------------
class EarthquakeEventSchema(BaseModel):
    id: str
    mag: float
    place: str
    time: datetime
    updated: Optional[datetime] = None
    url: Optional[str] = None
    status: str
    tsunami: int
    sig: Optional[int] = 0
    mag_type: Optional[str] = None
    type: Optional[str] = "earthquake"
    title: Optional[str] = None
    longitude: float
    latitude: float
    depth_km: float
    is_updated: Optional[bool] = False

class PaginatedEventsResponse(BaseModel):
    items: List[EarthquakeEventSchema]
    total: int
    page: int
    page_size: int
    total_pages: int

# -------------------------------------------------------------
# Indicadores Clave (KPIs)
# -------------------------------------------------------------
class KPISummaryResponse(BaseModel):
    events_last_24h: int
    max_magnitude_24h: float
    avg_magnitude_24h: float
    tsunami_alerts_24h: int
    quality_score: float
    last_event_time: Optional[datetime]
    data_freshness_minutes: float
    last_pipeline_run: Optional[datetime]

# -------------------------------------------------------------
# Estadísticas y Gráficos
# -------------------------------------------------------------
class TimeSeriesPoint(BaseModel):
    hour: str
    count: int
    max_mag: float

class MagnitudeDistribution(BaseModel):
    range_label: str
    count: int

class RegionActivity(BaseModel):
    region: str
    count: int
    max_mag: float

class StatsResponse(BaseModel):
    timeseries: List[TimeSeriesPoint]
    distribution: List[MagnitudeDistribution]
    top_regions: List[RegionActivity]

# -------------------------------------------------------------
# Reportes y Calidad
# -------------------------------------------------------------
class AIExecutiveReportSchema(BaseModel):
    id: int
    report_date: date
    title: str
    summary_text: str
    top_regions: List[Dict[str, Any]]
    metrics_snapshot: Dict[str, Any]
    generated_by_model: str
    created_at: datetime

class QualityMetricItem(BaseModel):
    rule_name: str
    records_evaluated: int
    records_passed: int
    records_failed: int
    score_pct: float
    status: str
    executed_at: datetime

class PipelineStatusResponse(BaseModel):
    dags_status: Dict[str, str]
    overall_quality_score: float
    freshness_minutes: float
    quality_rules: List[QualityMetricItem] = []
    view_mode: str = "summary"  # 'summary' para viewer, 'detail' para admin
    last_update: datetime


# -------------------------------------------------------------
# Acciones de Administración
# -------------------------------------------------------------
class BackfillRequest(BaseModel):
    days_back: int = Field(default=30, ge=1, le=365)
    min_magnitude: float = Field(default=2.5, ge=1.0, le=9.0)

# -------------------------------------------------------------
# Asistente IA / Chatbot
# -------------------------------------------------------------
class ChatQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Pregunta del usuario para el chatbot")
    history: Optional[List[Dict[str, str]]] = Field(default=None, description="Historial reciente de la conversación")

class ChatQueryResponse(BaseModel):
    reply: str
    data: Optional[Any] = None
    source_layer: Optional[str] = "Gold (curated.earthquake_events)"
    query_sql: Optional[str] = None
    execution_time_ms: float
    cached: Optional[bool] = False
    suggested_questions: Optional[List[str]] = []

