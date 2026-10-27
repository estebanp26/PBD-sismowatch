"""
SismoWatch - Servicio de Indicadores Clave (KPIs) y Estadísticas
Cálculo de métricas operativas y datos para gráficos de series de tiempo y distribuciones.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.earthquake import (
    KPISummaryResponse,
    StatsResponse,
    TimeSeriesPoint,
    MagnitudeDistribution,
    RegionActivity
)

class KPIService:
    @staticmethod
    def get_kpi_summary(db: Session) -> KPISummaryResponse:
        """Calcula los indicadores principales para las tarjetas del Dashboard."""
        kpi_query = text("""
            SELECT 
                COUNT(*) AS total_24h,
                COALESCE(MAX(mag), 0.0) AS max_mag_24h,
                COALESCE(ROUND(AVG(mag)::numeric, 2), 0.0) AS avg_mag_24h,
                COALESCE(SUM(CASE WHEN tsunami = 1 THEN 1 ELSE 0 END), 0) AS tsunamis_24h,
                MAX(time) AS latest_time
            FROM curated.earthquake_events
            WHERE time >= NOW() - INTERVAL '24 hours';
        """)

        quality_query = text("""
            SELECT COALESCE(ROUND(AVG(score_pct)::numeric, 1), 100.0)
            FROM curated.data_quality_runs
            WHERE executed_at >= NOW() - INTERVAL '24 hours';
        """)

        pipeline_query = text("""
            SELECT MAX(executed_at)
            FROM curated.data_quality_runs;
        """)

        row = db.execute(kpi_query).fetchone()
        q_row = db.execute(quality_query).fetchone()
        pipe_row = db.execute(pipeline_query).fetchone()

        total_24h = int(row[0]) if row else 0
        max_mag = float(row[1]) if row else 0.0
        avg_mag = float(row[2]) if row else 0.0
        tsunamis = int(row[3]) if row else 0
        latest_event = row[4] if row else None
        quality_score = float(q_row[0]) if q_row and q_row[0] is not None else 100.0
        last_pipeline = pipe_row[0] if pipe_row else None

        freshness_min = 0.0
        if latest_event:
            now_utc = datetime.now(timezone.utc)
            # Normalizar tzinfo
            event_utc = latest_event if latest_event.tzinfo else latest_event.replace(tzinfo=timezone.utc)
            freshness_min = max(0.0, round((now_utc - event_utc).total_seconds() / 60.0, 1))

        return KPISummaryResponse(
            events_last_24h=total_24h,
            max_magnitude_24h=max_mag,
            avg_magnitude_24h=avg_mag,
            tsunami_alerts_24h=tsunamis,
            quality_score=quality_score,
            last_event_time=latest_event,
            data_freshness_minutes=freshness_min,
            last_pipeline_run=last_pipeline
        )

    @staticmethod
    def get_timeseries_and_stats(db: Session) -> StatsResponse:
        """Obtiene la serie temporal por hora, la distribución por magnitud y top regiones."""
        # 1. Serie temporal por hora (últimas 24h)
        ts_query = text("""
            SELECT 
                TO_CHAR(DATE_TRUNC('hour', time), 'YYYY-MM-DD HH24:00') AS hr,
                COUNT(*) AS cnt,
                COALESCE(MAX(mag), 0.0) AS max_m
            FROM curated.earthquake_events
            WHERE time >= NOW() - INTERVAL '24 hours'
            GROUP BY hr
            ORDER BY hr ASC;
        """)
        ts_rows = db.execute(ts_query).fetchall()
        timeseries = [
            TimeSeriesPoint(hour=r[0], count=int(r[1]), max_mag=float(r[2]))
            for r in ts_rows
        ]

        # 2. Distribución por magnitud
        dist_query = text("""
            SELECT
                CASE 
                    WHEN mag < 3.0 THEN 'Micro (< 3.0)'
                    WHEN mag >= 3.0 AND mag < 4.5 THEN 'Menor (3.0 - 4.4)'
                    WHEN mag >= 4.5 AND mag < 6.0 THEN 'Moderado (4.5 - 5.9)'
                    ELSE 'Fuerte / Mayor (6.0+)'
                END AS range_label,
                COUNT(*) AS count
            FROM curated.earthquake_events
            WHERE time >= NOW() - INTERVAL '7 days'
            GROUP BY range_label
            ORDER BY count DESC;
        """)
        dist_rows = db.execute(dist_query).fetchall()
        distribution = [
            MagnitudeDistribution(range_label=r[0], count=int(r[1]))
            for r in dist_rows
        ]

        # 3. Top regiones con mayor actividad
        reg_query = text("""
            SELECT 
                SPLIT_PART(place, ', ', 2) AS clean_region,
                COUNT(*) AS event_count,
                MAX(mag) AS max_mag
            FROM curated.earthquake_events
            WHERE time >= NOW() - INTERVAL '7 days'
              AND place LIKE '%, %'
            GROUP BY clean_region
            ORDER BY event_count DESC, max_mag DESC
            LIMIT 5;
        """)
        reg_rows = db.execute(reg_query).fetchall()
        top_regions = [
            RegionActivity(region=r[0] or "Océano / Global", count=int(r[1]), max_mag=float(r[2]))
            for r in reg_rows
        ]

        return StatsResponse(
            timeseries=timeseries,
            distribution=distribution,
            top_regions=top_regions
        )
