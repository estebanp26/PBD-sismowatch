"""
SismoWatch - Detección Estadística de Anomalías y Cálculo Determinista de KPIs
Identificación de enjambres sísmicos (Z-score / clustering) y cálculo de indicadores clave.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, List, Tuple
import numpy as np
from sqlalchemy import text

from include.clients.db_client import get_db_connection

logger = logging.getLogger(__name__)

class SeismicAnalyticsService:
    """Servicio analítico para KPIs y detección de anomalías en la capa Curated."""

    @staticmethod
    def calculate_deterministic_kpis(hours_back: int = 24) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
        """
        Calcula determinísticamente mediante SQL las métricas de las últimas N horas.
        Retorna (metrics_dict, top_regions_list, highlight_event_string).
        """
        kpi_query = text("""
            SELECT 
                COUNT(*) AS total_events,
                COALESCE(MAX(mag), 0.0) AS max_magnitude,
                COALESCE(ROUND(AVG(mag)::numeric, 2), 0.0) AS avg_magnitude,
                COALESCE(SUM(CASE WHEN tsunami = 1 THEN 1 ELSE 0 END), 0) AS tsunami_alerts,
                COALESCE(ROUND(AVG(depth_km)::numeric, 1), 0.0) AS avg_depth_km
            FROM curated.earthquake_events
            WHERE time >= NOW() - (:hours || ' hours')::interval;
        """)

        regions_query = text("""
            SELECT 
                SPLIT_PART(place, ', ', 2) AS region_clean,
                COUNT(*) AS event_count,
                MAX(mag) AS max_mag
            FROM curated.earthquake_events
            WHERE time >= NOW() - (:hours || ' hours')::interval
              AND place LIKE '%, %'
            GROUP BY region_clean
            ORDER BY event_count DESC, max_mag DESC
            LIMIT 5;
        """)

        highlight_query = text("""
            SELECT title, mag, place
            FROM curated.earthquake_events
            WHERE time >= NOW() - (:hours || ' hours')::interval
            ORDER BY mag DESC, time DESC
            LIMIT 1;
        """)

        with get_db_connection(role="etl") as conn:
            kpi_row = conn.execute(kpi_query, {"hours": hours_back}).fetchone()
            metrics = {
                "total_events": int(kpi_row[0]) if kpi_row else 0,
                "max_magnitude": float(kpi_row[1]) if kpi_row else 0.0,
                "avg_magnitude": float(kpi_row[2]) if kpi_row else 0.0,
                "tsunami_alerts": int(kpi_row[3]) if kpi_row else 0,
                "avg_depth_km": float(kpi_row[4]) if kpi_row else 0.0,
                "period_hours": hours_back
            }

            region_rows = conn.execute(regions_query, {"hours": hours_back}).fetchall()
            top_regions = [
                {
                    "region": r[0] if r[0] else "Zona Marítima",
                    "count": int(r[1]),
                    "max_mag": float(r[2])
                }
                for r in region_rows
            ]

            h_row = conn.execute(highlight_query, {"hours": hours_back}).fetchone()
            highlight_event = f"{h_row[0]} ({h_row[2]})" if h_row else "Sin eventos relevantes registrados"

        logger.info(f"KPIs calculados: {metrics['total_events']} eventos, Mag Máx: {metrics['max_magnitude']}, Promedio: {metrics['avg_magnitude']}")
        return metrics, top_regions, highlight_event

    @staticmethod
    def detect_and_record_anomalies(hours_back: int = 24, z_score_threshold: float = 2.0) -> List[Dict[str, Any]]:
        """
        Detección estadística de comportamientos anómalos:
        1. Enjambres sísmicos (Seismic Swarms): concentración inusual de eventos en una región (Z-score > umbral).
        2. Outliers de magnitud: sismos con M >= 6.0 o significancia extrema.
        Persiste los hallazgos en curated.seismic_anomalies.
        """
        query_regional = text("""
            SELECT 
                SPLIT_PART(place, ', ', 2) AS region_clean,
                COUNT(*) AS event_count,
                AVG(mag) AS mean_mag,
                MAX(mag) AS max_mag
            FROM curated.earthquake_events
            WHERE time >= NOW() - (:hours || ' hours')::interval
              AND place LIKE '%, %'
            GROUP BY region_clean
            HAVING COUNT(*) >= 3;
        """)

        anomalies_detected: List[Dict[str, Any]] = []

        with get_db_connection(role="etl") as conn:
            rows = conn.execute(query_regional, {"hours": hours_back}).fetchall()
            if not rows:
                return []

            counts = np.array([float(r[1]) for r in rows])
            mean_count = np.mean(counts)
            std_count = np.std(counts) if np.std(counts) > 0 else 1.0

            for r in rows:
                region = r[0] or "Zona no delimitada"
                count = int(r[1])
                mean_mag = round(float(r[2]), 2)
                max_mag = round(float(r[3]), 2)

                z_score = round((count - mean_count) / std_count, 2)

                # Detección de Enjambre Sísmico (Seismic Swarm)
                if z_score >= z_score_threshold:
                    desc = (
                        f"Alerta de Enjambre Sísmico en '{region}': {count} eventos en {hours_back}h "
                        f"(Z-score: +{z_score:.2f} sobre media global de {mean_count:.1f}). "
                        f"Magnitud promedio M {mean_mag}, máx M {max_mag}."
                    )
                    anomalies_detected.append({
                        "anomaly_type": "SEISMIC_SWARM",
                        "region": region,
                        "event_count": count,
                        "mean_magnitude": mean_mag,
                        "max_magnitude": max_mag,
                        "z_score": z_score,
                        "description": desc
                    })

                # Detección de Evento de Alta Energía Individual
                elif max_mag >= 6.0:
                    desc = (
                        f"Evento Sísmico Mayor en '{region}': Magnitud M {max_mag} detectada. "
                        f"Requiere inspección prioritaria de protocolos locales."
                    )
                    anomalies_detected.append({
                        "anomaly_type": "MAGNITUDE_OUTLIER",
                        "region": region,
                        "event_count": count,
                        "mean_magnitude": mean_mag,
                        "max_magnitude": max_mag,
                        "z_score": z_score,
                        "description": desc
                    })

            # Inserción en curated.seismic_anomalies
            insert_query = text("""
                INSERT INTO curated.seismic_anomalies (
                    anomaly_type, region, event_count, mean_magnitude, max_magnitude, z_score, description, detected_at
                )
                VALUES (:anomaly_type, :region, :event_count, :mean_magnitude, :max_magnitude, :z_score, :description, NOW());
            """)

            for a in anomalies_detected:
                conn.execute(insert_query, a)

        logger.info(f"Detección de anomalías completada: {len(anomalies_detected)} anomalías identificadas y registradas.")
        return anomalies_detected
