from fastapi.testclient import TestClient

from backend.app import config
from backend.app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_gate1_knowledge_base():
    response = client.get("/api/v1/knowledge-base/gate1")
    assert response.status_code == 200
    body = response.json()
    assert body["gate"] == "Gate1"
    assert body["llm_editable"] is False


def test_api_key_is_required_when_configured(monkeypatch):
    monkeypatch.setattr(config, "AI_SECURITY_GATE_API_KEY", "test-api-key")
    response = client.get("/api/v1/health")
    assert response.status_code == 401

    response = client.get("/api/v1/health", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 200

    response = client.get("/api/v1/health", headers={"Authorization": "Bearer test-api-key"})
    assert response.status_code == 200

    monkeypatch.setattr(config, "AI_SECURITY_GATE_API_KEY", "")
