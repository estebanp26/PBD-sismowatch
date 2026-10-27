"""
Pruebas de Calidad de Datos: Reglas Pandera, Enrutamiento a Cuarentena y Controles de Frescura
"""

from datetime import datetime, timezone, timedelta
import pytest
from include.transformations.earthquake_transform import transform_geojson_feature_to_staging
from include.quality.validation_rules import (
    validate_earthquake_records,
    check_data_freshness,
    check_volume_bounds
)

def test_valid_record_passes_quality_gate(sample_geojson_feature):
    """Verifica que un registro conforme pase la compuerta de calidad con 100% de puntaje."""
    valid_row = transform_geojson_feature_to_staging(sample_geojson_feature)
    valid_list, rejected_list, summary = validate_earthquake_records([valid_row])

    assert len(valid_list) == 1
    assert len(rejected_list) == 0
    assert summary["records_evaluated"] == 1
    assert summary["records_passed"] == 1
    assert summary["records_failed"] == 0
    assert summary["score_pct"] == 100.0
    assert summary["status"] == "PASSED"

def test_invalid_latitude_is_rejected_and_discarded(sample_geojson_feature):
    """Verifica que un registro con latitud fuera de rango (-90 a 90) sea rechazado y descartado con motivo claro."""
    row = transform_geojson_feature_to_staging(sample_geojson_feature)
    row["latitude"] = 125.5  # Latitud imposible en el planeta Tierra

    valid_list, rejected_list, summary = validate_earthquake_records([row])

    assert len(valid_list) == 0
    assert len(rejected_list) == 1
    assert summary["records_passed"] == 0
    assert summary["records_failed"] == 1
    assert summary["score_pct"] == 0.0

    rejected_item = rejected_list[0]
    assert rejected_item["record_id"] == "us7000test"
    assert "Latitud inválida" in rejected_item["rejection_reason"]
    assert rejected_item["failing_rule"] == "LatitudeRangeCheck"

def test_invalid_magnitude_is_rejected_and_discarded(sample_geojson_feature):
    """Verifica que un registro con magnitud absurda sea rechazado y descartado."""
    row = transform_geojson_feature_to_staging(sample_geojson_feature)
    row["mag"] = 18.5  # Magnitud destructora planetaria imposible en escala Richter/Momento

    valid_list, rejected_list, summary = validate_earthquake_records([row])

    assert len(valid_list) == 0
    assert len(rejected_list) == 1
    assert "Magnitud fuera de rango" in rejected_list[0]["rejection_reason"]

def test_data_freshness_check():
    """Verifica que eventos recientes pasen y eventos antiguos disparen alerta de frescura."""
    now = datetime.now(timezone.utc)
    fresh_time = now - timedelta(minutes=15)
    stale_time = now - timedelta(minutes=240)

    is_fresh, msg_fresh = check_data_freshness(fresh_time, max_delay_minutes=60)
    assert is_fresh is True
    assert "óptima" in msg_fresh.lower()

    is_stale, msg_stale = check_data_freshness(stale_time, max_delay_minutes=60)
    assert is_stale is False
    assert "excedido" in msg_stale.lower()

def test_volume_bounds_check():
    """Verifica la detección de anomalías por conteo de eventos fuera de umbrales."""
    ok, _ = check_volume_bounds(record_count=120, min_count=1, max_count=5000)
    assert ok is True

    anomaly, _ = check_volume_bounds(record_count=15000, min_count=1, max_count=5000)
    assert anomaly is False

def test_mixed_batch_filters_bad_records_without_crashing(sample_geojson_feature):
    """Verifica que un lote con datos válidos y datos corruptos filtre los malos y conserve los buenos sin romper el flujo."""
    good_row = transform_geojson_feature_to_staging(sample_geojson_feature)
    bad_row_1 = dict(good_row)
    bad_row_1["id"] = "bad_mag"
    bad_row_1["mag"] = 55.0  # Magnitud absurda

    bad_row_2 = dict(good_row)
    bad_row_2["id"] = "bad_lat"
    bad_row_2["latitude"] = -150.0  # Latitud fuera de [-90, 90]

    batch = [good_row, bad_row_1, bad_row_2]
    valid_list, rejected_list, summary = validate_earthquake_records(batch)

    assert len(valid_list) == 1
    assert valid_list[0]["id"] == "us7000test"
    assert len(rejected_list) == 2
    assert summary["records_evaluated"] == 3
    assert summary["records_passed"] == 1
    assert summary["records_failed"] == 2
    assert summary["status"] == "FAILED"  # Score < 70%, pero el pipeline maneja el descarte sin crash

