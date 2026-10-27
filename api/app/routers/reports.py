"""
SismoWatch - Router de Reportes Ejecutivos (/api/reports)
Historial de reportes asistidos por IA y exportación a formatos CSV y PDF.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import require_viewer_or_admin
from app.db.session import get_db
from app.schemas.earthquake import AIExecutiveReportSchema
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["Reportes"])

@router.get("", response_model=List[AIExecutiveReportSchema], summary="Historial de reportes ejecutivos con IA")
def get_reports(
    limit: int = Query(default=15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_viewer_or_admin)
):
    """Retorna el listado cronológico de reportes narrativos generados con IA."""
    return ReportService.get_reports_history(db, limit=limit)

@router.get("/export", summary="Exportación de reportes o eventos a CSV o PDF")
def export_reports(
    format: str = Query(default="csv", pattern="^(csv|pdf)$", description="Formato de exportación ('csv' o 'pdf')"),
    report_id: Optional[int] = Query(default=None, description="ID del reporte (para PDF)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_viewer_or_admin)
):
    """
    Descarga los datos sísmicos en formato CSV o genera un informe formal en PDF
    con tablas de indicadores y resumen ejecutivo redactado por IA.
    """
    if format == "csv":
        csv_content = ReportService.export_events_csv(db)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sismowatch_eventos.csv"}
        )
    else:  # pdf
        pdf_bytes = ReportService.export_report_pdf(db, report_id=report_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=sismowatch_reporte_ejecutivo.pdf"}
        )
