import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..config import REPORTS_DIR, REVIEWS_DIR, REPO_ROOT
from ..schemas import ReviewRunRequest
from .documents import read_documents
from .gate2_verifier import verify_gate1_controls
from .knowledge_base import KnowledgeBaseService
from .matching import MatchingEngine
from .report_generator import generate_gate1_report, generate_gate2_report


class ReviewService:
    def __init__(self):
        self.kb_service = KnowledgeBaseService()

    def _store_review(self, review_id: str, payload: dict) -> None:
        path = REVIEWS_DIR / f"{review_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_review(self, review_id: str) -> dict:
        path = REVIEWS_DIR / f"{review_id}.json"
        if not path.exists():
            raise FileNotFoundError(review_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def run(self, gate: str, request: ReviewRunRequest) -> dict:
        gate = gate.lower()
        review_id = f"{gate}-review-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        kb = self.kb_service.load(gate)
        document_text, docs = read_documents(request.documents)
        matcher = MatchingEngine(kb, request.threshold)
        match_result = matcher.match(document_text, gate)

        gate1_report_text = ""
        verification = {"implemented": 0, "not_implemented": 0, "items": []}
        if gate == "gate2":
            if request.gate1_report:
                gate1_path = Path(request.gate1_report)
                if not gate1_path.is_absolute():
                    gate1_path = REPO_ROOT / request.gate1_report
                if gate1_path.exists():
                    gate1_report_text = gate1_path.read_text(encoding="utf-8")
            verification = verify_gate1_controls(document_text, match_result, gate1_report_text)
            report = generate_gate2_report(review_id, request, kb, match_result, verification)
            report_file = REPORTS_DIR / "Security-Review-Gate2.md"
        else:
            report = generate_gate1_report(review_id, request, kb, match_result)
            report_file = REPORTS_DIR / "Security-Review-Gate1.md"

        report_file.write_text(report, encoding="utf-8")
        response = {
            "review_id": review_id,
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
            "report_path": str(report_file.relative_to(REPO_ROOT)),
            "report_url": f"/api/v1/reports/{review_id}",
            "approval_status": "pending",
            "gate1_control_verification": verification,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "request": request.model_dump(),
            "documents": docs,
            "match_result": match_result,
        }
        self._store_review(review_id, response)
        return response

    def get(self, review_id: str) -> dict:
        return self._load_review(review_id)

    def get_report_content(self, review_id: str) -> str:
        review = self._load_review(review_id)
        path = REPO_ROOT / review["report_path"]
        return path.read_text(encoding="utf-8")

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
