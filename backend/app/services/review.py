import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..config import REPORTS_DIR, REVIEWS_DIR, REPO_ROOT, TASKS_DIR, WORK_ORDERS_DIR
from ..schemas import ReviewRunRequest
from .documents import read_documents
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


class ReviewService:
    def __init__(self):
        self.kb_service = KnowledgeBaseService()
        self.llm_matching = LLMMatchingService()

    def _review_path(self, review_id: str) -> Path:
        return REVIEWS_DIR / f"{review_id}.json"

    def _task_id(self, request: ReviewRunRequest) -> str:
        return request.task_id or f"task-{_slug(request.product_name)}-{_slug(request.product_version)}"

    def _task_path(self, product_name: str, product_version: str, task_id: str) -> Path:
        return TASKS_DIR / _slug(product_name) / _slug(product_version) / f"{task_id}.json"

    def _work_order_path(self, product_name: str, product_version: str, task_id: str, work_order_id: str) -> Path:
        return WORK_ORDERS_DIR / _slug(product_name) / _slug(product_version) / task_id / f"{work_order_id}.json"

    def _report_dir(self, product_name: str, product_version: str, task_id: str, work_order_id: str) -> Path:
        path = REPORTS_DIR / _slug(product_name) / _slug(product_version) / task_id / work_order_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _activity_summary(self, payload: dict) -> dict:
        return {
            "activity_id": payload.get("work_order_id"),
            "activity_type": payload.get("activity_type", "review_run"),
            "work_order_id": payload.get("work_order_id"),
            "review_id": payload.get("review_id"),
            "task_id": payload.get("task_id"),
            "product_name": payload.get("product_name"),
            "product_version": payload.get("product_version"),
            "gate": payload.get("gate"),
            "status": payload.get("status"),
            "matched": payload.get("matched"),
            "approval_status": payload.get("approval_status"),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at", payload.get("created_at")),
            "report_path": payload.get("report_path"),
            "report_url": payload.get("report_url"),
            "report_download_url": payload.get("report_download_url"),
            "work_order_url": payload.get("work_order_url"),
        }

    def _upsert_task(self, payload: dict) -> None:
        task_id = payload["task_id"]
        task_path = self._task_path(payload["product_name"], payload["product_version"], task_id)
        task_path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        task = _read_json(task_path) or {
            "task_id": task_id,
            "task_name": payload.get("task_name") or f"{payload['product_name']} {payload['product_version']} AI Gate Task",
            "product_name": payload["product_name"],
            "product_version": payload["product_version"],
            "project_id": payload.get("project_id"),
            "repository": payload.get("request", {}).get("repository"),
            "branch": payload.get("request", {}).get("branch"),
            "status": "open",
            "created_at": payload.get("created_at", now),
            "updated_at": now,
            "activities": [],
            "gate_reviews": {"gate1": [], "gate2": []},
        }
        task["updated_at"] = now
        task["repository"] = payload.get("request", {}).get("repository") or task.get("repository")
        task["branch"] = payload.get("request", {}).get("branch") or task.get("branch")
        task["project_id"] = payload.get("project_id") or task.get("project_id")
        task["status"] = "completed" if any(a.get("gate") == "gate2" for a in task.get("activities", [])) or payload.get("gate") == "gate2" else "in_progress"

        summary = self._activity_summary(payload)
        activities = [a for a in task.get("activities", []) if a.get("review_id") != payload.get("review_id")]
        activities.append(summary)
        activities.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        task["activities"] = activities

        gate_reviews = task.setdefault("gate_reviews", {"gate1": [], "gate2": []})
        gate = payload.get("gate")
        if gate in {"gate1", "gate2"}:
            gate_items = [a for a in gate_reviews.get(gate, []) if a.get("review_id") != payload.get("review_id")]
            gate_items.append(summary)
            gate_items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
            gate_reviews[gate] = gate_items
        task["latest_gate1_review_id"] = (gate_reviews.get("gate1") or [{}])[0].get("review_id")
        task["latest_gate2_review_id"] = (gate_reviews.get("gate2") or [{}])[0].get("review_id")
        task["activity_count"] = len(task["activities"])
        task["report_count"] = len([a for a in task["activities"] if a.get("report_path")])
        task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

    def _store_review(self, review_id: str, payload: dict) -> None:
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        review_path = self._review_path(review_id)
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        wo_path = self._work_order_path(payload["product_name"], payload["product_version"], payload["task_id"], payload["work_order_id"])
        wo_path.parent.mkdir(parents=True, exist_ok=True)
        wo_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._upsert_task(payload)

    def _load_review(self, review_id: str) -> dict:
        path = self._review_path(review_id)
        if not path.exists():
            raise FileNotFoundError(review_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _latest_gate1_report(self, product_name: str, product_version: str, task_id: str | None = None) -> Path | None:
        candidates = []
        for path in WORK_ORDERS_DIR.glob("**/*.json"):
            item = _read_json(path)
            if not item:
                continue
            if (
                item.get("gate") == "gate1"
                and item.get("product_name") == product_name
                and item.get("product_version") == product_version
                and (not task_id or item.get("task_id") == task_id)
                and item.get("report_path")
            ):
                candidates.append(item)
        candidates.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        if not candidates:
            return None
        report_path = REPO_ROOT / candidates[0]["report_path"]
        return report_path if report_path.exists() else None

    def run(self, gate: str, request: ReviewRunRequest) -> dict:
        gate = gate.lower()
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d%H%M%S")
        task_id = self._task_id(request)
        work_order_id = f"act-{task_id}-{gate}-{timestamp}-{uuid4().hex[:8]}"
        review_id = f"{gate}-review-{timestamp}-{uuid4().hex[:8]}"

        kb = self.kb_service.load(gate)
        document_text, docs = read_documents(request.documents)
        matcher = MatchingEngine(kb, request.threshold)
        match_result = matcher.match(document_text, gate)
        match_result = self.llm_matching.enhance_matches(gate, document_text, docs, kb, match_result, request.threshold)

        report_dir = self._report_dir(request.product_name, request.product_version, task_id, work_order_id)
        gate1_report_text = ""
        verification = {"implemented": 0, "not_implemented": 0, "items": []}

        if gate == "gate2":
            gate1_path = None
            if request.gate1_report:
                gate1_path = Path(request.gate1_report)
                if not gate1_path.is_absolute():
                    gate1_path = REPO_ROOT / request.gate1_report
            if not gate1_path or not gate1_path.exists():
                gate1_path = self._latest_gate1_report(request.product_name, request.product_version, task_id)
            if gate1_path and gate1_path.exists():
                gate1_report_text = gate1_path.read_text(encoding="utf-8")
            verification = verify_gate1_controls(document_text, match_result, gate1_report_text)
            report = generate_gate2_report(review_id, work_order_id, request, kb, match_result, verification)
            report_file = report_dir / f"Security-Review-Gate2-{review_id}.md"
        else:
            report = generate_gate1_report(review_id, work_order_id, request, kb, match_result)
            report_file = report_dir / f"Security-Review-Gate1-{review_id}.md"

        report_file.write_text(report, encoding="utf-8")
        relative_report_path = str(report_file.relative_to(REPO_ROOT))
        response = {
            "task_id": task_id,
            "task_name": request.task_name or f"{request.product_name} {request.product_version} AI Gate Task",
            "work_order_id": work_order_id,
            "activity_id": work_order_id,
            "activity_type": "review_run",
            "review_id": review_id,
            "project_id": request.project_id,
            "product_name": request.product_name,
            "product_version": request.product_version,
            "gate": gate,
            "status": "completed",
            "matched": match_result["matched"],
            "matched_scenarios": [
                {
                    "scenario_id": item["scenario"].get("id"),
                    "scenario_name": item["scenario"].get("name"),
                    "final_score": item.get("final_score"),
                    "risk_level": item["scenario"].get("risk", {}).get("level"),
                }
                for item in match_result.get("matched_scenarios", [])
            ],
            "report_path": relative_report_path,
            "report_url": f"/api/v1/reports/{review_id}",
            "report_download_url": f"/api/v1/reports/{review_id}/download",
            "work_order_url": f"/api/v1/work-orders/{work_order_id}",
            "task_url": f"/api/v1/tasks/{task_id}",
            "approval_status": "pending",
            "llm_enabled": match_result.get("llm_enabled", False),
            "llm_error": match_result.get("llm_error"),
            "gate1_control_verification": verification,
            "created_at": now.isoformat(),
            "request": request.model_dump(),
            "documents": docs,
            "match_result": match_result,
            "artifacts": [
                {
                    "type": "markdown_report",
                    "name": report_file.name,
                    "path": relative_report_path,
                    "view_url": f"/api/v1/reports/{review_id}",
                    "download_url": f"/api/v1/reports/{review_id}/download",
                }
            ],
        }
        self._store_review(review_id, response)
        return response

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
            items.append({
                "task_id": item.get("task_id"),
                "task_name": item.get("task_name"),
                "product_name": item.get("product_name"),
                "product_version": item.get("product_version"),
                "status": item.get("status"),
                "activity_count": item.get("activity_count", len(item.get("activities", []))),
                "report_count": item.get("report_count"),
                "latest_gate1_review_id": item.get("latest_gate1_review_id"),
                "latest_gate2_review_id": item.get("latest_gate2_review_id"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "task_url": f"/api/v1/tasks/{item.get('task_id')}",
            })
        items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        return items

    def get_task(self, task_id: str) -> dict:
        for path in TASKS_DIR.glob("**/*.json"):
            item = _read_json(path)
            if item and item.get("task_id") == task_id:
                return item
        raise FileNotFoundError(task_id)

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
        # Backfill from legacy work orders if tasks do not exist yet.
        for item in self.list_work_orders():
            product = item.get("product_name")
            version = item.get("product_version")
            if product:
                products.setdefault(product, set())
                if version:
                    products[product].add(version)
        return {
            "products": [
                {"product_name": product, "versions": sorted(versions)}
                for product, versions in sorted(products.items())
            ],
            "tasks": tasks,
            "totals": {
                "products": len(products),
                "tasks": len(tasks),
                "activities": len(self.list_work_orders()),
            },
        }

    def dashboard_stats(self) -> dict:
        tasks = self.list_tasks()
        activities = self.list_work_orders()
        return {
            "task_count": len(tasks),
            "activity_count": len(activities),
            "report_count": len([a for a in activities if a.get("report_path")]),
            "gate1_runs": len([a for a in activities if a.get("gate") == "gate1"]),
            "gate2_runs": len([a for a in activities if a.get("gate") == "gate2"]),
            "approved_count": len([a for a in activities if a.get("approval_status") == "approved"]),
            "modified_count": len([a for a in activities if a.get("approval_status") == "modified"]),
            "latest_tasks": tasks[:10],
            "latest_activities": activities[:10],
        }

    def get_work_order(self, work_order_id: str) -> dict:
        for path in WORK_ORDERS_DIR.glob("**/*.json"):
            item = _read_json(path)
            if item and item.get("work_order_id") == work_order_id:
                return item
        raise FileNotFoundError(work_order_id)

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
        review.setdefault("audit", []).append({
            "action": "update_report",
            "reviewer": reviewer,
            "comment": comment,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        self._store_review(review_id, review)
        return review

    def approve(self, review_id: str, reviewer: str, comment: str | None = None) -> dict:
        review = self._load_review(review_id)
        review["approval_status"] = "approved"
        review.setdefault("audit", []).append({
            "action": "approve",
            "reviewer": reviewer,
            "comment": comment,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        self._store_review(review_id, review)
        return review
