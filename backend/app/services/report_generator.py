from datetime import datetime, timezone
from typing import Any

# Risk model defaults. Every value can be overridden per knowledge base through
# `matching_policy.risk_model`, and per scenario through `scenario.residual_risk`.
DEFAULT_RISK_MODEL = {
    # Fraction of the occurrence probability removed once every listed control is
    # fully implemented and verified. 0.5 keeps the projection deliberately
    # conservative because Gate1/Gate2 are design-stage reviews.
    "control_effectiveness": 0.5,
    # Risk score = P x Severity, so the score range is 0-100 for 0-10 inputs.
    "level_thresholds": {"green": 20.0, "yellow": 50.0},
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".") or "0"


def risk_model_for(kb: dict[str, Any] | None) -> dict[str, Any]:
    model = {"control_effectiveness": DEFAULT_RISK_MODEL["control_effectiveness"], "level_thresholds": dict(DEFAULT_RISK_MODEL["level_thresholds"])}
    override = ((kb or {}).get("matching_policy") or {}).get("risk_model") or {}
    if "control_effectiveness" in override:
        model["control_effectiveness"] = min(max(_to_float(override["control_effectiveness"], model["control_effectiveness"]), 0.0), 1.0)
    thresholds = override.get("level_thresholds") or {}
    for key in ("green", "yellow"):
        if key in thresholds:
            model["level_thresholds"][key] = _to_float(thresholds[key], model["level_thresholds"][key])
    return model


def _risk_score(risk: dict[str, Any]) -> float:
    return round(_to_float(risk.get("P")) * _to_float(risk.get("severity")), 1)


def _level_from_score(score: float, model: dict[str, Any]) -> str:
    thresholds = model["level_thresholds"]
    if score < thresholds["green"]:
        return "Green"
    if score < thresholds["yellow"]:
        return "Yellow"
    return "Red"


def _residual_risk(scenario: dict[str, Any], controls: list[str], model: dict[str, Any]) -> dict[str, Any]:
    """Project the residual risk that remains after the listed controls are implemented.

    Controls reduce the probability of occurrence, not the severity of the impact,
    so severity is carried over unchanged unless the knowledge base overrides it.
    """
    risk = scenario.get("risk", {})
    override = scenario.get("residual_risk") or scenario.get("residualRisk") or {}
    initial_p = _to_float(risk.get("P"))
    initial_severity = _to_float(risk.get("severity"))

    effectiveness = 0.0 if not controls else _to_float(override.get("control_effectiveness"), model["control_effectiveness"])
    effectiveness = min(max(effectiveness, 0.0), 1.0)

    residual_p = _to_float(override.get("P"), round(initial_p * (1 - effectiveness), 2))
    residual_severity = _to_float(override.get("severity"), initial_severity)
    score = round(residual_p * residual_severity, 1)
    level = override.get("level") or override.get("risk_level") or _level_from_score(score, model)
    return {
        "P": residual_p,
        "severity": residual_severity,
        "score": score,
        "level": level,
        "effectiveness": effectiveness,
        "control_count": len(controls),
        "basis": override.get("basis"),
    }


def _risk_table_rows(risk: dict[str, Any]) -> list[str]:
    return [
        f"| Risk Level | {risk.get('level', '')} |",
        f"| P1 (attack attempt probability) | {risk.get('P1', '')} |",
        f"| P2 (attack success probability) | {risk.get('P2', '')} |",
        f"| P (combined probability) | {risk.get('P', '')} |",
        f"| Severity (impact) | {risk.get('severity', '')} |",
        f"| Risk Score (P x Severity) | {_fmt(_risk_score(risk))} |",
    ]


def _threat_modeling_sections(item: dict[str, Any], model: dict[str, Any] | None = None) -> list[str]:
    model = model or risk_model_for(None)
    scenario = item["scenario"]
    risk = scenario.get("risk", {})
    controls = item.get("optimized_security_controls") or scenario.get("security_control_requirements", [])
    residual = _residual_risk(scenario, list(controls), model)
    initial_score = _risk_score(risk)
    if residual["control_count"]:
        default_basis = (
            f"Projected value assuming all {residual['control_count']} listed controls are fully implemented and verified. "
            f"Controls are modelled as removing {residual['effectiveness']:.0%} of the occurrence probability; "
            "severity is unchanged because the controls are preventive rather than impact-limiting."
        )
    else:
        default_basis = "No security control is configured for this scenario, so no risk reduction can be claimed."
    residual_basis = residual["basis"] or default_basis
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
        "> Projected value for the design stage. It becomes the confirmed residual risk only after",
        "> implementation evidence is provided and the reviewer signs off.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Residual Risk Level | {residual['level']} |",
        f"| Residual P (combined probability) | {_fmt(residual['P'])} |",
        f"| Residual Severity (impact) | {_fmt(residual['severity'])} |",
        f"| Residual Risk Score (P x Severity) | {_fmt(residual['score'])} |",
        f"| Initial Risk Score (for comparison) | {_fmt(initial_score)} |",
        f"| Risk Reduction | {_fmt(initial_score - residual['score'])} ({(1 - residual['score'] / initial_score) if initial_score else 0:.0%}) |",
        f"| Assumed Control Effectiveness | {residual['effectiveness']:.0%} over {residual['control_count']} control(s) |",
        f"| Estimation Basis | {residual_basis} |",
        f"| If Controls Are Missing | Same as initial risk ({if_controls_missing}, score {_fmt(initial_score)}) |",
        "",
    ])
    return lines


def _scenario_markdown(item: dict[str, Any], model: dict[str, Any] | None = None) -> str:
    scenario = item["scenario"]
    lines = [
        f"### Scenario: {scenario.get('id')} {scenario.get('name')}",
        "",
    ]
    lines.extend(_threat_modeling_sections(item, model))
    lines.extend(["#### Matched Evidence", ""])
    if item.get("matched_evidence"):
        lines.extend([f"- {e}" for e in item["matched_evidence"]])
    else:
        lines.append("- 无直接关键词证据，基于语义和上下文匹配。")
    if item.get("matched_reason"):
        lines.extend(["", "#### LLM Matched Reason", "", f"- {item['matched_reason']}"])
    lines.extend(["", "#### Match Score Calculation", "", "| Metric | Score |", "|---|---:|"])
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
    model = risk_model_for(kb)
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
            lines.append(_scenario_markdown(item, model))
    lines.extend(["", "## 5. Final Security Control Requirements", ""])
    controls = _final_controls(match_result)
    if controls:
        lines.extend([f"- {control}" for control in controls])
    else:
        lines.append("- 无新增安全控制要求。")
    lines.extend(["", "## 6. Human Review", "", "- Status: Pending", "- Reviewer:", "- Review Comment:", "- Approved At:", ""])
    return "\n".join(lines)


def generate_gate2_report(review_id: str, work_order_id: str, request: Any, kb: dict[str, Any], match_result: dict[str, Any], verification: dict[str, Any], task_meta: dict[str, Any] | None = None) -> str:
    model = risk_model_for(kb)
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
            lines.append(_scenario_markdown(item, model))
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
