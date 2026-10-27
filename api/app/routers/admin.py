"""
SismoWatch - Router de Operaciones Administrativas (/api/admin)
Endpoints exclusivos de Administrador protegidos con RBAC estricto (403 para Viewer).
"""

from fastapi import APIRouter, Depends, status
from app.core.security import require_admin
from app.schemas.earthquake import BackfillRequest
from app.services.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["Administración"])

@router.post("/backfill", status_code=status.HTTP_202_ACCEPTED, summary="Lanzar backfill histórico (Solo Admin)")
def launch_historical_backfill(
    request: BackfillRequest,
    current_user: dict = Depends(require_admin)  # Requiere rol 'admin', rechaza 'viewer' con 403
):
    """
    Inicia la carga histórica de eventos sísmicos desde el catálogo de USGS
    con control de idempotencia y compuerta de calidad.
    """
    result = AdminService.trigger_backfill(
        days_back=request.days_back,
        min_magnitude=request.min_magnitude
    )
    return result

@router.post("/reports/regenerate", status_code=status.HTTP_202_ACCEPTED, summary="Regenerar reporte ejecutivo con IA (Solo Admin)")
def regenerate_ai_report(
    current_user: dict = Depends(require_admin)  # Requiere rol 'admin', rechaza 'viewer' con 403
):
    """
    Fuerza la ejecución inmediata del análisis de anomalías y la generación
    del reporte narrativo con IA para actualizar el resumen ejecutivo.
    """
    result = AdminService.trigger_report_regeneration()
    return result
