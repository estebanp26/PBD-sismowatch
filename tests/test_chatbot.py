"""
Pruebas Automatizadas para el Chatbot Analítico de IA (SismoWatch)
Valida autenticación RBAC, motor híbrido, caché en memoria, sanitización y respuestas.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.core.security import get_current_user
from app.db.session import get_db
from app.services.chatbot_service import ChatbotService, sanitize_user_input, global_chat_cache

class MockChatDB:
    """Mock de sesión SQLAlchemy para pruebas unitarias rápidas del chatbot."""
    def execute(self, query, params=None):
        mock_result = MagicMock()
        q_str = str(query).lower()
        if "silver_count" in q_str:
            mock_result.fetchone.return_value = (1990, 1995, 12)
        elif "curated.data_quality_runs" in q_str:
            mock_result.fetchall.return_value = [
                ("2026-10-27 15:00:00", 50, 49, 1, 98.0, "PASSED")
            ]
        elif "tsunami = 1" in q_str:
            mock_result.fetchall.return_value = []
        elif "curated.ai_executive_reports" in q_str:
            mock_result.fetchone.return_value = (
                "2026-10-27", "Informe Ejecutivo de Actividad Sísmica", "Resumen de prueba de IA", [], {}
            )
        else:
            mock_result.fetchall.return_value = [
                ("us7000m1a1", 6.8, "Sendai, Japan", "2026-10-27 12:00:00", 35.0, 0)
            ]
            mock_result.fetchone.return_value = (1995, 3.2, 7.7, 45.0, 5.0, 650.0)
        return mock_result

def override_get_db():
    yield MockChatDB()

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

def test_unauthenticated_chat_query_returns_401(client):
    """Verifica que una consulta al chatbot sin token JWT sea rechazada con 401."""
    res = client.post("/api/chat/query", json={"message": "Hola"})
    assert res.status_code == 401

def test_viewer_can_query_chatbot(client):
    """Verifica que un usuario con rol 'viewer' pueda consultar al asistente y recibir respuesta tipada."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 2, "username": "viewer", "role": "viewer", "is_active": True
    }
    res = client.post(
        "/api/chat/query",
        json={"message": "¿Cuáles son los 5 sismos más fuertes?"},
        headers={"Authorization": "Bearer fake_token"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "execution_time_ms" in data
    assert "source_layer" in data
    assert data["execution_time_ms"] >= 0

def test_chat_suggestions_endpoint(client):
    """Verifica que el endpoint /api/chat/suggestions devuelva preguntas de ejemplo."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 2, "username": "viewer", "role": "viewer", "is_active": True
    }
    res = client.get(
        "/api/chat/suggestions",
        headers={"Authorization": "Bearer fake_token"}
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 4

def test_chatbot_sanitization_removes_malicious_commands():
    """Valida que comandos de inyección como DROP TABLE sean neutralizados."""
    raw = "Hola; DROP TABLE curated.earthquake_events; SELECT * FROM staging;"
    cleaned = sanitize_user_input(raw)
    assert "DROP TABLE" not in cleaned
    assert "[FILTRADO]" in cleaned

def test_chatbot_in_memory_cache():
    """Valida que la caché en memoria almacene y devuelva resultados con flag cached=True."""
    global_chat_cache.clear()
    db = MockChatDB()
    msg = "¿cuántos sismos hay en silver vs gold?"
    
    # Primera consulta (calculada)
    res1 = ChatbotService.process_query(msg, db)
    assert res1["cached"] is False
    
    # Segunda consulta (desde caché)
    res2 = ChatbotService.process_query(msg, db)
    assert res2["cached"] is True
    assert res2["execution_time_ms"] < 10.0
