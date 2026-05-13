from typing import Any


def verify_gate1_controls(document_text: str, match_result: dict[str, Any], gate1_report_text: str = "") -> dict[str, Any]:
    """Validate whether Gate1/Gate2 controls appear in technical documents.

    This MVP uses deterministic text evidence so the engine is auditable. A future LLM
    adapter can optimize wording, but must not modify the golden knowledge base.
    """
    controls: list[str] = []
    for item in match_result.get("matched_scenarios", []):
        controls.extend(item["scenario"].get("security_control_requirements", []))

    # Include explicit bullet controls from Gate1 report if present.
    for line in gate1_report_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and any(keyword in stripped for keyword in ["校验", "限制", "认证", "加密", "白名单", "审计", "签名"]):
            controls.append(stripped[2:])

    unique_controls = list(dict.fromkeys([c for c in controls if c]))
    lower_doc = document_text.lower()
    items = []
    for control in unique_controls:
        # Use a few significant fragments to check evidence.
        fragments = [frag for frag in control.replace("/", " ").replace("，", " ").replace("（", " ").split() if len(frag) >= 2]
        hit = any(fragment.lower() in lower_doc for fragment in fragments[:6])
        items.append({
            "control": control,
            "result": "Implemented" if hit else "Not Implemented",
            "evidence": "技术文档中发现相关描述" if hit else "技术文档中未发现明确实现证据",
        })
    return {
        "implemented": sum(1 for i in items if i["result"] == "Implemented"),
        "not_implemented": sum(1 for i in items if i["result"] != "Implemented"),
        "items": items,
    }
