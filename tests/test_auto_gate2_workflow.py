from types import SimpleNamespace

import pytest

from backend.app.services import review as review_module
from backend.app.services.llm_client import LLMClient
from backend.app.services.review import ReviewService


@pytest.fixture
def review_service(tmp_path, monkeypatch):
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
    return ReviewService()


def seed_gate1_review(service: ReviewService, *, matched: bool = True) -> tuple[str, str]:
    task_id = "task-000001"
    review_id = "gate1-review-test"
    task = {
        "task_id": task_id,
        "task_serial_no": 1,
        "task_code": "TASK-000001",
        "task_name": "Demo-v1-gate1",
        "product_name": "Demo",
        "product_version": "v1",
        "project_id": "demo",
        "status": "in_progress",
        "flow_status": "gate1_pending",
        "final_result": "pending",
        "created_at": "2026-08-17T00:00:00+00:00",
        "activities": [],
        "reviews": {"gate1": [], "gate2": []},
        "reports": {"gate1": [], "gate2": []},
        "approval": {},
        "auto_gate2": {"enabled": True, "status": "not_started"},
        "gate2_documents": ["specs/architecture.md"],
        "gate2_document_texts": [],
        "gate2_knowledge_base_id": "default",
    }
    service._store_task(task)
    review = {
        "review_id": review_id,
        "work_order_id": "task-000001-gate1-test",
        "task_id": task_id,
        "task_serial_no": 1,
        "task_code": "TASK-000001",
        "task_name": "Demo-v1-gate1",
        "project_id": "demo",
        "product_name": "Demo",
        "product_version": "v1",
        "gate": "gate1",
        "status": "completed",
        "matched": matched,
        "approval_status": "pending",
        "report_path": "reports/gate1.md",
        "created_at": "2026-08-17T00:00:00+00:00",
        "request": {
            "project_id": "demo",
            "repository": "example/demo",
            "branch": "main",
            "threshold": 0.78,
            "gate2_documents": ["specs/architecture.md"],
            "gate2_document_texts": [],
            "gate2_knowledge_base_id": "default",
            "auto_run_gate2_on_gate1_approval": True,
        },
    }
    service._store_review(review_id, review)
    return task_id, review_id


def test_gate1_approval_queues_gate2_without_running_it_inline(review_service, monkeypatch):
    task_id, review_id = seed_gate1_review(review_service)
    run_calls = []
    monkeypatch.setattr(review_service, "run", lambda *args, **kwargs: run_calls.append((args, kwargs)))

    result = review_service.approve(review_id, "reviewer@example.com")

    task = review_service.get_task(task_id)
    assert result["auto_gate2_triggered"] is True
    assert result["auto_gate2_status"] == "queued"
    assert task["auto_gate2"]["status"] == "queued"
    assert task["flow_status"] == "gate1_approved_gate2_required"
    assert run_calls == []

    duplicate = review_service.approve(review_id, "reviewer@example.com")
    assert duplicate["auto_gate2_triggered"] is False
    assert duplicate["auto_gate2_status"] == "queued"


def test_auto_gate2_records_completed_and_failed_terminal_states(review_service, monkeypatch):
    task_id, review_id = seed_gate1_review(review_service)
    review_service.approve(review_id, "reviewer@example.com")
    monkeypatch.setattr(review_service, "run", lambda gate, request: {"review_id": "gate2-review-success"})

    completed = review_service.run_auto_gate2(review_id)

    assert completed["status"] == "completed"
    task = review_service.get_task(task_id)
    assert task["auto_gate2"]["status"] == "completed"
    assert task["auto_gate2"]["gate2_review_id"] == "gate2-review-success"
    assert task["flow_status"] == "gate2_completed"

    task["latest_gate2_review_id"] = None
    task["auto_gate2"] = {
        "enabled": True,
        "status": "queued",
        "triggered_by_gate1_review_id": review_id,
        "attempt": 2,
    }
    review_service._store_task(task)

    def fail_run(*_args, **_kwargs):
        raise RuntimeError("test Gate2 failure")

    monkeypatch.setattr(review_service, "run", fail_run)
    failed = review_service.run_auto_gate2(review_id)

    assert failed["status"] == "failed"
    task = review_service.get_task(task_id)
    assert task["auto_gate2"]["status"] == "failed"
    assert "test Gate2 failure" in task["auto_gate2"]["error"]
    assert task["flow_status"] == "gate2_failed"


def test_interrupted_gate2_is_requeued_for_startup_recovery(review_service):
    task_id, review_id = seed_gate1_review(review_service)
    review_service.approve(review_id, "reviewer@example.com")
    task = review_service.get_task(task_id)
    task["auto_gate2"]["status"] = "running"
    task["flow_status"] = "gate2_running"
    review_service._store_task(task)

    recovered = review_service.recover_interrupted_auto_gate2()

    assert recovered == [review_id]
    task = review_service.get_task(task_id)
    assert task["auto_gate2"]["status"] == "queued"
    assert task["auto_gate2"]["interrupted_status"] == "running"


def test_llm_timeout_is_not_retried_as_a_format_fallback(monkeypatch):
    client = LLMClient()
    client.enabled = True
    client.provider = "openai"
    client.api_key = "test-key"
    client.base_url = "https://example.invalid/v1"
    client.model = "test-model"
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        raise TimeoutError("request timed out")

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(client, "_client", lambda: fake_client)

    with pytest.raises(TimeoutError):
        client.complete_json("system", {"input": "test"})
    assert len(calls) == 1


def test_llm_client_disables_sdk_retries(monkeypatch):
    client = LLMClient()
    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return object()

    import openai

    monkeypatch.setattr(openai, "OpenAI", fake_openai)
    client._client()

    assert captured["max_retries"] == 0
