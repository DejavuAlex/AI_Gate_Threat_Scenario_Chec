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


def test_upload_spec_file_saves_under_specs_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SPECS_DIR", tmp_path)

    response = client.post(
        "/api/v1/specs/upload",
        files=[("files", ("../uploaded spec.md", b"# Uploaded spec\n", "text/markdown"))],
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["filename"] == "uploaded spec.md"
    assert item["path"] == "specs/uploaded spec.md"
    assert (tmp_path / "uploaded spec.md").read_text(encoding="utf-8") == "# Uploaded spec\n"

    list_response = client.get("/api/v1/specs")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["path"] == "specs/uploaded spec.md"
