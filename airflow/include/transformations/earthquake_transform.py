"""
SismoWatch - Módulo de Transformación de Datos Sísmicos
Funciones puras y deterministas para convertir eventos GeoJSON de USGS al esquema Staging.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def epoch_ms_to_datetime(epoch_ms: Optional[int]) -> Optional[datetime]:
    """Convierte milisegundos de época a objeto datetime UTC consciente de zona horaria."""
    if epoch_ms is None:
        return None
    try:
        return datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None

def transform_geojson_feature_to_staging(feature: Dict[str, Any], raw_reference_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Transforma un objeto individual 'feature' de un GeoJSON de USGS a un diccionario compatible con Staging.
    
    Lanza ValueError si el evento carece de identificador único o coordenadas.
    """
    if not isinstance(feature, dict):
        raise ValueError("El evento suministrado no es un diccionario válido.")

    record_id = feature.get("id")
    if not record_id or not str(record_id).strip():
        raise ValueError("El evento GeoJSON carece de identificador ('id').")

    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates")
    if not coordinates or not isinstance(coordinates, (list, tuple)) or len(coordinates) < 3:
        raise ValueError(f"Coordenadas inválidas o ausentes para el evento {record_id}.")

    props = feature.get("properties") or {}

    # Extracción de coordenadas GeoJSON: [longitud, latitud, profundidad_km]
    try:
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
        depth_km = float(coordinates[2])
    except (ValueError, TypeError) as e:
        raise ValueError(f"Error parseando coordenadas numéricas en evento {record_id}: {e}")

    # Parseo de marcas de tiempo
    event_time = epoch_ms_to_datetime(props.get("time"))
    if not event_time:
        raise ValueError(f"Marca temporal 'time' inválida o ausente en evento {record_id}.")

    updated_time = epoch_ms_to_datetime(props.get("updated")) or event_time

    # Manejo de magnitud
    raw_mag = props.get("mag")
    mag = float(raw_mag) if raw_mag is not None else 0.0

    return {
        "id": str(record_id).strip(),
        "mag": round(mag, 2),
        "place": str(props.get("place") or "Ubicación no especificada").strip(),
        "time": event_time,
        "updated": updated_time,
        "tz": props.get("tz"),
        "url": props.get("url") or "",
        "detail": props.get("detail") or "",
        "felt": props.get("felt"),
        "cdi": float(props["cdi"]) if props.get("cdi") is not None else None,
        "mmi": float(props["mmi"]) if props.get("mmi") is not None else None,
        "alert": props.get("alert"),
        "status": str(props.get("status") or "automatic").strip().lower(),
        "tsunami": int(props.get("tsunami") or 0),
        "sig": int(props.get("sig") or 0),
        "net": props.get("net") or "",
        "code": props.get("code") or "",
        "ids": props.get("ids") or "",
        "sources": props.get("sources") or "",
        "types": props.get("types") or "",
        "nst": props.get("nst"),
        "dmin": float(props["dmin"]) if props.get("dmin") is not None else None,
        "rms": float(props["rms"]) if props.get("rms") is not None else None,
        "gap": float(props["gap"]) if props.get("gap") is not None else None,
        "mag_type": str(props.get("magType") or "unknown").strip().lower(),
        "type": str(props.get("type") or "earthquake").strip().lower(),
        "title": str(props.get("title") or f"M {round(mag, 2)} - {props.get('place')}").strip(),
        "longitude": longitude,
        "latitude": latitude,
        "depth_km": depth_km,
        "raw_reference_id": raw_reference_id
    }

def transform_geojson_payload(payload: Dict[str, Any], raw_reference_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Transforma una colección completa de features de un GeoJSON de USGS.
    Retorna la lista de registros transformados en formato staging.
    """
    features = payload.get("features", [])
    transformed_records = []

    for feat in features:
        try:
            record = transform_geojson_feature_to_staging(feat, raw_reference_id=raw_reference_id)
            transformed_records.append(record)
        except ValueError as ex:
            logger.warning(f"Omitiendo feature inválido durante la transformación: {ex}")

    logger.info(f"Transformados exitosamente {len(transformed_records)} de {len(features)} eventos del GeoJSON.")
    return transformed_records
