#!/usr/bin/env python3
"""Run synthetic Gate1 -> approval -> auto-Gate2 scenarios against an AI-Gate server."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tests" / "fixtures" / "synthetic-e2e-scenarios.json"
TERMINAL_AUTO_GATE2_STATES = {"completed", "failed", "skipped_no_security_risk"}


class E2EFailure(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str, request_timeout: float):
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[Any, str]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                raw = response.read().decode("utf-8")
                content_type = response.headers.get("Content-Type", "")
                if "json" in content_type:
                    return json.loads(raw), raw
                return raw, raw
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise E2EFailure(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise E2EFailure(f"{method} {path} failed: {exc.reason}") from exc

    def get_json(self, path: str) -> dict[str, Any]:
        data, _ = self.request("GET", path)
        if not isinstance(data, dict):
            raise E2EFailure(f"GET {path} did not return a JSON object")
        return data

    def get_text(self, path: str) -> str:
        _, raw = self.request("GET", path)
        return raw

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data, _ = self.request("POST", path, payload)
        if not isinstance(data, dict):
            raise E2EFailure(f"POST {path} did not return a JSON object")
        return data


def scenario_ids(review: dict[str, Any]) -> set[str]:
    return {str(item.get("scenario_id")) for item in review.get("matched_scenarios", [])}


def assert_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise E2EFailure(f"{message}: expected {expected!r}, got {actual!r}")


def assert_review_accuracy(
    review: dict[str, Any],
    gate: str,
    knowledge_base_id: str,
    expected_ids: list[str],
    threshold: float,
) -> None:
    assert_equal(review.get("gate"), gate, f"{gate} response gate")
    assert_equal(review.get("knowledge_base_id"), knowledge_base_id, f"{gate} knowledge base")
    assert_equal(scenario_ids(review), set(expected_ids), f"{gate} matched scenario IDs")
    if not review.get("matched"):
        raise E2EFailure(f"{gate} unexpectedly reported no match")
    for item in review.get("matched_scenarios", []):
        if float(item.get("final_score", 0)) < threshold:
            raise E2EFailure(f"{gate} scenario {item.get('scenario_id')} is below threshold")
    source_text = "\n".join(str(item.get("content") or "") for item in review.get("documents", []))
    for item in (review.get("match_result") or {}).get("matched_scenarios", []):
        evidence = item.get("matched_evidence") or []
        if not evidence:
            raise E2EFailure(f"{gate} scenario {item.get('scenario', {}).get('id')} has no evidence")
        if any(str(quote) not in source_text for quote in evidence):
            raise E2EFailure(f"{gate} returned evidence that is not present in its source specs")


def wait_for_auto_gate2(client: ApiClient, task_id: str, deadline_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        task = client.get_json(f"/api/v1/tasks/{task_id}")
        state = (task.get("auto_gate2") or {}).get("status")
        if state in TERMINAL_AUTO_GATE2_STATES:
            return task
        time.sleep(0.5)
    raise E2EFailure(f"auto Gate2 timed out for task {task_id}")


def preflight(client: ApiClient, manifest: dict[str, Any]) -> None:
    assert_equal(client.get_json("/api/v1/health").get("status"), "ok", "health status")
    available_specs = {item["path"] for item in client.get_json("/api/v1/specs").get("items", [])}
    required_specs: set[str] = set(manifest["negative_gate1_documents"] + manifest["negative_gate2_documents"])
    for case in manifest["scenarios"]:
        required_specs.update(case["gate1_documents"])
        required_specs.update(case["gate2_documents"])
    missing_specs = sorted(required_specs - available_specs)
    if missing_specs:
        raise E2EFailure(f"server cannot see required specs: {missing_specs}")

    for gate in ("gate1", "gate2"):
        catalog = client.get_json(f"/api/v1/knowledge-base/{gate}/catalog").get("items", [])
        available_ids = {item.get("knowledge_base_id") for item in catalog}
        required_ids = {case["knowledge_base_id"] for case in manifest["scenarios"]}
        missing_ids = sorted(required_ids - available_ids)
        if missing_ids:
            raise E2EFailure(f"{gate} catalog is missing knowledge bases: {missing_ids}")


def run_positive_case(
    client: ApiClient,
    case: dict[str, Any],
    threshold: float,
    auto_gate2_deadline: float,
    traceability_mode: str,
    require_llm_success: bool,
) -> dict[str, Any]:
    run_id = uuid4().hex[:10]
    task_id = f"synthetic-e2e-{case['slug']}-{run_id}"
    payload = {
        "project_id": f"synthetic-e2e-{case['slug']}",
        "product_name": f"{case['product_name']} {run_id}",
        "product_version": "e2e-1.0.0",
        "task_id": task_id,
        "task_name": f"Synthetic E2E {case['slug']} {run_id}",
        "repository": "synthetic/ai-gate-e2e",
        "branch": "test-fixtures",
        "documents": case["gate1_documents"],
        "gate2_documents": case["gate2_documents"],
        "knowledge_base_id": case["knowledge_base_id"],
        "gate2_knowledge_base_id": case["knowledge_base_id"],
        "threshold": threshold,
        "triggered_by": "deployed-e2e",
        "auto_run_gate2_on_gate1_approval": True,
    }
    gate1 = client.post_json("/api/v1/ui/security-review/gate1/run", payload)
    assert_review_accuracy(
        gate1,
        "gate1",
        case["knowledge_base_id"],
        case["expected_gate1_scenarios"],
        threshold,
    )
    approval = client.post_json(
        f"/api/v1/reports/{gate1['review_id']}/approve",
        {"reviewer": "synthetic-e2e@example.invalid", "comment": "Automated synthetic E2E approval"},
    )
    assert_equal(approval.get("auto_gate2_triggered"), True, "Gate1 approval auto-Gate2 trigger")
    task = wait_for_auto_gate2(client, gate1["task_id"], auto_gate2_deadline)
    auto_gate2 = task.get("auto_gate2") or {}
    assert_equal(auto_gate2.get("status"), "completed", "auto Gate2 status")
    gate2_review_id = auto_gate2.get("gate2_review_id")
    if not gate2_review_id:
        raise E2EFailure("completed auto Gate2 has no review ID")
    gate2 = client.get_json(f"/api/v1/security-review/gate2/{gate2_review_id}")
    assert_review_accuracy(
        gate2,
        "gate2",
        case["knowledge_base_id"],
        case["expected_gate2_scenarios"],
        threshold,
    )
    assert_equal(gate2.get("task_id"), gate1.get("task_id"), "Gate1/Gate2 task identity")
    assert_equal(gate2.get("request", {}).get("knowledge_base_id"), case["knowledge_base_id"], "auto Gate2 KB propagation")
    assert_equal(gate2.get("request", {}).get("gate1_report"), gate1.get("report_path"), "auto Gate2 Gate1 report")
    if require_llm_success:
        for review in (gate1, gate2):
            if not review.get("llm_enabled") or review.get("llm_error"):
                raise E2EFailure(
                    f"{review.get('gate')} did not complete its LLM enhancement successfully: "
                    f"{review.get('llm_error') or 'LLM disabled'}"
                )

    verification = gate2.get("gate1_control_verification") or {}
    if not verification.get("baseline_available"):
        raise E2EFailure("Gate2 did not receive a Gate1 final-control baseline")
    if traceability_mode == "exact":
        assert_equal(verification.get("documented"), case["expected_gate1_control_count"], "documented Gate1 controls")
        assert_equal(verification.get("partial"), 0, "partial Gate1 controls")
        assert_equal(verification.get("no_evidence"), 0, "missing Gate1 controls")

    gate1_report = client.get_text(gate1["report_url"])
    gate1_download = client.get_text(gate1["report_download_url"])
    gate2_report = client.get_text(gate2["report_url"])
    gate2_download = client.get_text(gate2["report_download_url"])
    assert_equal(gate1_report, gate1_download, "Gate1 report view/download content")
    assert_equal(gate2_report, gate2_download, "Gate2 report view/download content")
    for expected_id in case["expected_gate1_scenarios"]:
        if expected_id not in gate1_report:
            raise E2EFailure(f"Gate1 report is missing {expected_id}")
    for expected_id in case["expected_gate2_scenarios"]:
        if expected_id not in gate2_report:
            raise E2EFailure(f"Gate2 report is missing {expected_id}")

    work_orders = client.get_json(f"/api/v1/work-orders?task_id={gate1['task_id']}").get("items", [])
    assert_equal({item.get("gate") for item in work_orders}, {"gate1", "gate2"}, "workflow work-order gates")
    final_report = client.get_text(f"/api/v1/tasks/{gate1['task_id']}/final-report")
    if gate1["review_id"] not in final_report or gate2["review_id"] not in final_report:
        raise E2EFailure("final task report does not reference both reviews")

    return {
        "slug": case["slug"],
        "task_id": gate1["task_id"],
        "gate1_review_id": gate1["review_id"],
        "gate2_review_id": gate2["review_id"],
        "gate1_scenarios": sorted(scenario_ids(gate1)),
        "gate2_scenarios": sorted(scenario_ids(gate2)),
        "documented_gate1_controls": verification.get("documented"),
        "partial_gate1_controls": verification.get("partial"),
        "missing_gate1_controls": verification.get("no_evidence"),
        "llm_enabled": bool(gate1.get("llm_enabled") and gate2.get("llm_enabled")),
        "llm_successful": not gate1.get("llm_error") and not gate2.get("llm_error"),
        "status": "passed",
    }


def run_negative_checks(
    client: ApiClient,
    manifest: dict[str, Any],
    case: dict[str, Any],
    threshold: float,
) -> int:
    false_positives = 0
    for gate in ("gate1", "gate2"):
        run_id = uuid4().hex[:10]
        payload = {
            "project_id": f"synthetic-negative-{case['slug']}",
            "product_name": f"Synthetic Negative Control {case['slug']} {run_id}",
            "product_version": "e2e-1.0.0",
            "task_id": f"synthetic-negative-{gate}-{case['slug']}-{run_id}",
            "repository": "synthetic/ai-gate-e2e",
            "branch": "test-fixtures",
            "documents": manifest[f"negative_{gate}_documents"],
            "knowledge_base_id": case["knowledge_base_id"],
            "threshold": threshold,
            "triggered_by": "deployed-e2e-negative",
            "auto_run_gate2_on_gate1_approval": False,
        }
        review = client.post_json(f"/api/v1/ui/security-review/{gate}/run", payload)
        ids = scenario_ids(review)
        false_positives += len(ids)
        if review.get("matched") or ids:
            raise E2EFailure(f"negative control matched {gate} scenarios for {case['slug']}: {sorted(ids)}")
    return false_positives


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:18082")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--request-timeout", type=float, default=130.0)
    parser.add_argument("--auto-gate2-deadline", type=float, default=180.0)
    parser.add_argument("--skip-negative", action="store_true")
    parser.add_argument("--traceability-mode", choices=("exact", "report-only"), default="exact")
    parser.add_argument("--require-llm-success", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    threshold = float(manifest["threshold"])
    client = ApiClient(args.base_url, args.request_timeout)
    started_at = time.time()

    try:
        preflight(client, manifest)
        positive_results = []
        negative_false_positives = 0
        for case in manifest["scenarios"]:
            print(f"[E2E] {case['slug']}: Gate1 -> approval -> auto Gate2", flush=True)
            positive_results.append(
                run_positive_case(
                    client,
                    case,
                    threshold,
                    args.auto_gate2_deadline,
                    args.traceability_mode,
                    args.require_llm_success,
                )
            )
            if not args.skip_negative:
                negative_false_positives += run_negative_checks(client, manifest, case, threshold)

        true_positives = sum(
            len(case["expected_gate1_scenarios"]) + len(case["expected_gate2_scenarios"])
            for case in manifest["scenarios"]
        )
        true_negatives = 0 if args.skip_negative else true_positives
        total = true_positives + true_negatives + negative_false_positives
        summary = {
            "status": "passed",
            "base_url": args.base_url,
            "threshold": threshold,
            "scenario_count": len(manifest["scenarios"]),
            "positive_expected": true_positives,
            "positive_matched": true_positives,
            "negative_decisions": true_negatives,
            "negative_false_positives": negative_false_positives,
            "precision": 1.0,
            "recall": 1.0,
            "specificity": None if args.skip_negative else 1.0,
            "accuracy": 1.0 if total else None,
            "duration_seconds": round(time.time() - started_at, 3),
            "results": positive_results,
        }
        rendered = json.dumps(summary, ensure_ascii=False, indent=2)
        print(rendered)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        return 0
    except (E2EFailure, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"E2E FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
