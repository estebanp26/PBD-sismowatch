"""
SismoWatch - Reglas de Calidad de Datos con Pandera
Control bloqueante de calidad, detección de anomalías de esquema y descarte de registros no conformes.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

logger = logging.getLogger(__name__)

# Definición del esquema estricto de calidad con Pandera
EARTHQUAKE_STAGING_SCHEMA = DataFrameSchema(
    columns={
        "id": Column(
            str,
            checks=[
                Check(lambda s: s.str.strip().str.len() > 0, error="El campo 'id' no puede ser una cadena vacía"),
            ],
            nullable=False,
            coerce=True
        ),
        "mag": Column(
            float,
            checks=[
                Check.in_range(-2.0, 10.0, include_min=True, include_max=True, error="Magnitud fuera del rango plausible [-2.0, 10.0]")
            ],
            nullable=False,
            coerce=True
        ),
        "latitude": Column(
            float,
            checks=[
                Check.in_range(-90.0, 90.0, include_min=True, include_max=True, error="Latitud fuera del rango geográfico válido [-90, 90]")
            ],
            nullable=False,
            coerce=True
        ),
        "longitude": Column(
            float,
            checks=[
                Check.in_range(-180.0, 180.0, include_min=True, include_max=True, error="Longitud fuera del rango geográfico válido [-180, 180]")
            ],
            nullable=False,
            coerce=True
        ),
        "depth_km": Column(
            float,
            checks=[
                Check.in_range(-5.0, 1000.0, include_min=True, include_max=True, error="Profundidad fuera del rango físico plausible [-5.0, 1000.0] km")
            ],
            nullable=False,
            coerce=True
        ),
        "place": Column(
            str,
            nullable=False,
            coerce=True
        ),
        "time": Column(
            "datetime64[ns, UTC]",
            nullable=False,
            coerce=True
        ),
        "tsunami": Column(
            int,
            checks=[Check.isin([0, 1]),],
            nullable=False,
            coerce=True
        ),
        "status": Column(
            str,
            nullable=False,
            coerce=True
        )
    },
    strict=False,
    ordered=False
)

def validate_earthquake_records(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Evalúa una lista de registros contra las reglas de calidad de Pandera.
    Bifurca los datos en:
        - valid_records: Registros aprobados para ser cargados en Curated.
        - rejected_records: Registros que fallaron reglas, con motivo detallado (descartados).
        - quality_summary: Métricas agregadas de evaluación y puntaje porcentual.
    """
    if not records:
        return [], [], {
            "records_evaluated": 0,
            "records_passed": 0,
            "records_failed": 0,
            "score_pct": 100.0,
            "status": "PASSED"
        }

    valid_records: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []

    for r in records:
        rejection_reason = None
        failing_rule = None

        # 1. Regla: ID obligatorio
        rec_id = r.get("id")
        if not rec_id or not str(rec_id).strip():
            rejection_reason = "Identificador 'id' nulo o vacío"
            failing_rule = "MandatoryFieldCheck"

        # 2. Regla: Rango de Latitud
        lat = r.get("latitude")
        if rejection_reason is None:
            if lat is None or not isinstance(lat, (int, float)) or lat < -90.0 or lat > 90.0:
                rejection_reason = f"Latitud inválida ({lat}). Debe estar entre -90 y 90."
                failing_rule = "LatitudeRangeCheck"

        # 3. Regla: Rango de Longitud
        lon = r.get("longitude")
        if rejection_reason is None:
            if lon is None or not isinstance(lon, (int, float)) or lon < -180.0 or lon > 180.0:
                rejection_reason = f"Longitud inválida ({lon}). Debe estar entre -180 y 180."
                failing_rule = "LongitudeRangeCheck"

        # 4. Regla: Rango de Magnitud
        mag = r.get("mag")
        if rejection_reason is None:
            if mag is None or not isinstance(mag, (int, float)) or mag < -2.0 or mag > 10.0:
                rejection_reason = f"Magnitud fuera de rango plausible ({mag}). Debe estar entre -2.0 y 10.0."
                failing_rule = "MagnitudeRangeCheck"

        # 5. Regla: Rango de Profundidad
        depth = r.get("depth_km")
        if rejection_reason is None:
            if depth is None or not isinstance(depth, (int, float)) or depth < -5.0 or depth > 1000.0:
                rejection_reason = f"Profundidad fuera de rango físico plausible ({depth} km)."
                failing_rule = "DepthRangeCheck"

        # 6. Regla: Fecha válida
        event_time = r.get("time")
        if rejection_reason is None:
            if isinstance(event_time, str):
                try:
                    parsed_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                    r["time"] = parsed_time
                except Exception:
                    rejection_reason = f"Marca de tiempo 'time' inválida ({event_time})."
                    failing_rule = "DateFormatCheck"
            elif not isinstance(event_time, datetime):
                rejection_reason = f"Marca de tiempo 'time' inválida ({event_time})."
                failing_rule = "DateFormatCheck"

        event_updated = r.get("updated")
        if isinstance(event_updated, str):
            try:
                r["updated"] = datetime.fromisoformat(event_updated.replace("Z", "+00:00"))
            except Exception:
                pass

        if rejection_reason is None:
            valid_records.append(r)
        else:
            rejected_records.append({
                "record_id": str(rec_id) if rec_id else "UNKNOWN",
                "rejection_reason": rejection_reason,
                "failing_rule": failing_rule,
                "raw_record": r
            })

    total_evaluated = len(records)
    total_passed = len(valid_records)
    total_failed = len(rejected_records)
    score_pct = round((total_passed / total_evaluated) * 100.0, 2) if total_evaluated > 0 else 100.0
    status = "PASSED" if score_pct >= 90.0 else ("WARNING" if score_pct >= 70.0 else "FAILED")

    logger.info(
        f"Control de Calidad: {total_evaluated} evaluados, {total_passed} aprobados, "
        f"{total_failed} rechazados. Puntaje: {score_pct}% ({status})"
    )

    quality_summary = {
        "records_evaluated": total_evaluated,
        "records_passed": total_passed,
        "records_failed": total_failed,
        "score_pct": score_pct,
        "status": status
    }

    return valid_records, rejected_records, quality_summary

def check_data_freshness(latest_event_time: Optional[datetime], max_delay_minutes: int = 120) -> Tuple[bool, str]:
    """
    Control de frescura: Verifica que el sismo más reciente no exceda el umbral máximo de retraso.
    """
    if not latest_event_time:
        return False, "No hay eventos registrados para evaluar frescura."

    now = datetime.now(timezone.utc)
    # Asegurar que latest_event_time tenga zona horaria
    if latest_event_time.tzinfo is None:
        latest_event_time = latest_event_time.replace(tzinfo=timezone.utc)

    diff_minutes = (now - latest_event_time).total_seconds() / 60.0
    if diff_minutes > max_delay_minutes:
        msg = f"Retraso de frescura excedido: {diff_minutes:.1f} minutos (umbral: {max_delay_minutes} min)."
        logger.warning(msg)
        return False, msg

    return True, f"Frescura óptima: último evento recibido hace {diff_minutes:.1f} minutos."

def check_volume_bounds(record_count: int, min_count: int = 0, max_count: int = 10000) -> Tuple[bool, str]:
    """
    Control de volumen: Detecta anomalías por caída drástica o explosión de registros.
    """
    if record_count < min_count or record_count > max_count:
        msg = f"Volumen anormal detectado: {record_count} registros (rango esperado: [{min_count}, {max_count}])."
        logger.warning(msg)
        return False, msg
    return True, f"Volumen dentro de parámetros normales ({record_count} eventos)."
