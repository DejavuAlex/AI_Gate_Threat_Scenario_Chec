import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response

from . import config
from .schemas import ApproveRequest, JiraSendRequest, KnowledgeBaseAssistantRequest, KnowledgeBaseUpdateRequest, ReportUpdateRequest, ReviewRunRequest
from .services import jira as jira_service
from .services import report_generator
from .services.knowledge_base import KnowledgeBaseService
from .services.knowledge_base_assistant import KnowledgeBaseAssistantService
from .services.review import ReviewService


def require_external_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
):
    """Require the shared key only for external API and CI/CD task submission.

    Local CLI agents do not call HTTP endpoints. UI task submission uses
    /api/v1/ui/... routes and intentionally does not require this key.
    """
    expected = config.AI_SECURITY_GATE_API_KEY
    if not expected:
        return
    bearer_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()
    if x_api_key == expected or bearer_token == expected:
        return
    raise HTTPException(status_code=401, detail="invalid or missing API key")


router = APIRouter()
review_service = ReviewService()
kb_service = KnowledgeBaseService()
kb_assistant_service = KnowledgeBaseAssistantService()

ALLOWED_SPEC_EXTENSIONS = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}
MAX_SPEC_FILE_SIZE = 10 * 1024 * 1024
MAX_KB_FILE_SIZE = 10 * 1024 * 1024


def _safe_spec_filename(filename: str | None) -> str:
    name = Path((filename or "").replace("\\", "/")).name.strip()
    name = "".join(ch if (ch.isalnum() or ch in {".", "-", "_", " ", "(", ")"}) else "_" for ch in name).strip()
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="invalid spec filename")
    if not Path(name).stem.strip(" ._"):
        raise HTTPException(status_code=400, detail="invalid spec filename")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SPEC_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_SPEC_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"unsupported spec file type; allowed: {allowed}")
    return name


def _unique_spec_path(filename: str) -> Path:
    config.SPECS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.SPECS_DIR / filename
    if not path.exists():
        return path
    original = Path(filename)
    stem, suffix = original.stem, original.suffix
    index = 1
    while True:
        candidate = config.SPECS_DIR / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _spec_item(path: Path) -> dict:
    stat = path.stat()
    rel = path.relative_to(config.SPECS_DIR).as_posix()
    return {
        "filename": path.name,
        "path": f"specs/{rel}",
        "size": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


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


@router.get("/specs")
def list_specs():
    config.SPECS_DIR.mkdir(parents=True, exist_ok=True)
    files = [path for path in config.SPECS_DIR.rglob("*") if path.is_file() and not path.name.startswith(".")]
    return {"items": [_spec_item(path) for path in sorted(files, key=lambda item: item.name.lower())]}


@router.post("/specs/upload")
async def upload_specs(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="no spec files uploaded")

    uploaded = []
    for file in files:
        filename = _safe_spec_filename(file.filename)
        path = _unique_spec_path(filename)
        total = 0
        try:
            with path.open("wb") as output:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_SPEC_FILE_SIZE:
                        raise HTTPException(status_code=413, detail="spec file is too large")
                    output.write(chunk)
            try:
                path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=400, detail="spec file must be UTF-8 text") from exc
            uploaded.append(_spec_item(path))
        except Exception:
            if path.exists():
                path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
    return {"items": uploaded}


@router.post("/security-review/gate1/run", dependencies=[Depends(require_external_api_key)])
def run_gate1(request: ReviewRunRequest):
    return review_service.run("gate1", request)


@router.post("/security-review/gate2/run", dependencies=[Depends(require_external_api_key)])
def run_gate2(request: ReviewRunRequest):
    return review_service.run("gate2", request)


@router.post("/ci/security-review/gate2/run", dependencies=[Depends(require_external_api_key)])
def run_gate2_from_ci(request: ReviewRunRequest):
    request.triggered_by = request.triggered_by or "ci-cd"
    return review_service.run("gate2", request)


@router.post("/ui/security-review/gate1/run")
def run_gate1_from_ui(request: ReviewRunRequest):
    request.triggered_by = request.triggered_by or "ui"
    return review_service.run("gate1", request)


@router.post("/ui/security-review/gate2/run")
def run_gate2_from_ui(request: ReviewRunRequest):
    request.triggered_by = request.triggered_by or "ui"
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


@router.post("/tasks/{task_id}/final-report/jira")
def send_task_final_report_to_jira(task_id: str, request: JiraSendRequest):
    try:
        task = review_service.get_task(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    task_code = task.get("task_code") or task_id
    attachment_name = f"{task_code}-Final-Review-Summary.md"
    markdown = _task_final_report_markdown(task)
    summary = request.summary or f"[AI Security Gate] Final review summary {task_code}"
    labels = request.labels or ["ai-security-gate", "final-report"]
    # Keep the issue description short; the full task summary rides along as an attachment.
    description = markdown if request.full_report else report_generator.build_task_jira_summary(task, attachment_name)
    try:
        created = jira_service.create_issue(summary, description, labels)
    except jira_service.JiraNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except jira_service.JiraError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    attachment_error = None
    try:
        jira_service.attach_bytes(created["issue_key"], markdown.encode("utf-8"), attachment_name)
    except jira_service.JiraError as exc:
        attachment_error = str(exc)
    result = {"task_id": task_id, **created}
    if attachment_error:
        result["attachment_error"] = attachment_error
    return result


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


@router.get("/integrations/jira")
def jira_settings():
    return jira_service.settings()


@router.post("/reports/{review_id}/jira")
def send_report_to_jira(review_id: str, request: JiraSendRequest):
    try:
        review = review_service.get(review_id)
    except FileNotFoundError:
        review = {}
    gate = review.get("gate", "")
    summary = request.summary or f"[AI Security Gate] {gate or 'Review'} report {review_id}"
    labels = request.labels or ["ai-security-gate"] + ([gate] if gate else [])
    # The issue description carries only the highlights; the full Markdown
    # report is attached below so reviewers are not forced to scroll it in Jira.
    if review and not request.full_report:
        description = report_generator.build_jira_summary(review)
    else:
        try:
            description = review_service.get_report_content(review_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="report not found")
    try:
        created = jira_service.create_issue(summary, description, labels)
    except jira_service.JiraNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except jira_service.JiraError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    attachment_error = None
    try:
        report_path = review_service.get_report_path(review_id)
        jira_service.attach_file(created["issue_key"], report_path, filename=f"{review_id}.md")
    except FileNotFoundError:
        attachment_error = "report file not found"
    except jira_service.JiraError as exc:
        attachment_error = str(exc)
    result = {"review_id": review_id, **created}
    if attachment_error:
        result["attachment_error"] = attachment_error
    return result


@router.put("/reports/{review_id}")
def update_report(review_id: str, request: ReportUpdateRequest):
    try:
        return review_service.update_report(review_id, request.content, request.reviewer, request.comment)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="review not found")


@router.post("/reports/{review_id}/approve")
def approve_report(review_id: str, request: ApproveRequest, background_tasks: BackgroundTasks):
    try:
        result = review_service.approve(review_id, request.reviewer, request.comment)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="review not found")
    if result.get("auto_gate2_triggered"):
        background_tasks.add_task(review_service.run_auto_gate2, review_id)
    return result


@router.post("/security-review/gate1/{review_id}/approve")
def approve_gate1_report(review_id: str, request: ApproveRequest, background_tasks: BackgroundTasks):
    return approve_report(review_id, request, background_tasks)


@router.post("/security-review/gate2/{review_id}/approve")
def approve_gate2_report(review_id: str, request: ApproveRequest, background_tasks: BackgroundTasks):
    return approve_report(review_id, request, background_tasks)


@router.get("/knowledge-base/{gate}/catalog")
def get_knowledge_base_catalog(gate: str):
    try:
        return {"items": kb_service.list_catalog(gate)}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/knowledge-base/{gate}/upload")
async def upload_knowledge_base(
    gate: str,
    file: UploadFile = File(...),
    knowledge_base_id: str = Form(...),
    updated_by: str = Form("security.admin@example.com"),
    change_reason: str = Form("Uploaded from UI"),
    version: str | None = Form(default=None),
    name: str | None = Form(default=None),
    category: str | None = Form(default=None),
    risk_level: str | None = Form(default=None),
    description: str | None = Form(default=None),
):
    total = 0
    chunks = []
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_KB_FILE_SIZE:
                raise HTTPException(status_code=413, detail="knowledge base file is too large")
            chunks.append(chunk)
        try:
            content = json.loads(b"".join(chunks).decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="knowledge base file must be UTF-8 JSON") from exc
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"invalid knowledge base JSON: {exc.msg}") from exc
        if not isinstance(content, dict):
            raise HTTPException(status_code=400, detail="knowledge base JSON must be an object")
        saved = kb_service.save_uploaded_update(
            gate,
            content,
            knowledge_base_id,
            updated_by,
            change_reason,
            version=version,
            name=name,
            category=category,
            risk_level=risk_level,
            description=description,
        )
        catalog = kb_service.list_catalog(gate)
        item = next((entry for entry in catalog if entry.get("knowledge_base_id") == saved.get("metadata", {}).get("knowledge_base_id")), None)
        return {"item": item, "content": saved}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        await file.close()


@router.post("/knowledge-base/{gate}/assistant/propose")
def propose_knowledge_base_scenario(gate: str, request: KnowledgeBaseAssistantRequest):
    try:
        knowledge_base = kb_service.load(gate, request.knowledge_base_id)
        return kb_assistant_service.propose(
            gate,
            knowledge_base,
            request.message,
            conversation=[item.model_dump() for item in request.conversation],
            draft_scenario=request.draft_scenario,
            draft_action=request.draft_action,
            draft_matched_scenario_id=request.draft_matched_scenario_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"assistant generation failed: {exc}")


@router.get("/knowledge-base/{gate}")
def get_knowledge_base(gate: str, knowledge_base_id: str = Query(default="default")):
    try:
        return kb_service.load(gate, knowledge_base_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/knowledge-base/{gate}/history")
def get_knowledge_base_history(gate: str, knowledge_base_id: str | None = Query(default=None)):
    try:
        return {"items": kb_service.list_history(gate, knowledge_base_id)}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/knowledge-base/{gate}/history/{history_id}")
def get_knowledge_base_history_detail(gate: str, history_id: str):
    try:
        return kb_service.get_history(gate, history_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/knowledge-base/{gate}")
def update_knowledge_base(gate: str, request: KnowledgeBaseUpdateRequest):
    try:
        return kb_service.save_manual_update(gate, request.content, request.updated_by, request.change_reason, request.version, request.knowledge_base_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
