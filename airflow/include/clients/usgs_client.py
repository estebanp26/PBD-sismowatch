"""
SismoWatch - Cliente USGS
Extracción automática, tipada y resiliente de datos sísmicos desde el USGS Earthquake Catalog.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

class USGSClient:
    """Cliente HTTP con reintentos y retroceso exponencial para la API de USGS."""

    def __init__(self, timeout: int = 15, max_retries: int = 3, backoff_factor: float = 1.5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "SismoWatch-DataPlatform/1.0 (EmergencyMonitoringBot; contact=risk@sismowatch.internal)",
            "Accept": "application/json"
        })

    def fetch_realtime_feed(self, url: str) -> Tuple[Dict[str, Any], str, int]:
        """
        Consulta el feed GeoJSON de última hora de la USGS.
        Retorna:
            (payload_dict, payload_hash_md5, total_events)
        """
        return self._fetch_with_retries(url)

    def fetch_historical_query(
        self,
        base_url: str,
        start_date: str,
        end_date: str,
        min_magnitude: float = 2.5
    ) -> Tuple[Dict[str, Any], str, int]:
        """
        Consulta el endpoint de búsqueda histórica de la USGS con parámetros.
        """
        params = {
            "format": "geojson",
            "starttime": start_date,
            "endtime": end_date,
            "minmagnitude": min_magnitude,
            "orderby": "time-asc"
        }
        return self._fetch_with_retries(base_url, params=params)

    def _fetch_with_retries(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], str, int]:
        """Realiza llamada HTTP con reintentos exponenciales y validación estructural mínima."""
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Iniciando solicitud a USGS (intento {attempt}/{self.max_retries}): {url}")
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()

                data = response.json()
                if not isinstance(data, dict) or "features" not in data:
                    raise ValueError("El payload retornado por USGS no es un GeoJSON válido con clave 'features'.")

                # Cálculo de hash criptográfico inmutable para idempotencia
                raw_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
                payload_hash = hashlib.sha256(raw_bytes).hexdigest()
                event_count = len(data.get("features", []))

                logger.info(f"Respuesta USGS recibida exitosamente: {event_count} eventos, hash: {payload_hash[:12]}...")
                return data, payload_hash, event_count

            except (requests.RequestException, ValueError, json.JSONDecodeError) as ex:
                last_exception = ex
                logger.warning(f"Fallo en llamada a USGS en intento {attempt}: {str(ex)}")
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor ** attempt
                    time.sleep(sleep_time)

        error_msg = f"Agotados los {self.max_retries} intentos de consulta a USGS. Causa raíz: {last_exception}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from last_exception
