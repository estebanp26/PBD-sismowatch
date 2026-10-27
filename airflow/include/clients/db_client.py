"""
SismoWatch - Cliente de Base de Datos PostgreSQL
Operaciones seguras con separación de roles (sismo_ingest, sismo_etl, sismo_app).
"""

from contextlib import contextmanager
import json
import logging
import math
from typing import Any, Dict, Generator, List, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

from include.config import get_connection_url

logger = logging.getLogger(__name__)

def _clean_sql_record(d: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte NaN, NaT y valores no serializables a None para PostgreSQL."""
    cleaned = {}
    for k, v in d.items():
        if v is None:
            cleaned[k] = None
        elif isinstance(v, float) and math.isnan(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned

# Cache de motores SQLAlchemy por rol para optimizar conexiones
_ENGINE_CACHE: Dict[str, Engine] = {}

def get_engine_for_role(role: str = "etl") -> Engine:
    """Devuelve o crea un engine con pool de conexiones para el rol indicado."""
    if role not in _ENGINE_CACHE:
        url = get_connection_url(role)
        _ENGINE_CACHE[role] = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 10}
        )
    return _ENGINE_CACHE[role]

@contextmanager
def get_db_connection(role: str = "etl") -> Generator[Connection, None, None]:
    """Context manager para obtener conexiones seguras con commit/rollback automático."""
    engine = get_engine_for_role(role)
    with engine.begin() as conn:
        yield conn

class DatabaseManager:
    """Gestor de operaciones de persistencia en las capas Raw, Staging y Curated."""

    @staticmethod
    def save_raw_feed(source_url: str, payload_hash: str, raw_payload: Dict[str, Any], event_count: int) -> Tuple[Optional[int], bool]:
        """
        Inserta el payload en raw.usgs_earthquakes_raw de forma idempotente.
        Retorna (id_insertado, fue_insertado_nuevo).
        """
        query = text("""
            INSERT INTO raw.usgs_earthquakes_raw (source_url, payload_hash, event_count, raw_payload)
            VALUES (:source_url, :payload_hash, :event_count, :raw_payload)
            ON CONFLICT (payload_hash) DO NOTHING
            RETURNING id;
        """)

        with get_db_connection(role="ingest") as conn:
            result = conn.execute(query, {
                "source_url": source_url,
                "payload_hash": payload_hash,
                "event_count": event_count,
                "raw_payload": json.dumps(raw_payload)
            }).fetchone()

            if result:
                raw_id = result[0]
                logger.info(f"Nuevo payload crudo almacenado en raw.usgs_earthquakes_raw (ID: {raw_id})")
                return raw_id, True
            else:
                # El payload ya existía (idempotencia)
                existing = conn.execute(
                    text("SELECT id FROM raw.usgs_earthquakes_raw WHERE payload_hash = :hash"),
                    {"hash": payload_hash}
                ).fetchone()
                existing_id = existing[0] if existing else None
                logger.info(f"Payload ya existente en raw (Hash: {payload_hash[:12]}..., ID: {existing_id}). Carga omitida.")
                return existing_id, False

    @staticmethod
    def get_unprocessed_raw_payloads(limit: int = 10) -> List[Dict[str, Any]]:
        """Recupera los últimos registros crudos para ser transformados."""
        query = text("""
            SELECT id, source_url, payload_hash, event_count, raw_payload, ingested_at
            FROM raw.usgs_earthquakes_raw
            ORDER BY ingested_at DESC
            LIMIT :limit;
        """)
        with get_db_connection(role="etl") as conn:
            rows = conn.execute(query, {"limit": limit}).fetchall()
            return [
                {
                    "id": r[0],
                    "source_url": r[1],
                    "payload_hash": r[2],
                    "event_count": r[3],
                    "raw_payload": r[4],
                    "ingested_at": r[5]
                }
                for r in rows
            ]

    @staticmethod
    def save_staging_events(events: List[Dict[str, Any]]) -> int:
        """
        Inserta registros limpios en la capa staging.earthquake_events_staging.
        """
        if not events:
            return 0

        staging_query = text("""
            INSERT INTO staging.earthquake_events_staging (
                id, mag, place, time, updated, tz, url, detail, felt, cdi, mmi, alert,
                status, tsunami, sig, net, code, ids, sources, types, nst, dmin, rms,
                gap, mag_type, type, title, longitude, latitude, depth_km, raw_reference_id
            )
            VALUES (
                :id, :mag, :place, :time, :updated, :tz, :url, :detail, :felt, :cdi, :mmi, :alert,
                :status, :tsunami, :sig, :net, :code, :ids, :sources, :types, :nst, :dmin, :rms,
                :gap, :mag_type, :type, :title, :longitude, :latitude, :depth_km, :raw_reference_id
            )
            ON CONFLICT (id) DO UPDATE SET
                mag = EXCLUDED.mag,
                updated = EXCLUDED.updated,
                status = EXCLUDED.status,
                ingested_at = NOW();
        """)
        saved_count = 0
        failed_count = 0
        with get_db_connection(role="etl") as conn:
            for ev in events:
                try:
                    with conn.begin_nested():  # Savepoint para aislar errores por registro
                        # Sanitizar campos faltantes
                        record_params = {
                            "id": ev.get("id"),
                            "mag": ev.get("mag"),
                            "place": ev.get("place"),
                            "time": ev.get("time"),
                            "updated": ev.get("updated"),
                            "tz": ev.get("tz"),
                            "url": ev.get("url"),
                            "detail": ev.get("detail"),
                            "felt": ev.get("felt"),
                            "cdi": ev.get("cdi"),
                            "mmi": ev.get("mmi"),
                            "alert": ev.get("alert"),
                            "status": ev.get("status"),
                            "tsunami": ev.get("tsunami", 0),
                            "sig": ev.get("sig"),
                            "net": ev.get("net"),
                            "code": ev.get("code"),
                            "ids": ev.get("ids"),
                            "sources": ev.get("sources"),
                            "types": ev.get("types"),
                            "nst": ev.get("nst"),
                            "dmin": ev.get("dmin"),
                            "rms": ev.get("rms"),
                            "gap": ev.get("gap"),
                            "mag_type": ev.get("mag_type"),
                            "type": ev.get("type"),
                            "title": ev.get("title"),
                            "longitude": ev.get("longitude"),
                            "latitude": ev.get("latitude"),
                            "depth_km": ev.get("depth_km"),
                            "raw_reference_id": ev.get("raw_reference_id")
                        }
                        conn.execute(staging_query, _clean_sql_record(record_params))
                        saved_count += 1
                except Exception as row_err:
                    failed_count += 1
                    logger.error(f"[ERROR DB STAGING]: Error al guardar sismo id={ev.get('id')}: {row_err}. Registro omitido sin romper el pipeline.")

        if failed_count > 0:
            logger.warning(f"[AVISO STAGING]: Se guardaron {saved_count} eventos exitosamente; {failed_count} fallaron y fueron descartados.")
        else:
            logger.info(f"Guardados {saved_count} eventos en staging.earthquake_events_staging.")
        return saved_count

    @staticmethod
    def upsert_curated_events(events: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Inserta o actualiza eventos en curated.earthquake_events asegurando idempotencia.
        Retorna (insertados_nuevos, actualizados).
        """
        if not events:
            return 0, 0

        upsert_query = text("""
            INSERT INTO curated.earthquake_events (
                id, mag, place, time, updated, tz, url, detail, felt, cdi, mmi, alert,
                status, tsunami, sig, net, code, ids, sources, types, nst, dmin, rms,
                gap, mag_type, type, title, longitude, latitude, depth_km, is_updated, processed_at
            )
            VALUES (
                :id, :mag, :place, :time, :updated, :tz, :url, :detail, :felt, :cdi, :mmi, :alert,
                :status, :tsunami, :sig, :net, :code, :ids, :sources, :types, :nst, :dmin, :rms,
                :gap, :mag_type, :type, :title, :longitude, :latitude, :depth_km, FALSE, NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                mag = EXCLUDED.mag,
                place = EXCLUDED.place,
                updated = EXCLUDED.updated,
                status = EXCLUDED.status,
                tsunami = EXCLUDED.tsunami,
                sig = EXCLUDED.sig,
                longitude = EXCLUDED.longitude,
                latitude = EXCLUDED.latitude,
                depth_km = EXCLUDED.depth_km,
                is_updated = TRUE,
                processed_at = NOW();
        """)

        upserted_count = 0
        failed_count = 0
        with get_db_connection(role="etl") as conn:
            for ev in events:
                try:
                    with conn.begin_nested():  # Savepoint para aislar errores por registro en Curated
                        conn.execute(upsert_query, _clean_sql_record(ev))
                        upserted_count += 1
                except Exception as row_err:
                    failed_count += 1
                    logger.error(f"[ERROR DB CURATED]: Error en upsert de sismo id={ev.get('id')}: {row_err}. Registro omitido sin romper el pipeline.")

        if failed_count > 0:
            logger.warning(f"[AVISO CURATED]: Upsert completado con {upserted_count} eventos guardados; {failed_count} fallaron.")
        else:
            logger.info(f"Upsert completado exitosamente en curated.earthquake_events: {upserted_count} eventos procesados.")
        return upserted_count, 0
    @staticmethod
    def record_quality_metrics(
        dag_run_id: str,
        rule_name: str,
        evaluated: int,
        passed: int,
        failed: int,
        score_pct: float,
        status: str
    ) -> None:
        """Registra el resultado de una regla de calidad en curated.data_quality_runs."""
        query = text("""
            INSERT INTO curated.data_quality_runs (
                dag_run_id, rule_name, records_evaluated, records_passed, records_failed, score_pct, status
            )
            VALUES (:dag_run_id, :rule_name, :evaluated, :passed, :failed, :score_pct, :status);
        """)

        with get_db_connection(role="etl") as conn:
            conn.execute(query, {
                "dag_run_id": dag_run_id,
                "rule_name": rule_name,
                "evaluated": evaluated,
                "passed": passed,
                "failed": failed,
                "score_pct": score_pct,
                "status": status
            })
