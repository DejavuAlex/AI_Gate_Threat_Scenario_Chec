import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..config import REPORTS_DIR, REVIEWS_DIR, REPO_ROOT, WORK_ORDERS_DIR
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


class ReviewService:
    def __init__(self):
        self.kb_service = KnowledgeBaseService()
        self.llm_matching = LLMMatchingService()

    def _review_path(self, review_id: str) -> Path:
        return REVIEWS_DIR / f"{review_id}.json"

    def _work_order_path(self, product_name: str, product_version: str, work_order_id: str) -> Path:
        return WORK_ORDERS_DIR / _slug(product_name) / _slug(product_version) / f"{work_order_id}.json"

    def _store_review(self, review_id: str, payload: dict) -> None:
        review_path = self._review_path(review_id)
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if payload.get("work_order_id"):
            wo_path = self._work_order_path(payload.get("product_name"), payload.get("product_version"), payload["work_order_id"])
            wo_path.parent.mkdir(parents=True, exist_ok=True)
            wo_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_review(self, review_id: str) -> dict:
        path = self._review_path(review_id)
        if not path.exists():
            raise FileNotFoundError(review_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _report_dir(self, product_name: str, product_version: str, work_order_id: str) -> Path:
        path = REPORTS_DIR / _slug(product_name) / _slug(product_version) / work_order_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _latest_gate1_report(self, product_name: str, product_version: str) -> Path | None:
        candidates = []
        for path in WORK_ORDERS_DIR.glob("**/*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if (
                item.get("gate") == "gate1"
                and item.get("product_name") == product_name
                and item.get("product_version") == product_version
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
        work_order_id = f"wo-{_slug(request.product_name)}-{_slug(request.product_version)}-{gate}-{timestamp}-{uuid4().hex[:8]}"
        review_id = f"{gate}-review-{timestamp}-{uuid4().hex[:8]}"

        kb = self.kb_service.load(gate)
        document_text, docs = read_documents(request.documents)
        matcher = MatchingEngine(kb, request.threshold)
        match_result = matcher.match(document_text, gate)
        match_result = self.llm_matching.enhance_matches(gate, document_text, docs, kb, match_result, request.threshold)

        report_dir = self._report_dir(request.product_name, request.product_version, work_order_id)
        gate1_report_text = ""
        verification = {"implemented": 0, "not_implemented": 0, "items": []}

        if gate == "gate2":
            gate1_path = None
            if request.gate1_report:
                gate1_path = Path(request.gate1_report)
                if not gate1_path.is_absolute():
                    gate1_path = REPO_ROOT / request.gate1_report
            if not gate1_path or not gate1_path.exists():
                gate1_path = self._latest_gate1_report(request.product_name, request.product_version)
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
            "work_order_id": work_order_id,
            "review_id": review_id,
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

    def list_work_orders(self, product_name: str | None = None, product_version: str | None = None) -> list[dict]:
        items = []
        for path in WORK_ORDERS_DIR.glob("**/*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if product_name and item.get("product_name") != product_name:
                continue
            if product_version and item.get("product_version") != product_version:
                continue
            items.append({
                "work_order_id": item.get("work_order_id"),
                "review_id": item.get("review_id"),
                "product_name": item.get("product_name"),
                "product_version": item.get("product_version"),
                "gate": item.get("gate"),
                "status": item.get("status"),
                "matched": item.get("matched"),
                "approval_status": item.get("approval_status"),
                "created_at": item.get("created_at"),
                "report_path": item.get("report_path"),
                "report_url": item.get("report_url"),
                "report_download_url": item.get("report_download_url"),
                "work_order_url": item.get("work_order_url"),
            })
        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return items

    def get_work_order(self, work_order_id: str) -> dict:
        for path in WORK_ORDERS_DIR.glob("**/*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if item.get("work_order_id") == work_order_id:
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
