from datetime import datetime, timezone
from typing import Any


def _scenario_markdown(item: dict[str, Any]) -> str:
    scenario = item["scenario"]
    risk = scenario.get("risk", {})
    lines = [
        f"### Scenario: {scenario.get('id')} {scenario.get('name')}",
        "",
        "#### Scenario Content",
        "",
        f"- Problem Scenario: {scenario.get('problem_scenario', '')}",
        f"- Category: {scenario.get('category', '')}",
        f"- Risk: {risk.get('level', '')}",
        f"- P1: {risk.get('P1', '')}",
        f"- P2: {risk.get('P2', '')}",
        f"- P: {risk.get('P', '')}",
        f"- Severity: {risk.get('severity', '')}",
        "",
        "#### Risk Identification",
        "",
    ]
    lines.extend([f"- {risk_text}" for risk_text in scenario.get("risk_identification", [])])
    lines.extend(["", "#### Matched Evidence", ""])
    if item.get("matched_evidence"):
        lines.extend([f"- {e}" for e in item["matched_evidence"]])
    else:
        lines.append("- 无直接关键词证据，基于语义和上下文匹配。")
    lines.extend(["", "#### Score Calculation", "", "| Metric | Score |", "|---|---:|"])
    for key, value in item.get("score_breakdown", {}).items():
        lines.append(f"| {key} | {value} |")
    lines.append(f"| Final Score | {item.get('final_score')} |")
    lines.extend(["", "#### Required Security Controls", ""])
    lines.extend([f"- {control}" for control in scenario.get("security_control_requirements", [])])
    lines.append("")
    return "\n".join(lines)


def generate_gate1_report(review_id: str, request: Any, kb: dict[str, Any], match_result: dict[str, Any]) -> str:
    lines = [
        "# Security Review Gate1 Report",
        "",
        "## 1. Review Metadata",
        "",
        f"- Review ID: {review_id}",
        "- Gate: Gate1",
        "- Review Type: Business Requirement Security Review",
        f"- Review Time: {datetime.now(timezone.utc).isoformat()}",
        f"- Repository: {request.repository or ''}",
        f"- Branch: {request.branch or ''}",
        f"- Triggered By: {request.triggered_by}",
        f"- Knowledge Base Version: {kb.get('knowledge_base_version')}",
        f"- Match Threshold: {request.threshold}",
        "- Approval Status: Pending",
        "",
        "## 2. Input Documents",
        "",
    ]
    lines.extend([f"- {doc}" for doc in request.documents])
    lines.extend(["", "## 3. Matching Result", ""])
    if not match_result.get("matched"):
        lines.extend([match_result.get("unmatched_message", "未匹配上任何威胁场景，本次安全评估确认无安全风险。"), ""])
    else:
        lines.append("### 3.1 Matched Threat Scenarios")
        lines.append("")
        for item in match_result.get("matched_scenarios", []):
            lines.append(_scenario_markdown(item))
    lines.extend([
        "", "## 4. Final Security Control Requirements", ""
    ])
    controls = []
    for item in match_result.get("matched_scenarios", []):
        controls.extend(item["scenario"].get("security_control_requirements", []))
    if controls:
        lines.extend([f"- {control}" for control in dict.fromkeys(controls)])
    else:
        lines.append("- 无新增安全控制要求。")
    lines.extend([
        "", "## 5. Human Review", "",
        "- Status: Pending",
        "- Reviewer:",
        "- Review Comment:",
        "- Approved At:",
        ""
    ])
    return "\n".join(lines)


def generate_gate2_report(review_id: str, request: Any, kb: dict[str, Any], match_result: dict[str, Any], verification: dict[str, Any]) -> str:
    lines = [
        "# Security Review Gate2 Report",
        "",
        "## 1. Review Metadata",
        "",
        f"- Review ID: {review_id}",
        "- Gate: Gate2",
        "- Review Type: Architecture and Technical Requirement Security Review",
        f"- Review Time: {datetime.now(timezone.utc).isoformat()}",
        f"- Repository: {request.repository or ''}",
        f"- Branch: {request.branch or ''}",
        f"- Triggered By: {request.triggered_by}",
        f"- Gate2 Knowledge Base Version: {kb.get('knowledge_base_version')}",
        f"- Gate1 Report: {request.gate1_report or ''}",
        f"- Match Threshold: {request.threshold}",
        "",
        "## 2. Input Documents",
        "",
    ]
    lines.extend([f"- {doc}" for doc in request.documents])
    lines.extend(["", "## 3. Gate2 Knowledge Base Matching Result", ""])
    if not match_result.get("matched"):
        lines.extend([match_result.get("unmatched_message", "未匹配上任何威胁场景，本次安全评估确认无安全风险。"), ""])
    else:
        for item in match_result.get("matched_scenarios", []):
            lines.append(_scenario_markdown(item))
    lines.extend([
        "", "## 4. Gate1 Security Control Verification", "",
        "| Control | Result | Evidence |",
        "|---|---|---|",
    ])
    for item in verification.get("items", []):
        lines.append(f"| {item['control']} | {item['result']} | {item['evidence']} |")
    lines.extend(["", "## 5. Non-compliance Findings", ""])
    findings = [item for item in verification.get("items", []) if item["result"] != "Implemented"]
    if findings:
        for item in findings:
            lines.append(f"- {item['control']}: {item['result']}，建议补充到 Gate2 需求文档。")
    else:
        lines.append("- 未发现 Gate1 控制措施未落实项。")
    lines.extend(["", "## 6. Optimized Gate2 Requirement Updates", ""])
    for item in findings:
        lines.append(f"- 建议在架构/API/实现计划中增加：{item['control']}")
    if not findings:
        lines.append("- 暂无额外文档优化建议。")
    lines.extend(["", "## 7. Final Security Control Requirements", ""])
    controls = []
    for item in match_result.get("matched_scenarios", []):
        controls.extend(item["scenario"].get("security_control_requirements", []))
    if controls:
        lines.extend([f"- {control}" for control in dict.fromkeys(controls)])
    else:
        lines.append("- 无新增安全控制要求。")
    lines.extend(["", "## 8. Conclusion", "", "Gate2 review completed.", ""])
    return "\n".join(lines)
