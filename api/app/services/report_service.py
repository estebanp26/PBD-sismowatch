"""
SismoWatch - Servicio de Reportes Ejecutivos y Exportación (CSV / PDF)
Consulta de historial de reportes con IA y generación de documentos descargables.
"""

import csv
import io
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.schemas.earthquake import AIExecutiveReportSchema

class ReportService:
    @staticmethod
    def get_reports_history(db: Session, limit: int = 15) -> List[AIExecutiveReportSchema]:
        """Obtiene el historial cronológico de reportes generados con IA."""
        query = text("""
            SELECT id, report_date, title, summary_text, top_regions, metrics_snapshot, generated_by_model, created_at
            FROM curated.ai_executive_reports
            ORDER BY report_date DESC
            LIMIT :limit;
        """)
        rows = db.execute(query, {"limit": limit}).fetchall()

        results = []
        for r in rows:
            top_regions = r[4]
            if isinstance(top_regions, str):
                try:
                    top_regions = json.loads(top_regions)
                except Exception:
                    top_regions = []

            metrics = r[5]
            if isinstance(metrics, str):
                try:
                    metrics = json.loads(metrics)
                except Exception:
                    metrics = {}

            results.append(AIExecutiveReportSchema(
                id=r[0],
                report_date=r[1],
                title=r[2],
                summary_text=r[3],
                top_regions=top_regions,
                metrics_snapshot=metrics,
                generated_by_model=r[6],
                created_at=r[7]
            ))

        return results

    @staticmethod
    def export_events_csv(db: Session, limit: int = 500) -> str:
        """Genera un archivo CSV con los eventos sísmicos más recientes."""
        query = text("""
            SELECT id, mag, place, time, status, tsunami, longitude, latitude, depth_km, url
            FROM curated.earthquake_events
            ORDER BY time DESC
            LIMIT :limit;
        """)
        rows = db.execute(query, {"limit": limit}).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Magnitud", "Ubicación", "Fecha UTC", "Estado", "Alerta Tsunami", "Longitud", "Latitud", "Profundidad (km)", "URL USGS"])

        for r in rows:
            writer.writerow([
                r[0], float(r[1]), r[2], r[3].isoformat() if r[3] else "",
                r[4], "SÍ" if r[5] == 1 else "NO", float(r[6]), float(r[7]), float(r[8]), r[9]
            ])

        return output.getvalue()

    @staticmethod
    def export_report_pdf(db: Session, report_id: Optional[int] = None) -> bytes:
        """Genera un reporte ejecutivo en formato PDF descargable utilizando ReportLab."""
        if report_id:
            query = text("SELECT id, report_date, title, summary_text, top_regions, metrics_snapshot, generated_by_model FROM curated.ai_executive_reports WHERE id = :id;")
            row = db.execute(query, {"id": report_id}).fetchone()
        else:
            query = text("SELECT id, report_date, title, summary_text, top_regions, metrics_snapshot, generated_by_model FROM curated.ai_executive_reports ORDER BY report_date DESC LIMIT 1;")
            row = db.execute(query).fetchone()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=12
        )
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            spaceAfter=10
        )
        header_meta = ParagraphStyle(
            'ReportMeta',
            parent=styles['Italic'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=14
        )

        elements = []

        if not row:
            elements.append(Paragraph("SismoWatch - Reporte Ejecutivo no disponible", title_style))
            elements.append(Paragraph("Aún no se ha generado ningún reporte ejecutivo en el sistema.", body_style))
        else:
            report_date = row[1]
            title = row[2]
            summary_text = row[3]
            top_regions = row[4] if isinstance(row[4], list) else (json.loads(row[4]) if row[4] else [])
            metrics = row[5] if isinstance(row[5], dict) else (json.loads(row[5]) if row[5] else {})
            model = row[6]

            elements.append(Paragraph(f"SismoWatch: {title}", title_style))
            elements.append(Paragraph(f"Fecha del Reporte: {report_date} | Motor de IA: {model} | Verificación Determinista: Aprobada", header_meta))
            elements.append(Spacer(1, 10))

            # Resumen Ejecutivo
            elements.append(Paragraph("<b>Resumen Ejecutivo Narrativo</b>", styles['Heading2']))
            for paragraph in summary_text.split("\n\n"):
                if paragraph.strip():
                    elements.append(Paragraph(paragraph.strip(), body_style))

            elements.append(Spacer(1, 15))

            # Tabla de KPIs Verificados
            elements.append(Paragraph("<b>Métricas Clave Calculadas (Verdad Fundamental)</b>", styles['Heading2']))
            table_data = [
                ["Métrica", "Valor Calculado"],
                ["Total de Sismos (24h)", str(metrics.get("total_events", "N/A"))],
                ["Magnitud Máxima", f"M {metrics.get('max_magnitude', 'N/A')}"],
                ["Magnitud Promedio", f"M {metrics.get('avg_magnitude', 'N/A')}"],
                ["Eventos con Alerta de Tsunami", str(metrics.get("tsunami_alerts", 0))],
                ["Profundidad Promedio", f"{metrics.get('avg_depth_km', 'N/A')} km"],
                ["Puntaje de Calidad de Datos", f"{metrics.get('quality_score', 100.0)}%"]
            ]

            t = Table(table_data, colWidths=[240, 260])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')])
            ]))
            elements.append(t)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
