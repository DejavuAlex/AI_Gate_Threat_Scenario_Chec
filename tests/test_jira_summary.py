"""Tests for the condensed review summary sent as the Jira issue description."""

from backend.app.services.report_generator import (
    SUMMARY_MAX_CONTROLS,
    SUMMARY_MAX_SCENARIOS,
    build_jira_summary,
)


def _review(**overrides) -> dict:
    review = {
        "review_id": "gate1-review-001",
        "gate": "gate1",
        "product_name": "Demo Product",
        "product_version": "1.0.0",
        "task_code": "TASK-000001",
        "task_name": "Demo review",
        "knowledge_base_id": "default",
        "knowledge_base_version": "1.2.0",
        "matched": True,
        "llm_enabled": True,
        "created_at": "2026-09-04T00:00:00+00:00",
        "approval_status": "approved",
        "approved_by": "reviewer@example.com",
        "approved_at": "2026-09-04T01:00:00+00:00",
        "request": {"threshold": 0.78},
        "match_result": {
            "matched_scenarios": [
                {
                    "scenario": {
                        "id": "G1-001",
                        "name": "File upload",
                        "category": "Data",
                        "risk": {"level": "Red"},
                        "security_control_requirements": ["Validate file type", "Scan for malware"],
                    },
                    "final_score": 0.91,
                },
                {
                    "scenario": {
                        "id": "G1-002",
                        "name": "Open redirect",
                        "risk": {"level": "Yellow"},
                        "security_control_requirements": ["Validate file type", "Allowlist redirects"],
                    },
                    "final_score": 0.8,
                },
            ]
        },
    }
    review.update(overrides)
    return review


def test_summary_is_far_shorter_than_the_full_report():
    summary = build_jira_summary(_review())

    assert len(summary) < 2500
    assert "#### Score Calculation" not in summary
    assert "Full report is attached to this issue as `gate1-review-001.md`." in summary


def test_summary_lists_metadata_scenarios_and_deduplicated_controls():
    summary = build_jira_summary(_review())

    assert "| Review ID | gate1-review-001 |" in summary
    assert "| Product / Version | Demo Product / 1.0.0 |" in summary
    assert "| Knowledge Base | default (1.2.0) |" in summary
    assert "| Result | Matched 2 threat scenario(s) |" in summary
    assert "| Highest Risk | Red |" in summary
    assert "| G1-001 File upload | Red | 0.91 |" in summary
    # "Validate file type" appears in both scenarios but must be listed once.
    assert summary.count("Validate file type") == 1
    assert "## Required Security Controls (3)" in summary


def test_unmatched_review_reports_the_reason_and_skips_empty_sections():
    review = _review(
        matched=False,
        match_result={"matched_scenarios": [], "unmatched_message": "No security risk identified"},
    )
    summary = build_jira_summary(review)

    assert "| Result | No security risk identified |" in summary
    assert "Matched Threat Scenarios" not in summary
    assert "Required Security Controls" not in summary


def test_gate2_adds_control_verification_and_action_items():
    review = _review(
        review_id="gate2-review-001",
        gate="gate2",
        gate1_control_verification={
            "baseline_available": True,
            "documented": 4,
            "partial": 1,
            "no_evidence": 2,
            "items": [
                {"control": "Covered control", "result": "Documented", "required_action": "None."},
                {"control": "Weak control", "result": "Partial", "required_action": "Add design detail."},
                {"control": "Missing control", "result": "No Evidence", "required_action": "Document the design."},
            ],
        },
    )
    summary = build_jira_summary(review)

    assert "## Gate1 Control Verification" in summary
    assert "| No Evidence | 2 |" in summary
    assert "### Controls Needing Action (2)" in summary
    assert "- **Partial**: Weak control — Add design detail." in summary
    assert "Covered control" not in summary


def test_long_lists_are_capped_with_a_pointer_to_the_attachment():
    total = max(SUMMARY_MAX_SCENARIOS, SUMMARY_MAX_CONTROLS) + 5
    scenarios = [
        {
            "scenario": {
                "id": f"G1-{index:03d}",
                "name": f"Scenario {index}",
                "risk": {"level": "Yellow"},
                "security_control_requirements": [f"Control {index}"],
            },
            "final_score": 0.8,
        }
        for index in range(total)
    ]
    summary = build_jira_summary(_review(match_result={"matched_scenarios": scenarios}))

    assert f"| ... {total - SUMMARY_MAX_SCENARIOS} more in the attached report | | |" in summary
    assert f"... {total - SUMMARY_MAX_CONTROLS} more in the attached report" in summary


def test_pipes_in_values_are_escaped_for_the_table():
    review = _review(
        match_result={
            "matched_scenarios": [
                {
                    "scenario": {"id": "G1-001", "name": "A | B", "risk": {"level": "Red"}},
                    "final_score": 0.9,
                }
            ]
        }
    )

    assert "| G1-001 A \\| B | Red | 0.9 |" in build_jira_summary(review)


def test_legacy_reviews_without_match_result_still_list_scenarios():
    review = _review(
        match_result={},
        matched_scenarios=[
            {"scenario_id": "G1-009", "scenario_name": "Email sending", "risk_level": "Yellow", "final_score": 0.85}
        ],
    )
    summary = build_jira_summary(review)

    assert "| G1-009 Email sending | Yellow | 0.85 |" in summary
