from typing import Any, Literal
from pydantic import BaseModel, Field


class ReviewRunRequest(BaseModel):
    project_id: str = "demo"
    product_name: str = "Demo Security Gate Product"
    product_version: str = "v1.0.0"
    task_id: str | None = None
    task_name: str | None = None
    repository: str | None = None
    branch: str | None = None
    documents: list[str] = Field(default_factory=list)
    knowledge_base_version: str = "latest"
    threshold: float = 0.78
    triggered_by: str = "manual"
    gate1_report: str | None = None


class ApproveRequest(BaseModel):
    reviewer: str
    comment: str | None = None


class ReportUpdateRequest(BaseModel):
    content: str
    reviewer: str | None = None
    comment: str | None = None


class KnowledgeBaseUpdateRequest(BaseModel):
    version: str
    updated_by: str
    change_reason: str
    content: dict[str, Any]


class MatchedScenario(BaseModel):
    scenario_id: str
    scenario_name: str
    final_score: float
    risk_level: str | None = None


class ReviewResponse(BaseModel):
    review_id: str
    work_order_id: str
    task_id: str
    product_name: str
    product_version: str
    gate: Literal["gate1", "gate2"]
    status: str
    matched: bool
    matched_scenarios: list[MatchedScenario]
    report_path: str
    report_url: str
    report_download_url: str
    work_order_url: str
    task_url: str
    approval_status: str = "pending"
