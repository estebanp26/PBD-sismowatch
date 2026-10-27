"""
SismoWatch - Fixtures y Configuración de Pruebas Pytest
"""

import sys
import os
import pytest

# Agregar directorios del proyecto al sys.path para importación limpia
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIRFLOW_DIR = os.path.join(BASE_DIR, "airflow")
API_DIR = os.path.join(BASE_DIR, "api")

for p in (BASE_DIR, AIRFLOW_DIR, API_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

@pytest.fixture
def sample_geojson_feature():
    """Retorna un evento GeoJSON de USGS válido para pruebas unitarias."""
    return {
        "type": "Feature",
        "properties": {
            "mag": 5.8,
            "place": "85 km SW of San Pedro de Atacama, Chile",
            "time": 1700000000000,
            "updated": 1700003600000,
            "tz": -180,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000test",
            "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/us7000test.geojson",
            "felt": 12,
            "cdi": 4.5,
            "mmi": 5.2,
            "alert": "green",
            "status": "reviewed",
            "tsunami": 0,
            "sig": 518,
            "net": "us",
            "code": "7000test",
            "ids": ",us7000test,",
            "sources": ",us,",
            "types": ",origin,phase-data,",
            "nst": 42,
            "dmin": 0.85,
            "rms": 0.72,
            "gap": 45.0,
            "magType": "mww",
            "type": "earthquake",
            "title": "M 5.8 - 85 km SW of San Pedro de Atacama, Chile"
        },
        "geometry": {
            "type": "Point",
            "coordinates": [-68.75, -23.45, 112.5]  # [longitud, latitud, profundidad_km]
        },
        "id": "us7000test"
    }

@pytest.fixture
def invalid_geojson_feature():
    """Retorna un evento GeoJSON con coordenadas anómalas fuera de límites geográficos."""
    return {
        "type": "Feature",
        "properties": {
            "mag": -15.0,  # Magnitud imposible
            "place": "Anomalous Zone",
            "time": 1700000000000,
            "status": "automatic",
            "tsunami": 0
        },
        "geometry": {
            "type": "Point",
            "coordinates": [999.0, 500.0, -100.0]  # Latitud > 90, Longitud > 180, Profundidad negativa anómala
        },
        "id": "us_invalid_01"
    }
