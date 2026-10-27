"""
SismoWatch - Router de Estado del Pipeline (/api/pipeline)
Supervisión de DAGs, métricas de calidad y frescura de datos.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_viewer_or_admin
from app.db.session import get_db
from app.schemas.earthquake import PipelineStatusResponse
from app.services.quality_service import QualityService

router = APIRouter(prefix="/api", tags=["Pipeline y Calidad"])

@router.get("/pipeline/status", response_model=PipelineStatusResponse, summary="Estado del pipeline y resumen de calidad")
def get_pipeline_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_viewer_or_admin)
):
    """
    Retorna el estado de ejecución de los DAGs, métricas de calidad y frescura de los datos.
    - Viewer: Retorna únicamente la vista 'summary' (resumen).
    - Admin: Retorna la vista 'detail' con el detalle de las reglas evaluadas.
    """
    is_admin = current_user.get("role") == "admin"
    return QualityService.get_pipeline_status(db, is_admin=is_admin)

