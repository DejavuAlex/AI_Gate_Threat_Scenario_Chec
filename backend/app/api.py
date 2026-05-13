from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from .schemas import ApproveRequest, KnowledgeBaseUpdateRequest, ReportUpdateRequest, ReviewRunRequest
from .services.knowledge_base import KnowledgeBaseService
from .services.review import ReviewService

router = APIRouter()
review_service = ReviewService()
kb_service = KnowledgeBaseService()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/security-review/gate1/run")
def run_gate1(request: ReviewRunRequest):
    return review_service.run("gate1", request)


@router.post("/security-review/gate2/run")
def run_gate2(request: ReviewRunRequest):
    return review_service.run("gate2", request)


@router.get("/security-review/{gate}/{review_id}")
def get_review(gate: str, review_id: str):
    try:
        review = review_service.get(review_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="review not found")
    if review.get("gate") != gate:
        raise HTTPException(status_code=404, detail="review not found for gate")
    return review


@router.get("/reports/{review_id}", response_class=PlainTextResponse)
def get_report(review_id: str):
    try:
        return review_service.get_report_content(review_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="report not found")


@router.put("/reports/{review_id}")
def update_report(review_id: str, request: ReportUpdateRequest):
    try:
        return review_service.update_report(review_id, request.content, request.reviewer, request.comment)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="review not found")


@router.post("/reports/{review_id}/approve")
def approve_report(review_id: str, request: ApproveRequest):
    try:
        return review_service.approve(review_id, request.reviewer, request.comment)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="review not found")


@router.post("/security-review/gate1/{review_id}/approve")
def approve_gate1_report(review_id: str, request: ApproveRequest):
    return approve_report(review_id, request)


@router.get("/knowledge-base/{gate}")
def get_knowledge_base(gate: str):
    try:
        return kb_service.load(gate)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/knowledge-base/{gate}")
def update_knowledge_base(gate: str, request: KnowledgeBaseUpdateRequest):
    try:
        return kb_service.save_manual_update(gate, request.content, request.updated_by, request.change_reason, request.version)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
