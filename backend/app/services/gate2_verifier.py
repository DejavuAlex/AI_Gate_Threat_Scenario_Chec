import re
from typing import Any


_FINAL_CONTROLS_HEADING_RE = re.compile(
    r"^#{2,3}\s+(?:\d+(?:\.\d+)?\.\s*)?(?:Final\s+Security\s+Control\s+Requirements|最终安全控制要求)\s*$",
    re.IGNORECASE,
)
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+")
_CONTROL_CONCEPTS: dict[str, tuple[str, ...]] = {
    "oauth": ("oauth2.0", "oauth 2.0", "oauth2", "oauth"),
    "access_control": ("rbac", "abac", "细粒度授权", "角色授权", "属性授权"),
    "schema_validation": ("schema校验", "schema 校验", "输入校验", "参数校验", "json schema"),
    "rate_limit": ("频率限制", "速率限制", "限流", "rate limit", "rate-limit", "throttling"),
    "audit": ("审计日志", "操作审计", "audit log", "audit trail"),
    "ip_allowlist": ("ip白名单", "ip 白名单", "来源ip", "source ip", "network allowlist"),
    "mfa": ("mfa", "多因素认证", "双因素认证", "2fa"),
    "login_lockout": ("登录失败锁定", "账户锁定", "account lockout"),
    "encryption": ("加密存储", "encrypted storage", "at rest encryption"),
    "secret_manager": ("kms", "vault", "密钥管理"),
    "gitignore": (".gitignore", "排除敏感配置"),
    "environment_secret": ("环境变量", "environment variable", "runtime secret"),
    "file_upload": ("文件上传", "上传接口", "upload"),
    "file_type": ("文件类型", "文件后缀", "扩展名", "file type", "extension"),
    "allowlist": ("白名单", "allowlist", "allow list"),
    "executable_file": ("可执行类型", "可执行文件", "executable"),
    "magic_number": ("magic number", "magic-number", "文件头", "文件签名", "mime类型", "mime type"),
    "script_execution": ("脚本执行", "执行权限", "script execution"),
    "security_sdk": ("security sdk", "安全sdk", "上传控件"),
    "file_size": ("文件大小", "上传大小", "file size"),
    "malware_scan": ("恶意内容扫描", "恶意文件扫描", "病毒扫描", "malware scan", "antivirus"),
    "sandbox": ("沙箱", "sandbox"),
    "output_encoding": ("输出编码", "html过滤", "html sanit", "xss"),
    "csrf": ("csrf", "跨站请求伪造"),
    "content_review": ("敏感词", "人工审核", "content moderation"),
    "email_delivery": ("smtp", "发送邮件", "发信", "邮件正文", "email"),
    "email_auth": ("spf", "dkim", "dmarc"),
}
_GENERIC_CONCEPTS = {"rate_limit", "audit", "allowlist", "encryption"}


def _normalize(text: str) -> str:
    return re.sub(r"[\s`*_#，,。；;：:（）()\[\]{}<>]+", "", str(text or "")).casefold()


def _extract_final_controls(report_text: str) -> list[str]:
    controls: list[str] = []
    in_final_controls = False
    for raw_line in str(report_text or "").splitlines():
        line = raw_line.strip()
        if _FINAL_CONTROLS_HEADING_RE.match(line):
            in_final_controls = True
            continue
        if in_final_controls and _MARKDOWN_HEADING_RE.match(line):
            break
        if in_final_controls and line.startswith("- "):
            control = line[2:].strip()
            if control:
                controls.append(control)
    return list(dict.fromkeys(controls))


def _document_segments(document_text: str) -> list[str]:
    segments: list[str] = []
    for raw_line in str(document_text or "").splitlines():
        line = raw_line.strip(" \t-*•")
        if not line or _MARKDOWN_HEADING_RE.match(line) or line.startswith("---"):
            continue
        segments.extend(
            sentence.strip()
            for sentence in re.split(r"(?<=[。！？!?；;])\s*", line)
            if sentence.strip()
        )
    return segments


def _concepts(text: str) -> set[str]:
    normalized = _normalize(text)
    return {
        concept
        for concept, aliases in _CONTROL_CONCEPTS.items()
        if any(_normalize(alias) in normalized for alias in aliases)
    }


def _trace_control(control: str, segments: list[str]) -> dict[str, Any]:
    normalized_control = _normalize(control)
    expected_concepts = _concepts(control)
    best_segment = ""
    best_coverage = 0.0
    best_concepts: set[str] = set()

    for segment in segments:
        normalized_segment = _normalize(segment)
        if normalized_control and normalized_control in normalized_segment:
            return {
                "control": control,
                "result": "Documented",
                "evidence": segment,
                "matched_concepts": sorted(expected_concepts),
                "evidence_basis": "Exact control wording",
                "concept_coverage": 1.0,
                "required_action": "None.",
            }
        matched_concepts = expected_concepts & _concepts(segment)
        domain_concepts = expected_concepts - _GENERIC_CONCEPTS
        if domain_concepts and matched_concepts and not (matched_concepts & domain_concepts):
            # A generic safeguard in another domain is not partial evidence.
            # For example, API rate limiting does not support an SMTP rate-limit control.
            matched_concepts = set()
        coverage = len(matched_concepts) / len(expected_concepts) if expected_concepts else 0.0
        if coverage > best_coverage:
            best_segment = segment
            best_coverage = coverage
            best_concepts = matched_concepts

    if expected_concepts and best_coverage >= 0.75:
        result = "Documented"
        action = "None."
    elif best_concepts:
        result = "Partial"
        action = "Clarify the missing details and add an acceptance criterion in the Gate2 documents."
    else:
        result = "No Evidence"
        action = "Add an explicit design or implementation requirement and an acceptance criterion."

    return {
        "control": control,
        "result": result,
        "evidence": best_segment or "No explicit evidence found in the supplied Gate2 documents.",
        "matched_concepts": sorted(best_concepts),
        "evidence_basis": (
            f"{len(best_concepts)}/{len(expected_concepts)} configured control concepts"
            if expected_concepts
            else "No configured concept evidence"
        ),
        "concept_coverage": round(best_coverage, 4),
        "required_action": action,
    }


def verify_gate1_controls(document_text: str, match_result: dict[str, Any], gate1_report_text: str = "") -> dict[str, Any]:
    """Trace Gate1 final controls to explicit evidence in the Gate2 documents.

    Gate2 scenario controls remain in the Gate2 matching section and are not
    copied into this baseline, preventing the report from repeating the same
    generated requirement list in every section. ``match_result`` is retained
    in the signature for API compatibility.
    """
    del match_result
    controls = _extract_final_controls(gate1_report_text)
    segments = _document_segments(document_text)
    items = [_trace_control(control, segments) for control in controls]
    documented = sum(1 for item in items if item["result"] == "Documented")
    partial = sum(1 for item in items if item["result"] == "Partial")
    no_evidence = sum(1 for item in items if item["result"] == "No Evidence")
    return {
        "baseline_available": bool(controls),
        "controls_source": "Gate1 Final Security Control Requirements" if controls else "No Gate1 final-control baseline available",
        "documented": documented,
        "partial": partial,
        "no_evidence": no_evidence,
        # Deprecated compatibility summary: clients needing evidence quality
        # should use documented/partial/no_evidence instead.
        "implemented": documented,
        "not_implemented": partial + no_evidence,
        "items": items,
    }
