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


def test_external_task_submission_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(config, "AI_SECURITY_GATE_API_KEY", "test-api-key")

    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/knowledge-base/gate1").status_code == 200

    response = client.post("/api/v1/security-review/gate1/run", json={})
    assert response.status_code == 401

    response = client.post("/api/v1/security-review/gate1/run", json={}, headers={"X-API-Key": "wrong"})
    assert response.status_code == 401

    monkeypatch.setattr(config, "AI_SECURITY_GATE_API_KEY", "")
