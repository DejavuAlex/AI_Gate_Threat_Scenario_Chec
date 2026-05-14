from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from .schemas import ApproveRequest, KnowledgeBaseUpdateRequest, ReportUpdateRequest, ReviewRunRequest
from .services.knowledge_base import KnowledgeBaseService
from .services.review import ReviewService

router = APIRouter()
review_service = ReviewService()
kb_service = KnowledgeBaseService()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/dashboard/stats")
def dashboard_stats():
    return review_service.dashboard_stats()


@router.get("/catalog")
def catalog():
    return review_service.catalog()


@router.post("/security-review/gate1/run")
def run_gate1(request: ReviewRunRequest):
    return review_service.run("gate1", request)


@router.post("/security-review/gate2/run")
def run_gate2(request: ReviewRunRequest):
    """Direct Gate2 entrypoint for UI/API/CI/CD callers.

    If task_id and gate1_report are provided, Gate2 runs under the existing task
    and verifies against that Gate1 report. If gate1_report is omitted, the
    service tries to use the latest Gate1 report from the same task.
    """
    return review_service.run("gate2", request)


@router.post("/ci/security-review/gate2/run")
def run_gate2_from_ci(request: ReviewRunRequest):
    """CI/CD-friendly Gate2 alias.

    This endpoint is intentionally equivalent to /security-review/gate2/run but
    makes pipeline integrations easier to discover and document.
    """
    request.triggered_by = request.triggered_by or "ci-cd"
    return review_service.run("gate2", request)


@router.get("/tasks")
def list_tasks(product_name: str | None = Query(default=None), product_version: str | None = Query(default=None)):
    return {"items": review_service.list_tasks(product_name=product_name, product_version=product_version)}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    try:
        return review_service.get_task(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")


@router.get("/work-orders")
def list_work_orders(
    product_name: str | None = Query(default=None),
    product_version: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
):
    return {"items": review_service.list_work_orders(product_name=product_name, product_version=product_version, task_id=task_id)}


@router.get("/work-orders/{work_order_id}")
def get_work_order(work_order_id: str):
    try:
        return review_service.get_work_order(work_order_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="work order not found")


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


@router.get("/reports/{review_id}/download")
def download_report(review_id: str):
    try:
        path = review_service.get_report_path(review_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(path=path, filename=path.name, media_type="text/markdown")


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


@router.post("/security-review/gate2/{review_id}/approve")
def approve_gate2_report(review_id: str, request: ApproveRequest):
    return approve_report(review_id, request)


@router.get("/knowledge-base/{gate}")
def get_knowledge_base(gate: str):
    try:
        return kb_service.load(gate)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/knowledge-base/{gate}/history")
def get_knowledge_base_history(gate: str):
    try:
        return {"items": kb_service.list_history(gate)}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/knowledge-base/{gate}")
def update_knowledge_base(gate: str, request: KnowledgeBaseUpdateRequest):
    try:
        return kb_service.save_manual_update(gate, request.content, request.updated_by, request.change_reason, request.version)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
