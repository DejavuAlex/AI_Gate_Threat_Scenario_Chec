from backend.app.schemas import ReviewRunRequest
from backend.app.services.gate2_verifier import verify_gate1_controls
from backend.app.services.report_generator import generate_gate2_report


def test_gate2_traceability_uses_only_gate1_final_controls_and_reports_evidence_quality():
    gate1_report = """# Gate1 Report

#### Risk Control

- 强制MFA

## 5. Final Security Control Requirements

- 白名单限制文件后缀，禁止可执行类型
- 服务端校验文件头内容，防止文件伪装
- SPF/DKIM/DMARC校验
- SMTP服务配置发信速率限制

## 6. Human Review
"""
    gate2_documents = """# Implementation Plan

- 文件上传场景：限制文件类型、校验 Magic Number、限制文件大小。
- API Rate Limit: token bucket per user.
"""

    result = verify_gate1_controls(gate2_documents, {"matched_scenarios": []}, gate1_report)

    assert [item["control"] for item in result["items"]] == [
        "白名单限制文件后缀，禁止可执行类型",
        "服务端校验文件头内容，防止文件伪装",
        "SPF/DKIM/DMARC校验",
        "SMTP服务配置发信速率限制",
    ]
    assert [item["result"] for item in result["items"]] == ["Partial", "Documented", "No Evidence", "No Evidence"]
    assert result["documented"] == 1
    assert result["partial"] == 1
    assert result["no_evidence"] == 2
    assert "Magic Number" in result["items"][1]["evidence"]
    assert result["items"][1]["evidence_basis"] == "1/1 configured control concepts"
    assert result["items"][1]["concept_coverage"] == 1.0
    assert all(item["control"] != "强制MFA" for item in result["items"])


def test_gate2_traceability_without_gate1_baseline_is_explicitly_not_evaluated():
    result = verify_gate1_controls("OAuth2.0 is configured.", {"matched_scenarios": []}, "")

    assert result["baseline_available"] is False
    assert result["items"] == []
    assert result["controls_source"] == "No Gate1 final-control baseline available"


def test_gate2_report_has_one_control_matrix_instead_of_repeated_requirement_sections():
    request = ReviewRunRequest(
        project_id="demo",
        product_name="Demo",
        product_version="v1",
        documents=["specs/architecture.md"],
        threshold=0.78,
        triggered_by="pytest",
    )
    scenario_control = "Require API rate limiting"
    gate1_control = "强制MFA"
    match_result = {
        "matched": True,
        "matched_scenarios": [
            {
                "scenario": {
                    "id": "G2-TEST-001",
                    "name": "API Security",
                    "problem_scenario": "Is an API exposed?",
                    "category": "API",
                    "risk": {"level": "Yellow", "P1": 6, "P2": 6, "P": 3, "severity": 8},
                    "risk_identification": ["API abuse"],
                    "security_control_requirements": [scenario_control],
                },
                "matched_evidence": ["The service exposes a REST API."],
                "score_breakdown": {"keyword_match": 1.0},
                "final_score": 0.9,
            }
        ],
        "story_assessments": [],
    }
    verification = {
        "baseline_available": True,
        "controls_source": "Gate1 Final Security Control Requirements",
        "documented": 0,
        "partial": 1,
        "no_evidence": 0,
        "implemented": 0,
        "not_implemented": 1,
        "items": [
            {
                "control": gate1_control,
                "result": "Partial",
                "evidence": "管理员登录需要二次验证。",
                "required_action": "Clarify that MFA is mandatory.",
            }
        ],
    }

    report = generate_gate2_report(
        "gate2-review-test",
        "gate2-work-order-test",
        request,
        {"knowledge_base_version": "1.0.1"},
        match_result,
        verification,
    )

    assert report.count(scenario_control) == 1
    assert report.count(gate1_control) == 1
    assert "## 5. Gate1-to-Gate2 Security Control Traceability" in report
    assert "| Gate1 Control | Traceability | Evidence Basis | Gate2 Evidence | Required Action |" in report
    assert "## 6. Gate2 Review Decision" in report
    assert "## 7. Human Review" in report
    assert "#### Required Security Controls" not in report
    assert "## 6. Non-compliance Findings" not in report
    assert "Optimized Gate2 Requirement Updates" not in report
    assert "## 8. Final Security Control Requirements" not in report
    assert "Gate2 review completed." not in report
    assert "Decision: Gate2 Document Update Required" in report
