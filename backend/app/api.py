from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse, Response

from . import config
from .schemas import ApproveRequest, KnowledgeBaseUpdateRequest, ReportUpdateRequest, ReviewRunRequest
from .services.knowledge_base import KnowledgeBaseService
from .services.review import ReviewService


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
):
    expected = config.AI_SECURITY_GATE_API_KEY
    if not expected:
        return
    bearer_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()
    if x_api_key == expected or bearer_token == expected:
        return
    raise HTTPException(status_code=401, detail="invalid or missing API key")


router = APIRouter(dependencies=[Depends(require_api_key)])
review_service = ReviewService()
kb_service = KnowledgeBaseService()


def _task_final_report_markdown(task: dict) -> str:
    approval = task.get("approval", {}) or {}
    auto_gate2 = task.get("auto_gate2", {}) or {}
    reports = task.get("reports", {}) or {}
    activities = task.get("activities", []) or []
    lines = [
        "# AI Gate Final Review Task Summary",
        "",
        "## 1. Task Identity",
        "",
        f"- Task Serial No: {task.get('task_serial_no', '')}",
        f"- Task Code: {task.get('task_code', '')}",
        f"- Task ID: {task.get('task_id', '')}",
        f"- Task Name: {task.get('task_name', '')}",
        f"- Product Name: {task.get('product_name', '')}",
        f"- Product Version: {task.get('product_version', '')}",
        f"- Project ID: {task.get('project_id', '')}",
        f"- Repository: {task.get('repository', '')}",
        f"- Branch: {task.get('branch', '')}",
        f"- Triggered By: {task.get('triggered_by', '')}",
        f"- Created At: {task.get('created_at', '')}",
        f"- Updated At: {task.get('updated_at', '')}",
        "",
        "## 2. Workflow Status",
        "",
        f"- Status: {task.get('status', '')}",
        f"- Flow Status: {task.get('flow_status', '')}",
        f"- Final Result: {task.get('final_result', '')}",
        f"- Auto Gate2 Enabled: {auto_gate2.get('enabled', '')}",
        f"- Auto Gate2 Status: {auto_gate2.get('status', '')}",
        f"- Auto Gate2 Review ID: {auto_gate2.get('gate2_review_id', '')}",
        "",
        "## 3. Approval Summary",
        "",
        "| Gate | Review ID | Approved By | Approved At | Comment |",
        "|---|---|---|---|---|",
    ]
    for gate in ["gate1", "gate2"]:
        item = approval.get(gate) or {}
        lines.append(f"| {gate} | {item.get('review_id', '')} | {item.get('approved_by', '')} | {item.get('approved_at', '')} | {item.get('comment', '')} |")
    lines.extend(["", "## 4. Generated Reports", "", "| Gate | Review ID | Activity ID | View URL | Download URL | Report Path |", "|---|---|---|---|---|---|"])
    has_report = False
    for gate in ["gate1", "gate2"]:
        for item in reports.get(gate, []) or []:
            has_report = True
            lines.append(f"| {gate} | {item.get('review_id', '')} | {item.get('work_order_id', '')} | {item.get('report_url', '')} | {item.get('report_download_url', '')} | {item.get('report_path', '')} |")
    if not has_report:
        lines.append("| - | - | - | - | - | - |")
    lines.extend(["", "## 5. Gate Run Timeline", "", "| Created At | Gate | Activity Name | Review ID | Matched | Approval Status | Triggered By |", "|---|---|---|---|---|---|---|"])
    for item in activities:
        lines.append(f"| {item.get('created_at', '')} | {item.get('gate', '')} | {item.get('activity_name', '')} | {item.get('review_id', '')} | {item.get('matched', '')} | {item.get('approval_status', '')} | {item.get('triggered_by', '')} |")
    if not activities:
        lines.append("| - | - | - | - | - | - | - |")
    lines.extend(["", "## 6. Detailed Report References", "", "For story-level scenario scoring, risk scoring, and final security controls, open the Gate1/Gate2 detailed reports listed above.", ""])
    return "\n".join(lines)


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
    return review_service.run("gate2", request)


@router.post("/ci/security-review/gate2/run")
def run_gate2_from_ci(request: ReviewRunRequest):
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


@router.get("/tasks/{task_id}/final-report", response_class=PlainTextResponse)
def get_task_final_report(task_id: str):
    try:
        task = review_service.get_task(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    return _task_final_report_markdown(task)


@router.get("/tasks/{task_id}/final-report/download")
def download_task_final_report(task_id: str):
    try:
        task = review_service.get_task(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    filename = f"{task.get('task_code') or task_id}-Final-Review-Summary.md"
    return Response(content=_task_final_report_markdown(task), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/work-orders")
def list_work_orders(product_name: str | None = Query(default=None), product_version: str | None = Query(default=None), task_id: str | None = Query(default=None)):
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
