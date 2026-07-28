import json

from fastapi.testclient import TestClient

from backend.app import config
from backend.app.main import app
from backend.app.services import knowledge_base as knowledge_base_module


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


def test_upload_and_select_classified_knowledge_base(tmp_path, monkeypatch):
    kb_root = tmp_path / "knowledge_base"
    history_root = tmp_path / "knowledge_base_history"
    monkeypatch.setattr(knowledge_base_module, "KNOWLEDGE_BASE_DIR", kb_root)
    monkeypatch.setattr(knowledge_base_module, "KB_HISTORY_DIR", history_root)
    content = {
        "schema_version": "1.0.0",
        "knowledge_base_version": "0.1.0",
        "gate": "Gate1",
        "name": "Uploaded Cloud KB",
        "scenarios": [
            {
                "id": "CLOUD-001",
                "name": "Cloud Object Storage Upload",
                "problem_scenario": "Does the service upload files to cloud storage?",
                "category": "Cloud Service",
                "risk": {"level": "Yellow"},
                "risk_identification": ["Unsafe cloud object upload"],
                "security_control_requirements": ["Validate object type"],
            }
        ],
    }

    response = client.post(
        "/api/v1/knowledge-base/gate1/upload",
        data={
            "knowledge_base_id": "cloud-service",
            "updated_by": "pytest@example.com",
            "change_reason": "upload from test",
            "version": "1.2.3",
            "name": "Cloud Service KB",
            "category": "Cloud Service",
            "risk_level": "Yellow",
            "description": "Cloud service golden KB",
        },
        files={"file": ("cloud.json", json.dumps(content).encode("utf-8"), "application/json")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["item"]["knowledge_base_id"] == "cloud-service"
    assert body["item"]["category"] == "Cloud Service"
    assert body["item"]["risk_level"] == "Yellow"

    load_response = client.get("/api/v1/knowledge-base/gate1", params={"knowledge_base_id": "cloud-service"})
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["metadata"]["knowledge_base_id"] == "cloud-service"
    assert loaded["knowledge_base_version"] == "1.2.3"

    catalog_response = client.get("/api/v1/knowledge-base/gate1/catalog")
    assert catalog_response.status_code == 200
    assert catalog_response.json()["items"][0]["knowledge_base_id"] == "cloud-service"

    history_response = client.get("/api/v1/knowledge-base/gate1/history", params={"knowledge_base_id": "cloud-service"})
    assert history_response.status_code == 200
    assert history_response.json()["items"][0]["knowledge_base_id"] == "cloud-service"
