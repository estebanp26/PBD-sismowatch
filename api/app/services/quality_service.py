"""
SismoWatch - Servicio de Estado del Pipeline y Calidad de Datos
Auditoría y métricas de reglas de calidad evaluadas en capa Curated.
"""

from datetime import datetime, timezone
import json
import math
from typing import Any, Dict, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.earthquake import (
    PipelineStatusResponse,
    QualityMetricItem
)

class QualityService:
    @staticmethod
    def get_pipeline_status(db: Session, is_admin: bool = False) -> PipelineStatusResponse:
        """
        Recupera el estado general del pipeline:
        - Para 'viewer': retorna el resumen (KPIs de calidad, frescura y estado de DAGs) con quality_rules vacío.
        - Para 'admin': retorna el detalle completo con la lista de reglas y corridas de calidad.
        """
        rules_query = text("""
            SELECT rule_name, records_evaluated, records_passed, records_failed, score_pct, status, executed_at
            FROM curated.data_quality_runs
            ORDER BY executed_at DESC
            LIMIT 15;
        """)
        rows = db.execute(rules_query).fetchall()

        quality_items = [
            QualityMetricItem(
                rule_name=r[0],
                records_evaluated=int(r[1]),
                records_passed=int(r[2]),
                records_failed=int(r[3]),
                score_pct=float(r[4]),
                status=r[5],
                executed_at=r[6]
            )
            for r in rows
        ]

        # Puntaje promedio global
        avg_score = 100.0
        if quality_items:
            avg_score = round(sum(q.score_pct for q in quality_items) / len(quality_items), 1)

        # Última fecha y frescura
        latest_event_query = text("SELECT MAX(time) FROM curated.earthquake_events;")
        latest_time = db.execute(latest_event_query).scalar()
        freshness_min = 0.0
        if latest_time:
            now_utc = datetime.now(timezone.utc)
            t_utc = latest_time if latest_time.tzinfo else latest_time.replace(tzinfo=timezone.utc)
            freshness_min = max(0.0, round((now_utc - t_utc).total_seconds() / 60.0, 1))

        dags_status = {
            "dag_usgs_ingest_raw": "Activo (cada 5 min)",
            "dag_transform_and_quality": "Activo (por trigger)",
            "dag_daily_ai_report": "Activo (diario 06:00 UTC)",
            "dag_historical_backfill": "Listo (on-demand)"
        }

        return PipelineStatusResponse(
            dags_status=dags_status,
            overall_quality_score=avg_score,
            freshness_minutes=freshness_min,
            quality_rules=quality_items if is_admin else [],
            view_mode="detail" if is_admin else "summary",
            last_update=datetime.now(timezone.utc)
        )
