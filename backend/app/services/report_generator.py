from datetime import datetime, timezone
from typing import Any


def _risk_table_rows(risk: dict[str, Any]) -> list[str]:
    return [
        f"| Risk Level | {risk.get('level', '')} |",
        f"| P1 | {risk.get('P1', '')} |",
        f"| P2 | {risk.get('P2', '')} |",
        f"| P | {risk.get('P', '')} |",
        f"| Severity | {risk.get('severity', '')} |",
    ]


def _threat_modeling_sections(item: dict[str, Any]) -> list[str]:
    scenario = item["scenario"]
    risk = scenario.get("risk", {})
    controls = item.get("optimized_security_controls") or scenario.get("security_control_requirements", [])
    residual = scenario.get("residual_risk") or scenario.get("residualRisk") or {}
    residual_level = residual.get("level") or residual.get("risk_level") or "Control-dependent / Pending validation"
    residual_basis = residual.get("basis") or (
        "Expected to be reduced after all listed controls are fully implemented; "
        "final residual risk requires implementation evidence and reviewer confirmation."
    )
    if_controls_missing = risk.get("level", "Initial risk")

    lines = [
        "#### Threat Scenario",
        "",
        f"- Scenario ID: {scenario.get('id', '')}",
        f"- Scenario Name: {scenario.get('name', '')}",
        f"- Problem Scenario: {scenario.get('problem_scenario', '')}",
        f"- Category: {scenario.get('category', '')}",
        "- Threat / Risk Description:",
    ]
    risks = scenario.get("risk_identification", [])
    if risks:
        lines.extend([f"  - {risk_text}" for risk_text in risks])
    else:
        lines.append("  - No explicit risk description is configured for this scenario.")

    lines.extend([
        "",
        "#### Initial Risk Estimation",
        "",
        "| Metric | Value |",
        "|---|---|",
    ])
    lines.extend(_risk_table_rows(risk))

    lines.extend([
        "",
        "#### Risk Control",
        "",
    ])
    if controls:
        lines.extend([f"- {control}" for control in controls])
    else:
        lines.append("- No risk control is configured for this scenario.")

    lines.extend([
        "",
        "#### Residual Risk Estimation",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Residual Risk Level | {residual_level} |",
        f"| Estimation Basis | {residual_basis} |",
        f"| If Controls Are Missing | Same as initial risk ({if_controls_missing}) |",
        "",
    ])
    return lines


def _scenario_markdown(item: dict[str, Any]) -> str:
    scenario = item["scenario"]
    risk = scenario.get("risk", {})
    lines = [
        f"### Scenario: {scenario.get('id')} {scenario.get('name')}",
        "",
    ]
    lines.extend(_threat_modeling_sections(item))
    lines.extend([
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
    ])
    lines.extend([f"- {risk_text}" for risk_text in scenario.get("risk_identification", [])])
    lines.extend(["", "#### Matched Evidence", ""])
    if item.get("matched_evidence"):
        lines.extend([f"- {e}" for e in item["matched_evidence"]])
    else:
        lines.append("- 无直接关键词证据，基于语义和上下文匹配。")
    if item.get("matched_reason"):
        lines.extend(["", "#### LLM Matched Reason", "", f"- {item['matched_reason']}"])
    lines.extend(["", "#### Score Calculation", "", "| Metric | Score |", "|---|---:|"])
    for key, value in item.get("score_breakdown", {}).items():
        lines.append(f"| {key} | {value} |")
    lines.append(f"| Final Score | {item.get('final_score')} |")
    lines.extend(["", "#### Required Security Controls", ""])
    controls = item.get("optimized_security_controls") or scenario.get("security_control_requirements", [])
    lines.extend([f"- {control}" for control in controls])
    lines.append("")
    return "\n".join(lines)


def _metadata_lines(review_id: str, work_order_id: str, request: Any, gate: str, review_type: str, kb_label: str, kb: dict[str, Any], task_meta: dict[str, Any] | None = None) -> list[str]:
    task_meta = task_meta or {}
    return [
        "## 1. Review Metadata",
        "",
        f"- Task Serial No: {task_meta.get('task_serial_no', '')}",
        f"- Task Code: {task_meta.get('task_code', '')}",
        f"- Task Name: {task_meta.get('task_name', '')}",
        f"- Work Order / Activity ID: {work_order_id}",
        f"- Review ID: {review_id}",
        f"- Product Name: {request.product_name}",
        f"- Product Version: {request.product_version}",
        f"- Project ID: {request.project_id}",
        f"- Gate: {gate}",
        f"- Review Type: {review_type}",
        f"- Review Time: {datetime.now(timezone.utc).isoformat()}",
        f"- Repository: {request.repository or ''}",
        f"- Branch: {request.branch or ''}",
        f"- Triggered By: {request.triggered_by}",
        f"- {kb_label}: {kb.get('knowledge_base_version')}",
        f"- Knowledge Base ID: {(kb.get('metadata') or {}).get('knowledge_base_id', 'default')}",
        f"- Knowledge Base Name: {kb.get('name') or (kb.get('metadata') or {}).get('name', '')}",
        f"- Knowledge Base Category: {kb.get('category') or (kb.get('metadata') or {}).get('category', '')}",
        f"- Knowledge Base Risk Level: {kb.get('risk_level') or (kb.get('metadata') or {}).get('risk_level', '')}",
        f"- Match Threshold: {request.threshold}",
        "- Approval Status: Pending",
        "",
    ]


def _story_assessments_markdown(match_result: dict[str, Any]) -> list[str]:
    lines = ["", "## 3. Story-by-Story Threat Scenario Assessment", ""]
    story_assessments = match_result.get("story_assessments", [])
    if not story_assessments:
        lines.append("- No story-level assessment data available.")
        return lines
    for story in story_assessments:
        lines.extend([
            f"### {story.get('story_id')} - {story.get('title')}",
            "",
            f"- Source Document: {story.get('document_path')}",
            f"- Story Matched: {'Yes' if story.get('matched') else 'No'}",
            "",
            "| Scenario ID | Scenario Name | Matched | Final Score | Semantic | Keyword | Context | Negative Adj. | Risk |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ])
        for item in story.get("top_scenarios", []):
            sb = item.get("score_breakdown", {})
            lines.append(
                f"| {item.get('scenario_id')} | {item.get('scenario_name')} | {'Yes' if item.get('matched') else 'No'} | "
                f"{item.get('final_score')} | {sb.get('semantic_similarity')} | {sb.get('keyword_match')} | "
                f"{sb.get('context')} | {sb.get('negative_evidence_adjustment')} | {item.get('risk_level') or ''} |"
            )
        lines.append("")
    return lines


def _final_controls(match_result: dict[str, Any]) -> list[str]:
    controls = []
    for item in match_result.get("matched_scenarios", []):
        controls.extend(item.get("optimized_security_controls") or item["scenario"].get("security_control_requirements", []))
    return list(dict.fromkeys(controls))


def _request_input_documents(request: Any) -> list[str]:
    items = list(getattr(request, "documents", []) or [])
    for index, item in enumerate(getattr(request, "document_texts", []) or [], start=1):
        name = getattr(item, "name", None) if not isinstance(item, dict) else item.get("name")
        text = str(name or f"Pasted Spec {index}").strip() or f"Pasted Spec {index}"
        items.append(f"inline://{text}")
    return items or ["No input documents provided."]


def generate_gate1_report(review_id: str, work_order_id: str, request: Any, kb: dict[str, Any], match_result: dict[str, Any], task_meta: dict[str, Any] | None = None) -> str:
    lines = ["# Security Review Gate1 Report", ""]
    lines.extend(_metadata_lines(review_id, work_order_id, request, "Gate1", "Business Requirement Security Review", "Knowledge Base Version", kb, task_meta))
    lines.extend(["## 2. Input Documents", ""])
    lines.extend([f"- {doc}" for doc in _request_input_documents(request)])
    lines.extend(_story_assessments_markdown(match_result))
    lines.extend(["", "## 4. Overall Matching Result", ""])
    if not match_result.get("matched"):
        lines.extend([match_result.get("unmatched_message", "未匹配上任何威胁场景，本次安全评估确认无安全风险。"), ""])
    else:
        lines.append("### 4.1 Matched Threat Scenarios")
        lines.append("")
        for item in match_result.get("matched_scenarios", []):
            lines.append(_scenario_markdown(item))
    lines.extend(["", "## 5. Final Security Control Requirements", ""])
    controls = _final_controls(match_result)
    if controls:
        lines.extend([f"- {control}" for control in controls])
    else:
        lines.append("- 无新增安全控制要求。")
    lines.extend(["", "## 6. Human Review", "", "- Status: Pending", "- Reviewer:", "- Review Comment:", "- Approved At:", ""])
    return "\n".join(lines)


def generate_gate2_report(review_id: str, work_order_id: str, request: Any, kb: dict[str, Any], match_result: dict[str, Any], verification: dict[str, Any], task_meta: dict[str, Any] | None = None) -> str:
    lines = ["# Security Review Gate2 Report", ""]
    lines.extend(_metadata_lines(review_id, work_order_id, request, "Gate2", "Architecture and Technical Requirement Security Review", "Gate2 Knowledge Base Version", kb, task_meta))
    lines.extend([f"- Gate1 Report: {request.gate1_report or 'Auto latest report for the same task'}", ""])
    lines.extend(["## 2. Input Documents", ""])
    lines.extend([f"- {doc}" for doc in _request_input_documents(request)])
    lines.extend(_story_assessments_markdown(match_result))
    lines.extend(["", "## 4. Overall Gate2 Knowledge Base Matching Result", ""])
    if not match_result.get("matched"):
        lines.extend([match_result.get("unmatched_message", "未匹配上任何威胁场景，本次安全评估确认无安全风险。"), ""])
    else:
        for item in match_result.get("matched_scenarios", []):
            lines.append(_scenario_markdown(item))
    lines.extend(["", "## 5. Gate1 Security Control Verification", "", "| Control | Result | Evidence |", "|---|---|---|"])
    for item in verification.get("items", []):
        lines.append(f"| {item['control']} | {item['result']} | {item['evidence']} |")
    findings = [item for item in verification.get("items", []) if item["result"] != "Implemented"]
    lines.extend(["", "## 6. Non-compliance Findings", ""])
    if findings:
        for item in findings:
            lines.append(f"- {item['control']}: {item['result']}，建议补充到 Gate2 需求文档。")
    else:
        lines.append("- 未发现 Gate1 控制措施未落实项。")
    lines.extend(["", "## 7. Optimized Gate2 Requirement Updates", ""])
    for item in findings:
        lines.append(f"- 建议在架构/API/实现计划中增加：{item['control']}")
    if not findings:
        lines.append("- 暂无额外文档优化建议。")
    lines.extend(["", "## 8. Final Security Control Requirements", ""])
    controls = _final_controls(match_result)
    if controls:
        lines.extend([f"- {control}" for control in controls])
    else:
        lines.append("- 无新增安全控制要求。")
    lines.extend(["", "## 9. Conclusion", "", "Gate2 review completed.", ""])
    return "\n".join(lines)
