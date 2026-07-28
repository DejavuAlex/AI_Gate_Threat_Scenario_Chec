from pathlib import Path

from backend.app.schemas import ApproveRequest, ReviewRunRequest
from backend.app.services.documents import extract_stories
from backend.app.services.matching import MatchingEngine
from backend.app.services.report_generator import generate_gate1_report


def test_review_run_request_supports_task_workflow_fields():
    request = ReviewRunRequest(
        product_name="Demo",
        product_version="v1",
        task_id="TASK-000001",
        task_name="Demo-v1-gate1",
        documents=["specs/product-requirements.md"],
        gate2_documents=["specs/architecture.md"],
        auto_run_gate2_on_gate1_approval=True,
    )

    assert request.task_id == "TASK-000001"
    assert request.task_name == "Demo-v1-gate1"
    assert request.gate2_documents == ["specs/architecture.md"]
    assert request.auto_run_gate2_on_gate1_approval is True


def test_approve_request_comment_is_optional():
    request = ApproveRequest(reviewer="security.reviewer@example.com")

    assert request.reviewer == "security.reviewer@example.com"
    assert request.comment is None


def test_extract_stories_splits_markdown_headings_and_falls_back_to_document():
    docs = [
        {
            "path": "specs/user-stories.md",
            "content": "# US-001 Login\nUsers can login.\n\n## US-002 Export\nUsers can export data.",
        },
        {"path": "specs/plain.txt", "content": "Plain requirement text."},
    ]

    stories = extract_stories(docs)

    assert [story["story_id"] for story in stories] == ["US-001", "US-002", "STORY-003"]
    assert stories[0]["title"] == "US-001 Login"
    assert stories[2]["title"] == "plain.txt"


def test_matching_engine_assess_stories_returns_top_scenario_scores():
    kb = {
        "matching_policy": {
            "score_formula": {
                "semantic_similarity": 0.35,
                "keyword_match": 0.25,
                "business_context": 0.2,
                "negative_evidence_adjustment": 0.1,
                "llm_confidence": 0.1,
            }
        },
        "scenarios": [
            {
                "id": "S-001",
                "name": "Sensitive Data Export",
                "problem_scenario": "Export sensitive customer data",
                "category": "Data",
                "risk_identification": ["sensitive data"],
                "business_indicators": ["export", "customer data"],
                "technical_indicators": [],
                "security_control_requirements": ["Require approval before export"],
                "negative_indicators": [],
                "risk": {"level": "High"},
            }
        ],
    }
    engine = MatchingEngine(kb, threshold=0.5)

    assessments = engine.assess_stories(
        [{"story_id": "US-001", "title": "Export", "document_path": "specs/a.md", "content": "Users export customer data."}],
        "gate1",
    )

    assert assessments[0]["story_id"] == "US-001"
    assert assessments[0]["matched"] is True
    assert assessments[0]["top_scenarios"][0]["scenario_id"] == "S-001"
    assert assessments[0]["top_scenarios"][0]["risk_level"] == "High"


def test_gate1_report_includes_task_metadata_and_story_assessment():
    request = ReviewRunRequest(
        project_id="demo",
        product_name="Demo",
        product_version="v1",
        repository="quy7_roche/AI_Security_Gate",
        branch="main",
        documents=["specs/user-stories.md"],
        threshold=0.78,
        triggered_by="pytest",
    )
    kb = {"knowledge_base_version": "1.0.0"}
    match_result = {
        "matched": False,
        "unmatched_message": "No risk.",
        "matched_scenarios": [],
        "story_assessments": [
            {
                "story_id": "US-001",
                "title": "Login",
                "document_path": "specs/user-stories.md",
                "matched": False,
                "top_scenarios": [],
            }
        ],
    }

    report = generate_gate1_report(
        "gate1-review-test",
        "task-000001-gate1-test",
        request,
        kb,
        match_result,
        {"task_serial_no": 1, "task_code": "TASK-000001", "task_name": "Demo-v1-gate1"},
    )

    assert "Task Code: TASK-000001" in report
    assert "Story-by-Story Threat Scenario Assessment" in report
    assert "US-001" in report
    assert "No risk." in report


def test_gate1_report_adds_threat_modeling_sections_without_replacing_original_content():
    request = ReviewRunRequest(
        project_id="demo",
        product_name="Demo",
        product_version="v1",
        documents=["specs/user-stories.md"],
        threshold=0.78,
        triggered_by="pytest",
    )
    scenario = {
        "id": "S-001",
        "name": "Sensitive Data Export",
        "problem_scenario": "Can users export sensitive customer data?",
        "category": "Data Export",
        "risk": {"level": "Yellow", "P1": 6, "P2": 6, "P": 3, "severity": 8},
        "risk_identification": ["PII leakage through bulk export"],
        "security_control_requirements": ["Require approval before export"],
    }
    match_result = {
        "matched": True,
        "matched_scenarios": [
            {
                "scenario": scenario,
                "matched_evidence": ["Users export customer data"],
                "score_breakdown": {"keyword_match": 1.0},
                "final_score": 0.95,
            }
        ],
        "story_assessments": [],
    }

    report = generate_gate1_report("review-1", "work-order-1", request, {"knowledge_base_version": "1.0.0"}, match_result)

    assert "#### Threat Scenario" in report
    assert "#### Initial Risk Estimation" in report
    assert "#### Risk Control" in report
    assert "#### Residual Risk Estimation" in report
    assert "Control-dependent / Pending validation" in report
    assert "#### Scenario Content" in report
    assert "#### Required Security Controls" in report
    assert "Require approval before export" in report
