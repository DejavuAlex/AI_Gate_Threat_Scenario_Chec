import json

from fastapi.testclient import TestClient

from backend.app import api as api_module
from backend.app.main import app
from backend.app.services import knowledge_base as knowledge_base_module
from backend.app.services.knowledge_base_assistant import KnowledgeBaseAssistantService


def sample_knowledge_base():
    return {
        "knowledge_base_version": "1.0.0",
        "gate": "Gate1",
        "name": "Test KB",
        "scenarios": [
            {
                "id": "TEST-001",
                "name": "Existing upload scenario",
                "problem_scenario": "Are files uploaded?",
                "category": "File Upload",
                "business_indicators": ["file upload"],
                "negative_indicators": ["upload disabled"],
                "risk": {"P1": 6, "P2": 5, "P": 3, "severity": 8, "level": "Yellow"},
                "risk_identification": ["Malicious file upload"],
                "security_control_requirements": ["Validate file type"],
            }
        ],
    }


class FakeLLMClient:
    def is_available(self):
        return True

    def complete_json(self, system_prompt, payload):
        serialized_payload = json.dumps(payload, ensure_ascii=False)
        assert "severity" in system_prompt
        assert "own cybersecurity" in system_prompt
        assert payload["scenario_description"] == "Users can share external links"
        assert set(payload) == {"gate", "scenario_description", "conversation", "current_draft", "scenario_schema"}
        assert "Existing upload scenario" not in serialized_payload
        assert "TEST-001" not in serialized_payload
        assert "Malicious file upload" not in serialized_payload
        return {
            "assistant_message": "My independent assessment is P=4 and S=7.",
            "scenario": {
                "name": "External link sharing",
                "problem_scenario": "Can users share external links?",
                "category": "External Link",
                "business_indicators": ["share link", "external URL"],
                "negative_indicators": ["external links disabled"],
                "risk": {"P1": 7, "P2": 6, "P": 4, "severity": 7, "level": "Yellow"},
                "risk_identification": ["Users may be redirected to phishing content"],
                "security_control_requirements": ["Validate and label external destinations"],
            },
        }


class PartialRevisionLLMClient:
    def is_available(self):
        return True

    def complete_json(self, system_prompt, payload):
        assert payload["current_draft"]["risk"]["P"] == 4
        return {
            "assistant_message": "Severity updated to S=9.",
            "action": "add",
            "scenario": {"risk": {"severity": 9}},
        }


class UpdateAttemptLLMClient(FakeLLMClient):
    def complete_json(self, system_prompt, payload):
        result = super().complete_json(system_prompt, payload)
        result["action"] = "update"
        result["matched_scenario_id"] = "TEST-001"
        return result


def test_assistant_uses_own_knowledge_and_matches_only_the_kb_field_shape():
    service = KnowledgeBaseAssistantService(client=FakeLLMClient())

    result = service.propose("gate1", sample_knowledge_base(), "Users can share external links")

    assert result["action"] == "add"
    assert result["scenario"]["id"] == "TEST-002"
    assert set(result["scenario"]) == set(sample_knowledge_base()["scenarios"][0])
    assert result["risk_summary"] == {"P1": 7, "P2": 6, "P": 4, "S": 7, "level": "Yellow"}
    assert result["reference_scenario_ids"] == []


def test_assistant_merges_partial_follow_up_into_the_edited_draft():
    first_result = KnowledgeBaseAssistantService(client=FakeLLMClient()).propose(
        "gate1", sample_knowledge_base(), "Users can share external links"
    )
    service = KnowledgeBaseAssistantService(client=PartialRevisionLLMClient())

    revised = service.propose(
        "gate1",
        sample_knowledge_base(),
        "Set S to 9",
        draft_scenario=first_result["scenario"],
        draft_action="add",
    )

    assert revised["scenario"]["risk"]["P"] == 4
    assert revised["scenario"]["risk"]["severity"] == 9
    assert revised["scenario"]["name"] == "External link sharing"


def test_assistant_always_creates_a_new_candidate_even_if_the_model_requests_an_update():
    service = KnowledgeBaseAssistantService(client=UpdateAttemptLLMClient())

    result = service.propose("gate1", sample_knowledge_base(), "Users can share external links")

    assert result["action"] == "add"
    assert result["matched_scenario_id"] is None
    assert result["scenario"]["id"] == "TEST-002"


def test_assistant_endpoint_only_proposes_and_does_not_write_kb(tmp_path, monkeypatch):
    kb_root = tmp_path / "knowledge_base"
    kb_path = kb_root / "gate1" / "default-gate1-knowledge-base.json"
    kb_path.parent.mkdir(parents=True)
    original = json.dumps(sample_knowledge_base(), ensure_ascii=False, indent=2)
    kb_path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(knowledge_base_module, "KNOWLEDGE_BASE_DIR", kb_root)
    monkeypatch.setattr(api_module.kb_assistant_service, "client", FakeLLMClient())

    response = TestClient(app).post(
        "/api/v1/knowledge-base/gate1/assistant/propose",
        json={"knowledge_base_id": "default", "message": "Users can share external links"},
    )

    assert response.status_code == 200
    assert response.json()["scenario"]["id"] == "TEST-002"
    assert kb_path.read_text(encoding="utf-8") == original
