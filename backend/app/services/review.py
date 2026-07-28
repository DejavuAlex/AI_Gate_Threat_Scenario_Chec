import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..config import (
    DEFAULT_GATE2_DOCUMENTS,
    REPORTS_DIR,
    REVIEWS_DIR,
    REPO_ROOT,
    TASKS_DIR,
    TASK_SEQUENCE_FILE,
    WORK_ORDERS_DIR,
)
from ..schemas import ReviewRunRequest
from .documents import extract_stories, read_documents
from .gate2_verifier import verify_gate1_controls
from .knowledge_base import KnowledgeBaseService
from .llm_matching import LLMMatchingService
from .matching import MatchingEngine
from .report_generator import generate_gate1_report, generate_gate2_report


def _slug(value: str | None, fallback: str = "unknown") -> str:
    text = (value or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    return text.strip("-") or fallback


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _compact_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


def _matched_scenario_summary(match_result: dict) -> list[dict]:
    return [
        {
            "scenario_id": item["scenario"].get("id"),
            "scenario_name": item["scenario"].get("name"),
            "final_score": item.get("final_score"),
            "risk_level": item["scenario"].get("risk", {}).get("level"),
        }
        for item in match_result.get("matched_scenarios", [])
    ]


class ReviewService:
    def __init__(self):
        self.kb_service = KnowledgeBaseService()
        self.llm_matching = LLMMatchingService()

    def _next_task_serial(self) -> int:
        TASK_SEQUENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = _read_json(TASK_SEQUENCE_FILE) or {"last_serial_no": 0}
        next_no = int(data.get("last_serial_no", 0)) + 1
        TASK_SEQUENCE_FILE.write_text(json.dumps({"last_serial_no": next_no}, ensure_ascii=False, indent=2), encoding="utf-8")
        return next_no

    def _task_code(self, serial_no: int) -> str:
        return f"TASK-{serial_no:06d}"

    def _review_path(self, review_id: str) -> Path:
        return REVIEWS_DIR / f"{review_id}.json"

    def _task_path_by_meta(self, product_name: str, product_version: str, task_id: str) -> Path:
        return TASKS_DIR / _slug(product_name) / _slug(product_version) / f"{task_id}.json"

    def _find_task_path(self, task_id: str) -> Path | None:
        normalized = task_id.lower()
        for path in TASKS_DIR.glob("**/*.json"):
            item = _read_json(path)
            if item and item.get("task_id", "").lower() == normalized:
                return path
            if item and item.get("task_code", "").lower() == normalized:
                return path
        return None

    def _load_task(self, task_id: str) -> dict | None:
        path = self._find_task_path(task_id)
        return _read_json(path) if path else None

    def _create_or_get_task(self, request: ReviewRunRequest, gate: str, now: datetime) -> dict:
        if request.task_id:
            existing = self._load_task(request.task_id)
            if existing:
                return existing

        serial_no = self._next_task_serial()
        task_code = self._task_code(serial_no)
        timestamp = _compact_timestamp(now)
        task_id = request.task_id or task_code.lower()
        task_name = request.task_name or f"{request.product_name}-{request.product_version}-{gate}-{timestamp}"
        task = {
            "task_id": task_id,
            "task_serial_no": serial_no,
            "task_code": task_code,
            "task_name": task_name,
            "product_name": request.product_name,
            "product_version": request.product_version,
            "project_id": request.project_id,
            "repository": request.repository,
            "branch": request.branch,
            "status": "in_progress",
            "flow_status": "gate1_pending" if gate == "gate1" else "gate2_direct_run",
            "final_result": "pending",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "triggered_by": request.triggered_by,
            "activities": [],
            "reviews": {"gate1": [], "gate2": []},
            "reports": {"gate1": [], "gate2": []},
            "approval": {},
            "auto_gate2": {"enabled": request.auto_run_gate2_on_gate1_approval, "status": "not_started"},
            "gate2_documents": request.gate2_documents or DEFAULT_GATE2_DOCUMENTS,
            "gate2_document_texts": [item.model_dump() for item in request.gate2_document_texts],
            "gate2_knowledge_base_id": request.gate2_knowledge_base_id,
        }
        path = self._task_path_by_meta(request.product_name, request.product_version, task_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
        return task

    def _task_path(self, task: dict) -> Path:
        return self._task_path_by_meta(task["product_name"], task["product_version"], task["task_id"])

    def _work_order_path(self, task: dict, work_order_id: str) -> Path:
        return WORK_ORDERS_DIR / _slug(task["product_name"]) / _slug(task["product_version"]) / task["task_id"] / f"{work_order_id}.json"

    def _report_dir(self, task: dict, work_order_id: str) -> Path:
        path = REPORTS_DIR / _slug(task["product_name"]) / _slug(task["product_version"]) / task["task_id"] / work_order_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _activity_summary(self, payload: dict) -> dict:
        return {
            "activity_id": payload.get("work_order_id"),
            "activity_name": payload.get("activity_name"),
            "activity_type": payload.get("activity_type", "review_run"),
            "work_order_id": payload.get("work_order_id"),
            "review_id": payload.get("review_id"),
            "task_id": payload.get("task_id"),
            "task_serial_no": payload.get("task_serial_no"),
            "task_code": payload.get("task_code"),
            "product_name": payload.get("product_name"),
            "product_version": payload.get("product_version"),
            "gate": payload.get("gate"),
            "status": payload.get("status"),
            "matched": payload.get("matched"),
            "approval_status": payload.get("approval_status"),
            "approved_by": payload.get("approved_by"),
            "approved_at": payload.get("approved_at"),
            "triggered_by": payload.get("request", {}).get("triggered_by"),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at", payload.get("created_at")),
            "report_path": payload.get("report_path"),
            "report_url": payload.get("report_url"),
            "report_download_url": payload.get("report_download_url"),
            "work_order_url": payload.get("work_order_url"),
        }

    def _store_task(self, task: dict) -> None:
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        path = self._task_path(task)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

    def _store_review(self, review_id: str, payload: dict) -> None:
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        review_path = self._review_path(review_id)
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        task = self._load_task(payload["task_id"])
        if not task:
            task = {
                "task_id": payload["task_id"],
                "task_serial_no": payload.get("task_serial_no"),
                "task_code": payload.get("task_code"),
                "task_name": payload.get("task_name"),
                "product_name": payload.get("product_name"),
                "product_version": payload.get("product_version"),
                "status": "in_progress",
                "flow_status": "in_progress",
                "created_at": payload.get("created_at"),
                "activities": [],
                "reviews": {"gate1": [], "gate2": []},
                "reports": {"gate1": [], "gate2": []},
                "approval": {},
                "auto_gate2": {"enabled": True, "status": "not_started"},
            }

        wo_path = self._work_order_path(task, payload["work_order_id"])
        wo_path.parent.mkdir(parents=True, exist_ok=True)
        wo_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        summary = self._activity_summary(payload)
        task["activities"] = [a for a in task.get("activities", []) if a.get("review_id") != review_id]
        task["activities"].append(summary)
        task["activities"].sort(key=lambda item: item.get("created_at") or "", reverse=True)
        task.setdefault("reviews", {"gate1": [], "gate2": []})
        task.setdefault("reports", {"gate1": [], "gate2": []})
        gate = payload.get("gate")
        if gate in {"gate1", "gate2"}:
            task["reviews"][gate] = [a for a in task["reviews"].get(gate, []) if a.get("review_id") != review_id]
            task["reviews"][gate].append(summary)
            task["reviews"][gate].sort(key=lambda item: item.get("created_at") or "", reverse=True)
            if payload.get("report_path"):
                task["reports"][gate] = [a for a in task["reports"].get(gate, []) if a.get("review_id") != review_id]
                task["reports"][gate].append(summary)
                task["reports"][gate].sort(key=lambda item: item.get("created_at") or "", reverse=True)
        task["latest_gate1_review_id"] = (task.get("reviews", {}).get("gate1") or [{}])[0].get("review_id")
        task["latest_gate2_review_id"] = (task.get("reviews", {}).get("gate2") or [{}])[0].get("review_id")
        task["activity_count"] = len(task.get("activities", []))
        task["report_count"] = len([a for a in task.get("activities", []) if a.get("report_path")])
        if gate == "gate1" and payload.get("status") == "completed":
            task["flow_status"] = "gate1_completed_pending_approval"
        elif gate == "gate2" and payload.get("status") == "completed":
            task["flow_status"] = "gate2_completed"
            task["status"] = "completed"
            task["final_result"] = "gate2_completed"
        self._store_task(task)

    def _load_review(self, review_id: str) -> dict:
        path = self._review_path(review_id)
        if not path.exists():
            raise FileNotFoundError(review_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _latest_gate1_report(self, task_id: str) -> Path | None:
        task = self._load_task(task_id)
        if not task:
            return None
        reports = task.get("reports", {}).get("gate1", [])
        if not reports:
            return None
        report_path = REPO_ROOT / reports[0].get("report_path", "")
        return report_path if report_path.exists() else None

    def _run_match(self, gate: str, request: ReviewRunRequest) -> tuple[dict, list[dict], str, dict]:
        kb = self.kb_service.load(gate, request.knowledge_base_id)
        document_text, docs = read_documents(request.documents, request.document_texts)
        stories = extract_stories(docs)
        matcher = MatchingEngine(kb, request.threshold)
        match_result = matcher.match(document_text, gate)
        match_result = self.llm_matching.enhance_matches(gate, document_text, docs, kb, match_result, request.threshold)
        match_result["story_assessments"] = matcher.assess_stories(stories, gate)
        return kb, docs, document_text, match_result

    def run_local_agent(self, gate: str, request: ReviewRunRequest) -> dict:
        """Run Gate1/Gate2 as a local CLI agent without persistence or approval flow.

        This is intended for VS Code, local CLI, and developer workstation usage.
        It never creates tasks, review records, work orders, report files, approvals,
        or auto-Gate2 workflow state. The caller receives a single in-memory review
        result and can decide whether/how to store it locally.
        """
        gate = gate.lower()
        now = datetime.now(timezone.utc)
        timestamp = _compact_timestamp(now)
        local_run_id = f"local-{gate}-{timestamp}-{uuid4().hex[:8]}"
        request.triggered_by = request.triggered_by or "cli-local"
        request.auto_run_gate2_on_gate1_approval = False

        kb, docs, document_text, match_result = self._run_match(gate, request)
        verification = {"implemented": 0, "not_implemented": 0, "items": []}

        if gate == "gate2":
            gate1_report_text = ""
            if request.gate1_report:
                gate1_path = Path(request.gate1_report)
                if not gate1_path.is_absolute():
                    gate1_path = REPO_ROOT / request.gate1_report
                if gate1_path.exists():
                    gate1_report_text = gate1_path.read_text(encoding="utf-8")
            verification = verify_gate1_controls(document_text, match_result, gate1_report_text)
            report_markdown = generate_gate2_report(local_run_id, local_run_id, request, kb, match_result, verification, {})
        else:
            report_markdown = generate_gate1_report(local_run_id, local_run_id, request, kb, match_result, {})

        return {
            "execution_mode": "local_cli_agent",
            "persistence": "none",
            "approval_required": False,
            "auto_gate2_enabled": False,
            "local_run_id": local_run_id,
            "gate": gate,
            "status": "completed",
            "project_id": request.project_id,
            "product_name": request.product_name,
            "product_version": request.product_version,
            "repository": request.repository,
            "branch": request.branch,
            "matched": match_result["matched"],
            "matched_scenarios": _matched_scenario_summary(match_result),
            "gate1_control_verification": verification,
            "llm_enabled": match_result.get("llm_enabled", False),
            "llm_error": match_result.get("llm_error"),
            "knowledge_base_id": request.knowledge_base_id,
            "knowledge_base_version": kb.get("knowledge_base_version"),
            "created_at": now.isoformat(),
            "request": request.model_dump(),
            "documents": docs,
            "match_result": match_result,
            "report_markdown": report_markdown,
        }

    def run(self, gate: str, request: ReviewRunRequest) -> dict:
        gate = gate.lower()
        now = datetime.now(timezone.utc)
        timestamp = _compact_timestamp(now)
        task = self._create_or_get_task(request, gate, now)
        activity_name = f"{request.product_name}-{request.product_version}-{gate}-{timestamp}"
        work_order_id = f"{task['task_code'].lower()}-{gate}-{timestamp}-{uuid4().hex[:6]}"
        review_id = f"{gate}-review-{timestamp}-{uuid4().hex[:8]}"

        kb, docs, document_text, match_result = self._run_match(gate, request)
        verification = {"implemented": 0, "not_implemented": 0, "items": []}

        report_dir = self._report_dir(task, work_order_id)
        task_meta = {
            "task_serial_no": task.get("task_serial_no"),
            "task_code": task.get("task_code"),
            "task_name": task.get("task_name"),
        }
        if gate == "gate2":
            gate1_report_text = ""
            gate1_path = None
            if request.gate1_report:
                gate1_path = Path(request.gate1_report)
                if not gate1_path.is_absolute():
                    gate1_path = REPO_ROOT / request.gate1_report
            if not gate1_path or not gate1_path.exists():
                gate1_path = self._latest_gate1_report(task["task_id"])
            if gate1_path and gate1_path.exists():
                gate1_report_text = gate1_path.read_text(encoding="utf-8")
            verification = verify_gate1_controls(document_text, match_result, gate1_report_text)
            report = generate_gate2_report(review_id, work_order_id, request, kb, match_result, verification, task_meta)
            report_file = report_dir / f"Security-Review-Gate2-{review_id}.md"
        else:
            report = generate_gate1_report(review_id, work_order_id, request, kb, match_result, task_meta)
            report_file = report_dir / f"Security-Review-Gate1-{review_id}.md"

        report_file.write_text(report, encoding="utf-8")
        relative_report_path = str(report_file.relative_to(REPO_ROOT))
        response = {
            "task_id": task["task_id"],
            "task_serial_no": task.get("task_serial_no"),
            "task_code": task.get("task_code"),
            "task_name": task.get("task_name"),
            "work_order_id": work_order_id,
            "activity_id": work_order_id,
            "activity_name": activity_name,
            "activity_type": "review_run",
            "review_id": review_id,
            "project_id": request.project_id,
            "product_name": request.product_name,
            "product_version": request.product_version,
            "gate": gate,
            "status": "completed",
            "matched": match_result["matched"],
            "matched_scenarios": _matched_scenario_summary(match_result),
            "report_path": relative_report_path,
            "report_url": f"/api/v1/reports/{review_id}",
            "report_download_url": f"/api/v1/reports/{review_id}/download",
            "work_order_url": f"/api/v1/work-orders/{work_order_id}",
            "task_url": f"/api/v1/tasks/{task['task_id']}",
            "approval_status": "pending",
            "approved_by": None,
            "approved_at": None,
            "llm_enabled": match_result.get("llm_enabled", False),
            "llm_error": match_result.get("llm_error"),
            "knowledge_base_id": request.knowledge_base_id,
            "knowledge_base_version": kb.get("knowledge_base_version"),
            "gate1_control_verification": verification,
            "created_at": now.isoformat(),
            "request": request.model_dump(),
            "documents": docs,
            "match_result": match_result,
            "artifacts": [{"type": "markdown_report", "name": report_file.name, "path": relative_report_path, "view_url": f"/api/v1/reports/{review_id}", "download_url": f"/api/v1/reports/{review_id}/download"}],
        }
        self._store_review(review_id, response)
        return response

    def approve(self, review_id: str, reviewer: str, comment: str | None = None) -> dict:
        review = self._load_review(review_id)
        now = datetime.now(timezone.utc).isoformat()
        review["approval_status"] = "approved"
        review["approved_by"] = reviewer
        review["approved_at"] = now
        review.setdefault("audit", []).append({"action": "approve", "reviewer": reviewer, "comment": comment, "at": now})
        self._store_review(review_id, review)

        result = {"approved_review": review, "auto_gate2_triggered": False, "auto_gate2_result": None}
        task = self._load_task(review.get("task_id"))
        if not task:
            return result
        task.setdefault("approval", {})[review["gate"]] = {"review_id": review_id, "approved_by": reviewer, "approved_at": now, "comment": comment}

        if review.get("gate") == "gate1":
            if not review.get("matched"):
                task["flow_status"] = "completed_no_security_risk"
                task["status"] = "completed"
                task["final_result"] = "no_security_risk"
                task["auto_gate2"] = {"enabled": False, "status": "skipped_no_security_risk"}
            else:
                task["flow_status"] = "gate1_approved_gate2_required"
                task["final_result"] = "gate1_risk_found_gate2_required"
                auto_enabled = review.get("request", {}).get("auto_run_gate2_on_gate1_approval", True)
                if auto_enabled:
                    task["auto_gate2"] = {"enabled": True, "status": "running", "triggered_by_gate1_review_id": review_id, "triggered_at": now}
                    self._store_task(task)
                    gate2_request = ReviewRunRequest(
                        project_id=review.get("project_id") or review.get("request", {}).get("project_id", "demo"),
                        product_name=review["product_name"],
                        product_version=review["product_version"],
                        task_id=review["task_id"],
                        task_name=review.get("task_name"),
                        repository=review.get("request", {}).get("repository"),
                        branch=review.get("request", {}).get("branch"),
                        documents=review.get("request", {}).get("gate2_documents") or task.get("gate2_documents") or DEFAULT_GATE2_DOCUMENTS,
                        document_texts=review.get("request", {}).get("gate2_document_texts") or task.get("gate2_document_texts") or [],
                        knowledge_base_id=review.get("request", {}).get("gate2_knowledge_base_id") or task.get("gate2_knowledge_base_id") or "default",
                        threshold=review.get("request", {}).get("threshold", 0.78),
                        triggered_by="auto-after-gate1-approval",
                        gate1_report=review.get("report_path"),
                        auto_run_gate2_on_gate1_approval=False,
                    )
                    gate2_result = self.run("gate2", gate2_request)
                    result["auto_gate2_triggered"] = True
                    result["auto_gate2_result"] = gate2_result
                    task = self._load_task(review["task_id"]) or task
                    task["auto_gate2"] = {"enabled": True, "status": "completed", "triggered_by_gate1_review_id": review_id, "gate2_review_id": gate2_result["review_id"], "completed_at": datetime.now(timezone.utc).isoformat()}
                else:
                    task["auto_gate2"] = {"enabled": False, "status": "manual_gate2_required"}
        elif review.get("gate") == "gate2":
            task["flow_status"] = "completed_gate2_approved"
            task["status"] = "completed"
            task["final_result"] = "gate2_approved"
        self._store_task(task)
        return result

    def list_tasks(self, product_name: str | None = None, product_version: str | None = None) -> list[dict]:
        items = []
        for path in TASKS_DIR.glob("**/*.json"):
            item = _read_json(path)
            if not item:
                continue
            if product_name and item.get("product_name") != product_name:
                continue
            if product_version and item.get("product_version") != product_version:
                continue
            latest_gate1 = (item.get("reviews", {}).get("gate1") or [{}])[0]
            latest_gate2 = (item.get("reviews", {}).get("gate2") or [{}])[0]
            items.append({
                "task_id": item.get("task_id"),
                "task_serial_no": item.get("task_serial_no"),
                "task_code": item.get("task_code"),
                "task_name": item.get("task_name"),
                "product_name": item.get("product_name"),
                "product_version": item.get("product_version"),
                "status": item.get("status"),
                "flow_status": item.get("flow_status"),
                "final_result": item.get("final_result"),
                "triggered_by": item.get("triggered_by"),
                "activity_count": item.get("activity_count", len(item.get("activities", []))),
                "report_count": item.get("report_count"),
                "latest_gate1_review_id": latest_gate1.get("review_id"),
                "latest_gate1_report_url": latest_gate1.get("report_url"),
                "latest_gate1_download_url": latest_gate1.get("report_download_url"),
                "latest_gate2_review_id": latest_gate2.get("review_id"),
                "latest_gate2_report_url": latest_gate2.get("report_url"),
                "latest_gate2_download_url": latest_gate2.get("report_download_url"),
                "approval": item.get("approval", {}),
                "auto_gate2": item.get("auto_gate2", {}),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "task_url": f"/api/v1/tasks/{item.get('task_id')}",
                "final_report_url": f"/api/v1/tasks/{item.get('task_id')}/final-report",
                "final_report_download_url": f"/api/v1/tasks/{item.get('task_id')}/final-report/download",
            })
        items.sort(key=lambda item: item.get("task_serial_no") or 0, reverse=True)
        return items

    def get_task(self, task_id: str) -> dict:
        task = self._load_task(task_id)
        if not task:
            raise FileNotFoundError(task_id)
        return task

    def list_work_orders(self, product_name: str | None = None, product_version: str | None = None, task_id: str | None = None) -> list[dict]:
        items = []
        for path in WORK_ORDERS_DIR.glob("**/*.json"):
            item = _read_json(path)
            if not item:
                continue
            if product_name and item.get("product_name") != product_name:
                continue
            if product_version and item.get("product_version") != product_version:
                continue
            if task_id and item.get("task_id") != task_id:
                continue
            items.append(self._activity_summary(item))
        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return items

    def get_work_order(self, work_order_id: str) -> dict:
        for path in WORK_ORDERS_DIR.glob("**/*.json"):
            item = _read_json(path)
            if item and item.get("work_order_id") == work_order_id:
                return item
        raise FileNotFoundError(work_order_id)

    def catalog(self) -> dict:
        products: dict[str, set[str]] = {}
        tasks = self.list_tasks()
        for task in tasks:
            product = task.get("product_name")
            version = task.get("product_version")
            if product:
                products.setdefault(product, set())
                if version:
                    products[product].add(version)
        return {"products": [{"product_name": product, "versions": sorted(versions)} for product, versions in sorted(products.items())], "tasks": tasks, "totals": {"products": len(products), "tasks": len(tasks)}}

    def dashboard_stats(self) -> dict:
        tasks = self.list_tasks()
        activities = self.list_work_orders()
        return {"task_count": len(tasks), "activity_count": len(activities), "report_count": len([a for a in activities if a.get("report_path")]), "gate1_runs": len([a for a in activities if a.get("gate") == "gate1"]), "gate2_runs": len([a for a in activities if a.get("gate") == "gate2"]), "approved_count": len([a for a in activities if a.get("approval_status") == "approved"]), "latest_tasks": tasks[:20]}

    def get(self, review_id: str) -> dict:
        return self._load_review(review_id)

    def get_report_path(self, review_id: str) -> Path:
        review = self._load_review(review_id)
        path = REPO_ROOT / review["report_path"]
        if not path.exists():
            raise FileNotFoundError(review_id)
        return path

    def get_report_content(self, review_id: str) -> str:
        return self.get_report_path(review_id).read_text(encoding="utf-8")

    def update_report(self, review_id: str, content: str, reviewer: str | None = None, comment: str | None = None) -> dict:
        review = self._load_review(review_id)
        path = REPO_ROOT / review["report_path"]
        path.write_text(content, encoding="utf-8")
        review["approval_status"] = "modified"
        review.setdefault("audit", []).append({"action": "update_report", "reviewer": reviewer, "comment": comment, "at": datetime.now(timezone.utc).isoformat()})
        self._store_review(review_id, review)
        return review
