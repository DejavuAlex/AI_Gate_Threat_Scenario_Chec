import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import api as api_module
from backend.app.main import app
from backend.app.services import review as review_module
from backend.app.services.documents import read_documents
from backend.app.services.knowledge_base import KnowledgeBaseService
from backend.app.services.matching import MatchingEngine


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads(
    (ROOT / "tests" / "fixtures" / "synthetic-e2e-scenarios.json").read_text(encoding="utf-8")
)
CASES = MANIFEST["scenarios"]
CLIENT = TestClient(app)


def _ids(review: dict) -> set[str]:
    return {item["scenario_id"] for item in review.get("matched_scenarios", [])}


def _wait_for_auto_gate2(task_id: str, timeout: float = 3.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = CLIENT.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200, response.text
        task = response.json()
        status = (task.get("auto_gate2") or {}).get("status")
        if status in {"completed", "failed", "skipped_no_security_risk"}:
            return task
        time.sleep(0.02)
    pytest.fail(f"auto Gate2 did not reach a terminal state for {task_id}")


@pytest.fixture
def isolated_workflow_storage(tmp_path, monkeypatch):
    paths = {
        "REPO_ROOT": tmp_path,
        "REPORTS_DIR": tmp_path / "reports",
        "REVIEWS_DIR": tmp_path / "data" / "reviews",
        "TASKS_DIR": tmp_path / "data" / "tasks",
        "TASK_SEQUENCE_FILE": tmp_path / "data" / "task_sequence.json",
        "WORK_ORDERS_DIR": tmp_path / "data" / "work_orders",
    }
    for name, path in paths.items():
        monkeypatch.setattr(review_module, name, path)
        if name not in {"REPO_ROOT", "TASK_SEQUENCE_FILE"}:
            path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_module.review_service.llm_matching.client, "enabled", False)
    yield


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["slug"])
def test_full_gate1_approval_auto_gate2_workflow(case, isolated_workflow_storage):
    payload = {
        "project_id": f"synthetic-e2e-{case['slug']}",
        "product_name": case["product_name"],
        "product_version": "e2e-1.0.0",
        "task_id": f"synthetic-e2e-{case['slug']}",
        "task_name": f"Synthetic E2E {case['slug']}",
        "repository": "synthetic/ai-gate-e2e",
        "branch": "test-fixtures",
        "documents": case["gate1_documents"],
        "gate2_documents": case["gate2_documents"],
        "knowledge_base_id": case["knowledge_base_id"],
        "gate2_knowledge_base_id": case["knowledge_base_id"],
        "threshold": MANIFEST["threshold"],
        "triggered_by": "pytest-e2e",
        "auto_run_gate2_on_gate1_approval": True,
    }

    gate1_response = CLIENT.post("/api/v1/ui/security-review/gate1/run", json=payload)
    assert gate1_response.status_code == 200, gate1_response.text
    gate1 = gate1_response.json()
    assert gate1["gate"] == "gate1"
    assert gate1["matched"] is True
    assert gate1["approval_status"] == "pending"
    assert gate1["knowledge_base_id"] == case["knowledge_base_id"]
    assert _ids(gate1) == set(case["expected_gate1_scenarios"])
    assert all(item["final_score"] >= MANIFEST["threshold"] for item in gate1["matched_scenarios"])

    source_text = "\n".join(document["content"] for document in gate1["documents"])
    for matched in gate1["match_result"]["matched_scenarios"]:
        assert matched["matched_evidence"]
        assert all(evidence in source_text for evidence in matched["matched_evidence"])

    approve_response = CLIENT.post(
        f"/api/v1/reports/{gate1['review_id']}/approve",
        json={"reviewer": "synthetic-e2e@example.invalid", "comment": "Automated E2E approval"},
    )
    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["auto_gate2_triggered"] is True

    task = _wait_for_auto_gate2(gate1["task_id"])
    assert task["auto_gate2"]["status"] == "completed", task["auto_gate2"].get("error")
    assert task["flow_status"] == "gate2_completed"
    assert task["gate2_knowledge_base_id"] == case["knowledge_base_id"]
    gate2_review_id = task["auto_gate2"]["gate2_review_id"]

    gate2_response = CLIENT.get(f"/api/v1/security-review/gate2/{gate2_review_id}")
    assert gate2_response.status_code == 200, gate2_response.text
    gate2 = gate2_response.json()
    assert gate2["gate"] == "gate2"
    assert gate2["task_id"] == gate1["task_id"]
    assert gate2["matched"] is True
    assert gate2["knowledge_base_id"] == case["knowledge_base_id"]
    assert gate2["request"]["knowledge_base_id"] == case["knowledge_base_id"]
    assert gate2["request"]["triggered_by"] == "auto-after-gate1-approval"
    assert gate2["request"]["gate1_report"] == gate1["report_path"]
    assert _ids(gate2) == set(case["expected_gate2_scenarios"])
    assert all(item["final_score"] >= MANIFEST["threshold"] for item in gate2["matched_scenarios"])

    verification = gate2["gate1_control_verification"]
    assert verification["baseline_available"] is True
    assert verification["documented"] == case["expected_gate1_control_count"]
    assert verification["partial"] == 0
    assert verification["no_evidence"] == 0

    gate1_report = CLIENT.get(gate1["report_url"])
    gate1_download = CLIENT.get(gate1["report_download_url"])
    gate2_report = CLIENT.get(gate2["report_url"])
    gate2_download = CLIENT.get(gate2["report_download_url"])
    assert gate1_report.status_code == gate1_download.status_code == 200
    assert gate2_report.status_code == gate2_download.status_code == 200
    assert gate1_report.text == gate1_download.text
    assert gate2_report.text == gate2_download.text
    assert f"Knowledge Base ID: {case['knowledge_base_id']}" in gate1_report.text
    assert f"Knowledge Base ID: {case['knowledge_base_id']}" in gate2_report.text
    assert set(case["expected_gate1_scenarios"]).issubset(set(gate1_report.text.split()))
    assert set(case["expected_gate2_scenarios"]).issubset(set(gate2_report.text.split()))

    work_orders = CLIENT.get("/api/v1/work-orders", params={"task_id": gate1["task_id"]})
    assert work_orders.status_code == 200
    assert {item["gate"] for item in work_orders.json()["items"]} == {"gate1", "gate2"}

    final_report = CLIENT.get(f"/api/v1/tasks/{gate1['task_id']}/final-report")
    assert final_report.status_code == 200
    assert gate1["review_id"] in final_report.text
    assert gate2["review_id"] in final_report.text

    duplicate_approval = CLIENT.post(
        f"/api/v1/reports/{gate1['review_id']}/approve",
        json={"reviewer": "synthetic-e2e@example.invalid", "comment": "Duplicate approval check"},
    )
    assert duplicate_approval.status_code == 200
    assert duplicate_approval.json()["auto_gate2_triggered"] is False
    work_orders_after_duplicate = CLIENT.get("/api/v1/work-orders", params={"task_id": gate1["task_id"]})
    assert len(work_orders_after_duplicate.json()["items"]) == 2


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["slug"])
def test_negative_control_has_no_false_positive(case):
    service = KnowledgeBaseService()
    for gate in ("gate1", "gate2"):
        knowledge_base = service.load(gate, case["knowledge_base_id"])
        document_text, _ = read_documents(MANIFEST[f"negative_{gate}_documents"])
        result = MatchingEngine(knowledge_base, MANIFEST["threshold"]).match(document_text, gate)
        assert result["matched"] is False
        assert result["matched_scenarios"] == []


def test_synthetic_knowledge_bases_have_unique_ids_and_gate2_mapping():
    service = KnowledgeBaseService()
    for case in CASES:
        gate1 = service.load("gate1", case["knowledge_base_id"])
        gate2 = service.load("gate2", case["knowledge_base_id"])
        gate1_ids = [scenario["id"] for scenario in gate1["scenarios"]]
        gate2_ids = [scenario["id"] for scenario in gate2["scenarios"]]
        assert len(gate1_ids) == len(set(gate1_ids))
        assert len(gate2_ids) == len(set(gate2_ids))
        assert set(gate1_ids) == set(case["expected_gate1_scenarios"])
        assert set(gate2_ids) == set(case["expected_gate2_scenarios"])
        assert {scenario["mapped_gate1_scenario_id"] for scenario in gate2["scenarios"]} == set(gate1_ids)
