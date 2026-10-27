"""
Pruebas Unitarias: Transformación de Datos Sísmicos GeoJSON -> Staging
"""

from datetime import datetime, timezone
import pytest
from include.transformations.earthquake_transform import (
    transform_geojson_feature_to_staging,
    epoch_ms_to_datetime
)

def test_epoch_ms_to_datetime_conversion():
    """Valida que los milisegundos epoch se conviertan con precisión a datetime UTC."""
    epoch_ms = 1700000000000  # 2023-11-14 22:13:20 UTC
    dt = epoch_ms_to_datetime(epoch_ms)
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.year == 2023
    assert dt.month == 11
    assert dt.day == 14

def test_transform_valid_geojson_feature(sample_geojson_feature):
    """Verifica que un evento GeoJSON válido se aplane y tipifique correctamente para Staging."""
    staging_row = transform_geojson_feature_to_staging(sample_geojson_feature, raw_reference_id=42)

    assert staging_row["id"] == "us7000test"
    assert staging_row["mag"] == 5.8
    assert staging_row["longitude"] == -68.75
    assert staging_row["latitude"] == -23.45
    assert staging_row["depth_km"] == 112.5
    assert staging_row["place"] == "85 km SW of San Pedro de Atacama, Chile"
    assert staging_row["status"] == "reviewed"
    assert staging_row["tsunami"] == 0
    assert staging_row["raw_reference_id"] == 42
    assert isinstance(staging_row["time"], datetime)
    assert staging_row["time"].tzinfo == timezone.utc

def test_transform_feature_missing_id():
    """Verifica que un evento sin 'id' lance ValueError de forma explícita."""
    malformed_feature = {
        "type": "Feature",
        "properties": {"mag": 3.2},
        "geometry": {"type": "Point", "coordinates": [-70.0, -30.0, 10.0]}
    }
    with pytest.raises(ValueError, match="carece de identificador"):
        transform_geojson_feature_to_staging(malformed_feature)

def test_transform_feature_missing_coordinates():
    """Verifica que un evento sin coordenadas completas lance ValueError."""
    feature_no_coords = {
        "id": "missing_coords_01",
        "type": "Feature",
        "properties": {"mag": 4.1},
        "geometry": {"type": "Point", "coordinates": []}
    }
    with pytest.raises(ValueError, match="Coordenadas inválidas o ausentes"):
        transform_geojson_feature_to_staging(feature_no_coords)
