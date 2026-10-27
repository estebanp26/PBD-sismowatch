"""
Pruebas de API y Seguridad RBAC: Autenticación JWT y Control de Acceso por Rol (401/403)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token, get_current_user
from app.db.session import get_db

class MockDB:
    """Mock de base de datos para aislar pruebas de endpoints API."""
    def execute(self, query, params=None):
        return self

    def fetchone(self):
        # (total_24h, max_mag, avg_mag, tsunamis, latest_event)
        from datetime import datetime, timezone
        return (10, 6.2, 4.5, 1, datetime.now(timezone.utc))

    def fetchall(self):
        return []

    def scalar(self):
        return 0

def override_get_db():
    try:
        yield MockDB()
    finally:
        pass

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

def test_unauthenticated_request_returns_401(client):
    """Verifica que cualquier solicitud sin token reciba HTTP 401 Unauthorized."""
    response = client.get("/api/kpis")
    assert response.status_code == 401
    assert "Credenciales de autenticación no proporcionadas" in response.json()["detail"]

def test_viewer_can_access_kpis_and_events(client):
    """Verifica que el rol 'viewer' pueda consultar los KPIs del dashboard."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 2,
        "username": "viewer",
        "full_name": "Operador Viewer",
        "role": "viewer",
        "is_active": True
    }
    response = client.get("/api/kpis", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 200
    data = response.json()
    assert "events_last_24h" in data
    assert "quality_score" in data

def test_viewer_blocked_from_admin_backfill(client):
    """Verifica que un 'viewer' reciba HTTP 403 Forbidden al intentar lanzar un backfill."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 2,
        "username": "viewer",
        "full_name": "Operador Viewer",
        "role": "viewer",
        "is_active": True
    }
    payload = {"days_back": 15, "min_magnitude": 3.0}
    response = client.post("/api/admin/backfill", json=payload, headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 403

def test_admin_can_access_admin_endpoints(client):
    """Verifica que un 'admin' pueda acceder exitosamente a las rutas de administración (backfill)."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "username": "admin",
        "full_name": "Administrador",
        "role": "admin",
        "is_active": True
    }
    # Disparo de backfill
    b_response = client.post("/api/admin/backfill", json={"days_back": 7, "min_magnitude": 3.0}, headers={"Authorization": "Bearer fake_token"})
    assert b_response.status_code == 202

def test_health_check_public(client):
    """Verifica que el endpoint /health sea público y responda 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"

def test_lineage_endpoint_requires_auth(client):
    """Verifica que /api/metadata/lineage rechace solicitudes anónimas con 401."""
    response = client.get("/api/metadata/lineage")
    assert response.status_code == 401

def test_lineage_endpoint_returns_nodes_and_edges(client):
    """Verifica que un usuario autenticado pueda consultar el grafo de linaje de datos."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 2,
        "username": "viewer",
        "full_name": "Operador Viewer",
        "role": "viewer",
        "is_active": True
    }
    response = client.get("/api/metadata/lineage", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 200
    data = response.json()
    assert "service_name" in data
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 10
    assert len(data["edges"]) >= 10
    # Validar que contenga nodos clave de la arquitectura Medallion
    node_ids = [n["id"] for n in data["nodes"]]
    assert "source_usgs" in node_ids
    assert "lake_minio" in node_ids
    assert "table_staging" in node_ids
    assert "gate_pandera" in node_ids
    assert "table_curated" in node_ids



def test_viewer_receives_summary_pipeline_status(client):
    """Verifica que 'viewer' reciba el estado del pipeline en modo resumen (quality_rules vacío)."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 2,
        "username": "viewer",
        "full_name": "Operador Viewer",
        "role": "viewer",
        "is_active": True
    }
    response = client.get("/api/pipeline/status", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["view_mode"] == "summary"
    assert len(data["quality_rules"]) == 0

def test_admin_receives_detail_pipeline_status(client):
    """Verifica que 'admin' reciba el estado del pipeline en modo detalle."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "username": "admin",
        "full_name": "Administrador",
        "role": "admin",
        "is_active": True
    }
    response = client.get("/api/pipeline/status", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["view_mode"] == "detail"


