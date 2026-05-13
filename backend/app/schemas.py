from typing import Any, Literal
from pydantic import BaseModel, Field


class ReviewRunRequest(BaseModel):
    project_id: str = "demo"
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
    gate: Literal["gate1", "gate2"]
    status: str
    matched: bool
    matched_scenarios: list[MatchedScenario]
    report_path: str
    report_url: str
    approval_status: str = "pending"
