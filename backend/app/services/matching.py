import re
from dataclasses import dataclass
from typing import Any

from ..config import UNMATCHED_MESSAGE

WORD_RE = re.compile(r"[A-Za-z0-9_\-\.]+|[\u4e00-\u9fff]{2,}")


def tokenize(text: str) -> set[str]:
    return {w.lower() for w in WORD_RE.findall(text or "") if w.strip()}


def contains_any(text: str, indicators: list[str]) -> int:
    lower = text.lower()
    return sum(1 for item in indicators if item and item.lower() in lower)


@dataclass
class MatchResult:
    scenario: dict[str, Any]
    final_score: float
    score_breakdown: dict[str, float]
    matched_evidence: list[str]


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
            " ".join(scenario.get("business_indicators", [])),
            " ".join(scenario.get("technical_indicators", [])),
        ])
        a, b = tokenize(document_text), tokenize(scenario_text)
        if not a or not b:
            return 0.0
        return min(1.0, len(a & b) / max(1, min(len(b), 12)))

    def _keyword_match(self, document_text: str, scenario: dict[str, Any], gate: str) -> float:
        indicators = scenario.get("business_indicators", []) if gate == "gate1" else scenario.get("technical_indicators", [])
        if not indicators:
            indicators = scenario.get("business_indicators", []) + scenario.get("technical_indicators", [])
        if not indicators:
            return 0.0
        return min(1.0, contains_any(document_text, indicators) / max(1, min(3, len(indicators))))

    def _context_score(self, document_text: str, scenario: dict[str, Any]) -> float:
        evidence_count = contains_any(document_text, scenario.get("risk_identification", []) + scenario.get("security_control_requirements", []))
        indicator_count = contains_any(document_text, scenario.get("business_indicators", []) + scenario.get("technical_indicators", []))
        return min(1.0, (indicator_count * 0.3) + (evidence_count * 0.2))

    def _negative_adjustment(self, document_text: str, scenario: dict[str, Any]) -> float:
        negatives = scenario.get("negative_indicators", [])
        return 0.0 if contains_any(document_text, negatives) else 1.0

    def _evidence(self, document_text: str, scenario: dict[str, Any]) -> list[str]:
        evidence = []
        for indicator in scenario.get("business_indicators", []) + scenario.get("technical_indicators", []):
            if indicator.lower() in document_text.lower():
                evidence.append(f"命中指标：{indicator}")
        return evidence[:10]

    def evaluate_scenarios(self, document_text: str, gate: str, include_below_threshold: bool = False) -> list[dict[str, Any]]:
        evaluated: list[dict[str, Any]] = []
        for scenario in self.kb.get("scenarios", []):
            semantic = self._semantic_similarity(document_text, scenario)
            keyword = self._keyword_match(document_text, scenario, gate)
            context = self._context_score(document_text, scenario)
            negative = self._negative_adjustment(document_text, scenario)
            llm_confidence = min(1.0, max(semantic, keyword) * 0.8 + context * 0.2)

            if gate == "gate1":
                final = (
                    semantic * self.weights.get("semantic_similarity", 0.35)
                    + keyword * self.weights.get("keyword_match", 0.25)
                    + context * self.weights.get("business_context", 0.2)
                    + negative * self.weights.get("negative_evidence_adjustment", 0.1)
                    + llm_confidence * self.weights.get("llm_confidence", 0.1)
                )
            else:
                final = (
                    semantic * self.weights.get("semantic_similarity", 0.3)
                    + keyword * self.weights.get("technical_keyword_match", 0.25)
                    + context * self.weights.get("architecture_context", 0.2)
                    + negative * 0.05
                    + llm_confidence * self.weights.get("llm_confidence", 0.1)
                )

            if negative == 0.0:
                final = min(final, self.threshold - 0.01)

            score_breakdown = {
                "semantic_similarity": round(semantic, 4),
                "keyword_match": round(keyword, 4),
                "context": round(context, 4),
                "negative_evidence_adjustment": round(negative, 4),
                "llm_confidence": round(llm_confidence, 4),
            }
            final_score = round(final, 4)
            matched = final_score >= self.threshold
            if matched or include_below_threshold:
                evaluated.append({
                    "scenario": scenario,
                    "scenario_id": scenario.get("id"),
                    "scenario_name": scenario.get("name"),
                    "risk_level": scenario.get("risk", {}).get("level"),
                    "risk": scenario.get("risk", {}),
                    "matched": matched,
                    "final_score": final_score,
                    "score_breakdown": score_breakdown,
                    "matched_evidence": self._evidence(document_text, scenario),
                })
        evaluated.sort(key=lambda item: item["final_score"], reverse=True)
        return evaluated

    def assess_stories(self, stories: list[dict[str, str]], gate: str, top_n: int = 8) -> list[dict[str, Any]]:
        assessments = []
        for story in stories:
            evaluated = self.evaluate_scenarios(story.get("content", ""), gate, include_below_threshold=True)
            matched = [item for item in evaluated if item["matched"]]
            assessments.append({
                "story_id": story.get("story_id"),
                "title": story.get("title"),
                "document_path": story.get("document_path"),
                "matched": bool(matched),
                "top_scenarios": evaluated[:top_n],
                "matched_scenarios": matched,
            })
        return assessments

    def match(self, document_text: str, gate: str) -> dict[str, Any]:
        evaluated = self.evaluate_scenarios(document_text, gate, include_below_threshold=False)
        return {
            "matched": bool(evaluated),
            "matched_scenarios": [
                {
                    "scenario": item["scenario"],
                    "final_score": item["final_score"],
                    "score_breakdown": item["score_breakdown"],
                    "matched_evidence": item["matched_evidence"],
                }
                for item in evaluated
            ],
            "unmatched_message": None if evaluated else self.policy.get("unmatched_message", UNMATCHED_MESSAGE),
        }
