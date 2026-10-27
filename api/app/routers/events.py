"""
SismoWatch - Router de Eventos y Estadísticas (/api)
Consultas de eventos sísmicos en Curated, KPIs de Dashboard y series temporales.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_viewer_or_admin
from app.db.session import get_db
from app.schemas.earthquake import (
    KPISummaryResponse,
    PaginatedEventsResponse,
    StatsResponse
)
from app.services.event_service import EventService
from app.services.kpi_service import KPIService

router = APIRouter(prefix="/api", tags=["Eventos y Analítica"])

@router.get("/kpis", response_model=KPISummaryResponse, summary="Indicadores clave del dashboard")
def get_kpis(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_viewer_or_admin)
):
    """Retorna los KPIs acumulados de las últimas 24 horas y salud del dato."""
    return KPIService.get_kpi_summary(db)

@router.get("/events", response_model=PaginatedEventsResponse, summary="Listado paginado de eventos sísmicos")
def get_events(
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Registros por página"),
    min_mag: Optional[float] = Query(default=None, description="Magnitud mínima"),
    max_mag: Optional[float] = Query(default=None, description="Magnitud máxima"),
    region: Optional[str] = Query(default=None, description="Filtro textual de región o país"),
    tsunami_only: bool = Query(default=False, description="Solo sismos con alerta de tsunami"),
    start_date: Optional[datetime] = Query(default=None, description="Fecha de inicio (ISO)"),
    end_date: Optional[datetime] = Query(default=None, description="Fecha de fin (ISO)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_viewer_or_admin)
):
    """Consulta la capa Curated con filtros geoespaciales, magnitudes y rangos temporales."""
    return EventService.get_events(
        db=db,
        page=page,
        page_size=page_size,
        min_mag=min_mag,
        max_mag=max_mag,
        region=region,
        tsunami_only=tsunami_only,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/stats/timeseries", response_model=StatsResponse, summary="Serie temporal y distribución de magnitudes")
def get_stats_timeseries(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_viewer_or_admin)
):
    """Retorna la serie horaria de sismos y la distribución por rangos de energía."""
    return KPIService.get_timeseries_and_stats(db)
