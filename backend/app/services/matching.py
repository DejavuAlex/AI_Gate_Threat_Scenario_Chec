import re
from dataclasses import dataclass
from typing import Any

from ..config import UNMATCHED_MESSAGE

WORD_RE = re.compile(r"[A-Za-z0-9_./:-]+|[\u4e00-\u9fff]+")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
DOCUMENT_SEPARATOR_RE = re.compile(r"^\s*(?:---.*---|={3,}.*={3,})\s*$")
NEGATIVE_SECTION_RE = re.compile(
    r"(?:非目标|不在范围|范围外|排除项|不支持的功能|non[- ]?goals?|out\s+of\s+scope|exclusions?|not\s+supported)",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(
    r"(?:不支持|不涉及|不使用|不提供|不允许|不执行|不会|无需|禁止|禁用|未启用|未使用|没有|无法|无任何|"
    r"does\s+not|doesn't|do\s+not|don't|will\s+not|won't|not\s+supported|without|never|no\s+)",
    re.IGNORECASE,
)
CHINESE_ACTIONS = ("上传", "下载", "导出", "导入", "登录", "跳转", "重定向", "支付", "退款", "执行", "发送", "读取", "加载")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold()


def tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw_token in WORD_RE.findall(text or ""):
        token = raw_token.casefold().strip()
        if not token:
            continue
        tokens.add(token)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) > 2:
            tokens.update(token[index:index + 2] for index in range(len(token) - 1))
    return tokens


def _literal_indicator_match(text: str, indicator: str) -> bool:
    """Match a curated indicator without allowing short ASCII substrings."""
    normalized_text = _normalize_text(text)
    normalized_indicator = _normalize_text(indicator)
    if not normalized_indicator:
        return False
    if re.fullmatch(r"[a-z0-9_]+", normalized_indicator):
        pattern = rf"(?<![a-z0-9_]){re.escape(normalized_indicator)}(?![a-z0-9_])"
        return re.search(pattern, normalized_text, re.IGNORECASE) is not None
    if normalized_indicator in normalized_text:
        return True

    # Chinese indicators often use object-action order (附件上传), while
    # requirements naturally use action-object order (上传业务需求附件).
    if re.fullmatch(r"[\u4e00-\u9fff]+", normalized_indicator):
        for action in CHINESE_ACTIONS:
            if action not in normalized_indicator:
                continue
            concept = normalized_indicator.replace(action, "", 1)
            if len(concept) < 2 or action not in normalized_text or concept not in normalized_text:
                continue
            action_positions = [match.start() for match in re.finditer(re.escape(action), normalized_text)]
            concept_positions = [match.start() for match in re.finditer(re.escape(concept), normalized_text)]
            if any(abs(action_pos - concept_pos) <= 24 for action_pos in action_positions for concept_pos in concept_positions):
                return True
    return False


def contains_any(text: str, indicators: list[str]) -> int:
    return sum(1 for item in indicators if item and _literal_indicator_match(text, str(item)))


def _scenario_indicators(scenario: dict[str, Any]) -> list[str]:
    return [
        str(item)
        for item in scenario.get("business_indicators", []) + scenario.get("technical_indicators", [])
        if str(item).strip()
    ]


def _split_context_segments(text: str) -> list[tuple[str, bool]]:
    """Return sentence-like segments and whether they are in a negative section."""
    segments: list[tuple[str, bool]] = []
    negative_section_level: int | None = None
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if DOCUMENT_SEPARATOR_RE.match(line):
            negative_section_level = None
            continue
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2)
            if NEGATIVE_SECTION_RE.search(title):
                negative_section_level = level
            elif negative_section_level is not None and level <= negative_section_level:
                negative_section_level = None
            continue
        for sentence in re.split(r"(?<=[。！？!?；;])\s*", line):
            sentence = sentence.strip(" \t-*•")
            if sentence:
                segments.append((sentence, negative_section_level is not None))
    if not segments and str(text or "").strip():
        segments.append((str(text).strip(), False))
    return segments


def _context_requirement_satisfied(segment: str, scenario: dict[str, Any]) -> bool:
    """Apply optional same-segment context groups declared by a knowledge base."""
    context = scenario.get("match_context") or {}
    any_of = context.get("any_of") or []
    if not any_of:
        return True
    for group in any_of:
        terms = [group] if isinstance(group, str) else list(group or [])
        if terms and all(_literal_indicator_match(segment, str(term)) for term in terms):
            return True
    return False


def _locally_negated(segment: str, scenario: dict[str, Any], matched_indicators: list[str]) -> bool:
    negative_indicators = [str(item) for item in scenario.get("negative_indicators", []) if str(item).strip()]
    if contains_any(segment, negative_indicators):
        return True

    normalized_segment = _normalize_text(segment)
    negations = list(NEGATION_RE.finditer(normalized_segment))
    if not negations:
        return False
    anchor_positions: list[int] = []
    for indicator in matched_indicators:
        normalized_indicator = _normalize_text(indicator)
        position = normalized_segment.find(normalized_indicator)
        if position >= 0:
            anchor_positions.append(position)
        for action in CHINESE_ACTIONS:
            if action in indicator and action in normalized_segment:
                anchor_positions.append(normalized_segment.find(action))
    if not anchor_positions:
        return len(normalized_segment) <= 100 and bool(NEGATION_RE.match(normalized_segment))
    return any(abs(match.start() - position) <= 28 for match in negations for position in anchor_positions)


def collect_scenario_evidence(text: str, scenario: dict[str, Any]) -> dict[str, list[str]]:
    """Collect positive and negated evidence using a shared matching policy."""
    indicators = _scenario_indicators(scenario)
    configured_negatives = [str(item) for item in scenario.get("negative_indicators", []) if str(item).strip()]
    positive_indicators: list[str] = []
    negative_indicators: list[str] = []
    positive_evidence: list[str] = []
    negative_evidence: list[str] = []

    for segment, negative_section in _split_context_segments(text):
        matched = [indicator for indicator in indicators if _literal_indicator_match(segment, indicator)]
        explicit_negative = bool(configured_negatives and contains_any(segment, configured_negatives))
        if matched:
            is_negative = negative_section or explicit_negative or _locally_negated(segment, scenario, matched)
            if is_negative:
                negative_indicators.extend(matched)
                negative_evidence.append(segment)
            elif _context_requirement_satisfied(segment, scenario):
                positive_indicators.extend(matched)
                positive_evidence.append(segment)
        elif explicit_negative:
            negative_evidence.append(segment)

    return {
        "positive_indicators": list(dict.fromkeys(positive_indicators)),
        "negative_indicators": list(dict.fromkeys(negative_indicators)),
        "positive_evidence": list(dict.fromkeys(positive_evidence))[:5],
        "negative_evidence": list(dict.fromkeys(negative_evidence))[:5],
    }


def quote_has_positive_scenario_context(document_text: str, quote: str, scenario: dict[str, Any]) -> bool:
    """Verify that an LLM quote exists verbatim and supports this scenario."""
    normalized_quote = _normalize_text(quote).strip(" \"'`“”‘’")
    if len(normalized_quote) < 3 or normalized_quote not in _normalize_text(document_text):
        return False
    for segment, negative_section in _split_context_segments(document_text):
        normalized_segment = _normalize_text(segment)
        if normalized_quote not in normalized_segment and normalized_segment not in normalized_quote:
            continue
        matched = [indicator for indicator in _scenario_indicators(scenario) if _literal_indicator_match(segment, indicator)]
        if not matched:
            continue
        if negative_section or _locally_negated(segment, scenario, matched):
            continue
        if _context_requirement_satisfied(segment, scenario):
            return True
    return False


def extract_positive_scenario_quotes(document_text: str, evidence: str, scenario: dict[str, Any]) -> list[str]:
    """Extract and verify literal quotes from an LLM evidence value.

    Models commonly prefix an otherwise exact quote with its source path. The
    prefix is discarded only after the enclosed text independently passes the
    same verbatim, indicator-context, and negation checks.
    """
    raw = str(evidence or "").strip()
    candidates = [raw]
    candidates.extend(re.findall(r"[“\"]([^“”\"]{3,})[”\"]", raw))
    candidates.extend(re.findall(r"[‘']([^‘’']{3,})[’']", raw))
    if ":" in raw:
        candidates.append(raw.split(":", 1)[1].strip())

    verified = [
        candidate.strip(" \"'`“”‘’、，,")
        for candidate in candidates
        if quote_has_positive_scenario_context(
            document_text,
            candidate.strip(" \"'`“”‘’、，,"),
            scenario,
        )
    ]
    return list(dict.fromkeys(value for value in verified if value))


@dataclass
class MatchResult:
    scenario: dict[str, Any]
    final_score: float
    score_breakdown: dict[str, float]
    matched_evidence: list[str]
    negative_evidence: list[str]


class MatchingEngine:
    def __init__(self, knowledge_base: dict[str, Any], threshold: float):
        self.kb = knowledge_base
        self.threshold = threshold
        self.policy = knowledge_base.get("matching_policy", {})
        self.weights = self.policy.get("score_formula", {})

    def _semantic_similarity(self, document_text: str, scenario: dict[str, Any]) -> float:
        scenario_text = " ".join([
            scenario.get("name", ""),
            scenario.get("problem_scenario", ""),
            scenario.get("category", ""),
            " ".join(scenario.get("risk_identification", [])),
            " ".join(_scenario_indicators(scenario)),
        ])
        document_tokens, scenario_tokens = tokenize(document_text), tokenize(scenario_text)
        if not document_tokens or not scenario_tokens:
            return 0.0
        return _clamp(len(document_tokens & scenario_tokens) / max(1, min(len(scenario_tokens), 24)))

    @staticmethod
    def _indicator_strength(matched_indicators: list[str]) -> float:
        if not matched_indicators:
            return 0.0
        longest = max(len(re.sub(r"\s+", "", item)) for item in matched_indicators)
        return _clamp(0.84 + 0.04 * min(len(matched_indicators), 3) + 0.01 * min(longest, 8))

    @staticmethod
    def _context_score(evidence: dict[str, list[str]], gate: str) -> float:
        if not evidence["positive_indicators"]:
            return 0.0
        context_text = " ".join(evidence["positive_evidence"])
        if gate == "gate1":
            terms = ["业务", "用户", "客户", "系统", "功能", "支持", "允许", "管理员", "数据", "接口", "流程"]
        else:
            terms = ["API", "接口", "架构", "服务", "endpoint", "controller", "storage", "database", "配置", "实现"]
        base = 1.0 if contains_any(context_text, terms) else 0.82
        return _clamp(base + (0.04 if len(evidence["positive_evidence"]) > 1 else 0.0))

    def _traceability_score(self, document_text: str, scenario: dict[str, Any], gate: str) -> float:
        if gate != "gate2":
            return 0.0
        mapped_id = str(scenario.get("mapped_gate1_scenario_id") or "").strip()
        if mapped_id and mapped_id.casefold() in document_text.casefold():
            return 1.0
        document_tokens = tokenize(document_text)
        best = 0.0
        for statement in scenario.get("security_control_requirements", []) + scenario.get("verification_points", []):
            statement_tokens = tokenize(str(statement))
            if statement_tokens:
                best = max(best, len(document_tokens & statement_tokens) / len(statement_tokens))
        return _clamp(best)

    def recalculate_score(self, score_breakdown: dict[str, float], gate: str) -> float:
        semantic = score_breakdown.get("semantic_similarity", 0.0)
        keyword = score_breakdown.get("keyword_match", 0.0)
        context = score_breakdown.get("context", 0.0)
        llm_confidence = score_breakdown.get("llm_confidence", 0.0)
        negative_penalty = score_breakdown.get("negative_evidence_adjustment", 0.0)
        if gate == "gate1":
            final = (
                semantic * self.weights.get("semantic_similarity", 0.35)
                + keyword * self.weights.get("keyword_match", 0.25)
                + context * self.weights.get("business_context", 0.2)
                + llm_confidence * self.weights.get("llm_confidence", 0.1)
                - negative_penalty * self.weights.get("negative_evidence_adjustment", 0.1)
            )
        else:
            final = (
                semantic * self.weights.get("semantic_similarity", 0.3)
                + keyword * self.weights.get("technical_keyword_match", 0.25)
                + context * self.weights.get("architecture_context", 0.2)
                + score_breakdown.get("gate1_control_traceability", 0.0) * self.weights.get("gate1_control_traceability", 0.15)
                + llm_confidence * self.weights.get("llm_confidence", 0.1)
            )
        return round(_clamp(final), 4)

    def score_scenario(self, document_text: str, scenario: dict[str, Any], gate: str) -> MatchResult:
        evidence = collect_scenario_evidence(document_text, scenario)
        keyword = self._indicator_strength(evidence["positive_indicators"])
        semantic = self._semantic_similarity(document_text, scenario)
        if keyword:
            semantic = max(semantic, _clamp(keyword + 0.04))
        context = self._context_score(evidence, gate)
        if evidence["negative_evidence"]:
            negative_penalty = 0.5 if evidence["positive_evidence"] else 1.0
        else:
            negative_penalty = 0.0
        score_breakdown = {
            "semantic_similarity": round(semantic, 4),
            "keyword_match": round(keyword, 4),
            "context": round(context, 4),
            "negative_evidence_adjustment": round(negative_penalty, 4),
            "llm_confidence": 0.0,
        }
        if gate == "gate2":
            score_breakdown["gate1_control_traceability"] = round(self._traceability_score(document_text, scenario, gate), 4)
        return MatchResult(
            scenario=scenario,
            final_score=self.recalculate_score(score_breakdown, gate),
            score_breakdown=score_breakdown,
            matched_evidence=evidence["positive_evidence"],
            negative_evidence=evidence["negative_evidence"],
        )

    def match(self, document_text: str, gate: str) -> dict[str, Any]:
        results = [
            self.score_scenario(document_text, scenario, gate)
            for scenario in self.kb.get("scenarios", [])
        ]
        matched = [result for result in results if result.final_score >= self.threshold]
        matched.sort(key=lambda item: item.final_score, reverse=True)
        return {
            "matched": bool(matched),
            "matched_scenarios": [
                {
                    "scenario": result.scenario,
                    "final_score": result.final_score,
                    "score_breakdown": result.score_breakdown,
                    "matched_evidence": result.matched_evidence,
                    "negative_evidence": result.negative_evidence,
                }
                for result in matched
            ],
            "unmatched_message": None if matched else self.policy.get("unmatched_message", UNMATCHED_MESSAGE),
        }

    def assess_stories(
        self,
        stories: list[dict[str, str]],
        gate: str,
        top_n: int = 5,
        overall_matches: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        assessments: list[dict[str, Any]] = []
        canonical = {
            item.get("scenario", {}).get("id"): item
            for item in (overall_matches or [])
            if item.get("scenario", {}).get("id")
        }
        for story in stories:
            content = story.get("content", "")
            if overall_matches is None:
                scored = [self.score_scenario(content, scenario, gate) for scenario in self.kb.get("scenarios", [])]
                scored.sort(key=lambda item: item.final_score, reverse=True)
                selected = scored[:top_n]
                rows = [
                    {
                        "scenario_id": item.scenario.get("id"),
                        "scenario_name": item.scenario.get("name"),
                        "matched": item.final_score >= self.threshold,
                        "final_score": item.final_score,
                        "overall_final_score": item.final_score,
                        "local_evidence_score": item.final_score,
                        "score_breakdown": item.score_breakdown,
                        "matched_evidence": item.matched_evidence,
                        "risk_level": item.scenario.get("risk", {}).get("level"),
                    }
                    for item in selected
                ]
            else:
                rows = []
                for scenario_id, overall in canonical.items():
                    scenario = overall["scenario"]
                    local = self.score_scenario(content, scenario, gate)
                    if not local.matched_evidence:
                        continue
                    rows.append({
                        "scenario_id": scenario_id,
                        "scenario_name": scenario.get("name"),
                        "matched": True,
                        "final_score": overall.get("final_score", 0.0),
                        "overall_final_score": overall.get("final_score", 0.0),
                        "local_evidence_score": local.final_score,
                        "score_breakdown": local.score_breakdown,
                        "matched_evidence": local.matched_evidence,
                        "risk_level": scenario.get("risk", {}).get("level"),
                    })
                rows.sort(key=lambda item: item["overall_final_score"], reverse=True)
                rows = rows[:top_n]
            assessments.append({
                "story_id": story.get("story_id"),
                "title": story.get("title"),
                "document_path": story.get("document_path"),
                "matched": any(item["matched"] for item in rows),
                "top_scenarios": rows,
            })
        return assessments
