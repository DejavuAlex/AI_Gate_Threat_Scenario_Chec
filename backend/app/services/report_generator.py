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


def _scenario_markdown(
    item: dict[str, Any],
    model: dict[str, Any] | None = None,
    include_required_controls: bool = True,
) -> str:
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
        lines.append("- No direct positive indicator quote was retained.")
    if item.get("negative_evidence"):
        lines.extend(["", "#### Negative / Excluded Evidence", ""])
        lines.extend([f"- {e}" for e in item["negative_evidence"]])
    if item.get("matched_reason"):
        lines.extend(["", "#### LLM Matched Reason", "", f"- {item['matched_reason']}"])
    lines.extend([
        "",
        "#### Match Score Calculation",
        "",
        "> Final Score is recomputed from the configured weighted components. "
        "negative_evidence_adjustment is subtracted; no component is raised to the threshold.",
        "",
        "| Metric | Score |",
        "|---|---:|",
    ])
    for key, value in item.get("score_breakdown", {}).items():
        lines.append(f"| {key} | {value} |")
    lines.append(f"| Final Score | {item.get('final_score')} |")
    if include_required_controls:
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
    lines = [
        "",
        "## 3. Story-by-Story Threat Scenario Assessment",
        "",
        "> Story rows are projections of verified Overall matches. A scenario appears under a story only when that story contains positive local evidence; Non-goals and locally negated text are excluded.",
        "",
    ]
    story_assessments = match_result.get("story_assessments", [])
    if not story_assessments:
        lines.append("- No story-level assessment data available.")
        return lines
    for story in story_assessments:
        lines.extend([
            f"### {story.get('story_id')} - {story.get('title')}",
            "",
            f"- Source Document: {story.get('document_path')}",
            f"- Matched in this story: {'Yes' if story.get('matched') else 'No'}",
            "",
        ])
        story_scenarios = story.get("top_scenarios", [])
        if not story_scenarios:
            lines.extend(["- No verified Overall scenario has positive evidence in this story.", ""])
            continue
        lines.extend([
            "| Scenario ID | Scenario Name | Matched in this story | Overall Final Score | Story Evidence Score | Semantic | Keyword | Context | Negative Penalty | Risk | Evidence |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ])
        for item in story_scenarios:
            sb = item.get("score_breakdown", {})
            evidence = "<br>".join(str(value).replace("|", "\\|") for value in item.get("matched_evidence", []))
            lines.append(
                f"| {item.get('scenario_id')} | {item.get('scenario_name')} | {'Yes' if item.get('matched') else 'No'} | "
                f"{item.get('overall_final_score', item.get('final_score'))} | {item.get('local_evidence_score', item.get('final_score'))} | "
                f"{sb.get('semantic_similarity')} | {sb.get('keyword_match')} | {sb.get('context')} | "
                f"{sb.get('negative_evidence_adjustment')} | {item.get('risk_level') or ''} | {evidence} |"
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


# Jira issue descriptions stay short on purpose: reviewers act on the scenarios
# and controls, and the full report is always attached to the same issue.
SUMMARY_MAX_SCENARIOS = 20
SUMMARY_MAX_CONTROLS = 25
SUMMARY_MAX_ACTION_ITEMS = 15
_RISK_ORDER = {"red": 0, "yellow": 1, "green": 2}


def _cell(value: Any) -> str:
    """Make a value safe to place inside a Markdown table cell."""
    text = str(value if value is not None else "").strip()
    return text.replace("|", "\\|").replace("\n", "<br>")


def _highest_risk(scenarios: list[dict[str, Any]]) -> str:
    levels = [str(item.get("risk_level") or "").strip() for item in scenarios]
    levels = [level for level in levels if level]
    if not levels:
        return "None"
    return sorted(levels, key=lambda level: _RISK_ORDER.get(level.lower(), 9))[0]


def _summary_scenarios(review: dict[str, Any]) -> list[dict[str, Any]]:
    """Matched scenarios with risk level and score, newest schema first."""
    detailed = (review.get("match_result") or {}).get("matched_scenarios") or []
    if detailed:
        return [
            {
                "scenario_id": (item.get("scenario") or {}).get("id", ""),
                "scenario_name": (item.get("scenario") or {}).get("name", ""),
                "category": (item.get("scenario") or {}).get("category", ""),
                "risk_level": ((item.get("scenario") or {}).get("risk") or {}).get("level", ""),
                "final_score": item.get("final_score"),
            }
            for item in detailed
        ]
    return list(review.get("matched_scenarios") or [])


def _summary_controls(review: dict[str, Any]) -> list[str]:
    match_result = review.get("match_result") or {}
    if match_result.get("matched_scenarios"):
        return _final_controls(match_result)
    return []


def _verification_action_items(verification: dict[str, Any]) -> list[dict[str, Any]]:
    """Gate1 controls that Gate2 could not confirm as fully covered."""
    return [
        item
        for item in verification.get("items") or []
        if str(item.get("result", "")).strip().lower() not in {"documented", "implemented"}
    ]


def build_jira_summary(review: dict[str, Any]) -> str:
    """Condense a stored review into the highlights worth putting in a Jira issue."""
    review_id = review.get("review_id", "")
    gate = str(review.get("gate") or "review").strip()
    request = review.get("request") or {}
    scenarios = _summary_scenarios(review)
    controls = _summary_controls(review)
    matched = bool(review.get("matched"))

    product = " / ".join(part for part in [review.get("product_name"), review.get("product_version")] if part)
    task_label = " ".join(part for part in [review.get("task_code"), review.get("task_name")] if part)
    kb_label = review.get("knowledge_base_id") or request.get("knowledge_base_id") or ""
    kb_version = review.get("knowledge_base_version") or ""
    if kb_version:
        kb_label = f"{kb_label} ({kb_version})"
    approval = (
        f"{review.get('approval_status')} by {review.get('approved_by')} at {review.get('approved_at')}"
        if review.get("approval_status") == "approved"
        else review.get("approval_status") or "pending"
    )
    result_text = (
        f"Matched {len(scenarios)} threat scenario(s)"
        if matched
        else (review.get("match_result") or {}).get("unmatched_message") or "No threat scenario matched"
    )

    lines = [f"# {gate.upper()} Security Review Summary", ""]
    lines += ["| Field | Value |", "|---|---|"]
    for label, value in [
        ("Review ID", review_id),
        ("Gate", gate),
        ("Product / Version", product),
        ("Task", task_label),
        ("Knowledge Base", kb_label),
        ("Threshold", request.get("threshold")),
        ("Result", result_text),
        ("Highest Risk", _highest_risk(scenarios)),
        ("Approval", approval),
        ("LLM Enhanced", "yes" if review.get("llm_enabled") else "no"),
        ("Reviewed At", review.get("created_at")),
    ]:
        if value not in (None, ""):
            lines.append(f"| {_cell(label)} | {_cell(value)} |")
    lines.append("")

    if scenarios:
        lines += [f"## Matched Threat Scenarios ({len(scenarios)})", ""]
        lines += ["| Scenario | Risk | Score |", "|---|---|---|"]
        for item in scenarios[:SUMMARY_MAX_SCENARIOS]:
            name = " ".join(part for part in [item.get("scenario_id"), item.get("scenario_name")] if part)
            score = item.get("final_score")
            lines.append(f"| {_cell(name)} | {_cell(item.get('risk_level'))} | {_cell(score)} |")
        if len(scenarios) > SUMMARY_MAX_SCENARIOS:
            lines.append(f"| ... {len(scenarios) - SUMMARY_MAX_SCENARIOS} more in the attached report | | |")
        lines.append("")

    if controls:
        lines += [f"## Required Security Controls ({len(controls)})", ""]
        lines += [f"{index}. {control}" for index, control in enumerate(controls[:SUMMARY_MAX_CONTROLS], start=1)]
        if len(controls) > SUMMARY_MAX_CONTROLS:
            lines.append(f"{SUMMARY_MAX_CONTROLS + 1}. ... {len(controls) - SUMMARY_MAX_CONTROLS} more in the attached report")
        lines.append("")

    verification = review.get("gate1_control_verification") or {}
    if verification.get("baseline_available"):
        lines += ["## Gate1 Control Verification", ""]
        lines += ["| Result | Count |", "|---|---|"]
        for label, key in [
            ("Documented", "documented"),
            ("Partial", "partial"),
            ("No Evidence", "no_evidence"),
            ("Implemented", "implemented"),
            ("Not Implemented", "not_implemented"),
        ]:
            if key in verification:
                lines.append(f"| {_cell(label)} | {_cell(verification.get(key))} |")
        lines.append("")
        pending = _verification_action_items(verification)
        if pending:
            lines += [f"### Controls Needing Action ({len(pending)})", ""]
            for item in pending[:SUMMARY_MAX_ACTION_ITEMS]:
                action = str(item.get("required_action") or "").strip()
                suffix = f" — {action}" if action and action.lower() != "none." else ""
                lines.append(f"- **{item.get('result', '')}**: {item.get('control', '')}{suffix}")
            if len(pending) > SUMMARY_MAX_ACTION_ITEMS:
                lines.append(f"- ... {len(pending) - SUMMARY_MAX_ACTION_ITEMS} more in the attached report")
            lines.append("")

    lines += ["---", "", f"Full report is attached to this issue as `{review_id}.md`."]
    return "\n".join(lines)


def build_task_jira_summary(task: dict[str, Any], attachment_name: str) -> str:
    """Condense a task's end-to-end review outcome for a Jira issue description."""
    approval = task.get("approval") or {}
    auto_gate2 = task.get("auto_gate2") or {}
    reports = task.get("reports") or {}

    product = " / ".join(part for part in [task.get("product_name"), task.get("product_version")] if part)
    repo = "/".join(part for part in [task.get("repository"), task.get("branch")] if part)

    lines = ["# AI Gate Final Review Summary", ""]
    lines += ["| Field | Value |", "|---|---|"]
    for label, value in [
        ("Task", " ".join(part for part in [task.get("task_code"), task.get("task_name")] if part)),
        ("Product / Version", product),
        ("Project", task.get("project_id")),
        ("Repository / Branch", repo),
        ("Flow Status", task.get("flow_status")),
        ("Final Result", task.get("final_result")),
        ("Auto Gate2 Status", auto_gate2.get("status")),
        ("Triggered By", task.get("triggered_by")),
        ("Created At", task.get("created_at")),
        ("Updated At", task.get("updated_at")),
    ]:
        if value not in (None, ""):
            lines.append(f"| {_cell(label)} | {_cell(value)} |")
    lines.append("")

    lines += ["## Approvals", "", "| Gate | Approved By | Approved At |", "|---|---|---|"]
    for gate in ["gate1", "gate2"]:
        item = approval.get(gate) or {}
        lines.append(f"| {gate} | {_cell(item.get('approved_by') or 'pending')} | {_cell(item.get('approved_at') or '-')} |")
    lines.append("")

    lines += ["## Latest Reports", "", "| Gate | Review ID |", "|---|---|"]
    has_report = False
    for gate in ["gate1", "gate2"]:
        items = reports.get(gate) or []
        if items:
            has_report = True
            lines.append(f"| {gate} | {_cell(items[-1].get('review_id'))} |")
    if not has_report:
        lines.append("| - | - |")
    lines.append("")

    error = auto_gate2.get("error")
    if error:
        lines += ["## Auto Gate2 Error", "", f"> {_cell(error)}", ""]

    lines += ["---", "", f"Full task summary is attached to this issue as `{attachment_name}`."]
    return "\n".join(lines)


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
            # Risk Control above is the single canonical Gate2 control list.
            lines.append(_scenario_markdown(item, model, include_required_controls=False))

    items = verification.get("items", [])
    documented = int(verification.get("documented", verification.get("implemented", 0)) or 0)
    partial = int(verification.get("partial", 0) or 0)
    no_evidence = int(verification.get("no_evidence", verification.get("not_implemented", 0)) or 0)
    gaps = [item for item in items if item.get("result") not in {"Documented", "Implemented"}]
    baseline_available = bool(verification.get("baseline_available", items))

    lines.extend([
        "",
        "## 5. Gate1-to-Gate2 Security Control Traceability",
        "",
        "> This section checks only the final controls inherited from Gate1. Gate2 scenario controls are listed once under Risk Control in section 4.",
        "> Documented means explicit design evidence was found; it is not a code-level implementation or vulnerability verdict.",
        "",
        f"- Baseline Source: {verification.get('controls_source', 'Gate1 Final Security Control Requirements')}",
        f"- Summary: {documented} documented / {partial} partial / {no_evidence} with no explicit evidence",
        "",
    ])
    if items:
        lines.extend([
            "| Gate1 Control | Traceability | Evidence Basis | Gate2 Evidence | Required Action |",
            "|---|---|---|---|---|",
        ])
        for item in items:
            control = str(item.get("control", "")).replace("|", "\\|")
            basis = str(item.get("evidence_basis", "Legacy literal check")).replace("|", "\\|")
            evidence = str(item.get("evidence", "")).replace("|", "\\|")
            action = str(item.get("required_action") or ("None." if item.get("result") in {"Documented", "Implemented"} else "Add explicit Gate2 design evidence and an acceptance criterion.")).replace("|", "\\|")
            lines.append(f"| {control} | {item.get('result', '')} | {basis} | {evidence} | {action} |")
    else:
        lines.append("- No Gate1 final-control baseline was available, so cross-gate traceability was not evaluated.")

    if not baseline_available:
        decision = "Gate1 Baseline Required"
        rationale = "Provide or link the approved Gate1 report before making a cross-gate decision."
    elif gaps:
        decision = "Gate2 Document Update Required"
        rationale = f"Resolve the {len(gaps)} partial or no-evidence row(s) in section 5, then rerun Gate2."
    else:
        decision = "Ready for Human Review"
        rationale = "Every inherited Gate1 control has explicit Gate2 document evidence."
    lines.extend([
        "",
        "## 6. Gate2 Review Decision",
        "",
        f"- Decision: {decision}",
        f"- Rationale: {rationale}",
        "- Scope: Document traceability only; source-code and runtime implementation still require separate verification.",
        "- Automated Review Execution: Completed",
        "",
        "## 7. Human Review",
        "",
        "- Status: Pending",
        "- Reviewer:",
        "- Review Comment:",
        "- Approved At:",
        "",
    ])
    return "\n".join(lines)
