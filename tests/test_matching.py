from backend.app.services.knowledge_base import KnowledgeBaseService
from backend.app.services.llm_matching import LLMMatchingService
from backend.app.services.matching import MatchingEngine


def test_gate1_matches_file_upload_business_context():
    kb = KnowledgeBaseService().load("gate1")
    text = "系统支持用户上传附件和业务需求文档，并提供文件上传能力。"
    result = MatchingEngine(kb, 0.78).match(text, "gate1")
    ids = [item["scenario"]["id"] for item in result["matched_scenarios"]]
    assert "G1-BIZ-001" in ids


def test_gate1_negative_indicator_prevents_forced_match():
    kb = KnowledgeBaseService().load("gate1")
    text = "系统明确不支持文件上传，所有文件仅本地处理不上传。"
    result = MatchingEngine(kb, 0.78).match(text, "gate1")
    ids = [item["scenario"]["id"] for item in result["matched_scenarios"]]
    assert "G1-BIZ-001" not in ids


def test_non_goals_payment_is_negative_evidence_not_a_match():
    kb = KnowledgeBaseService().load("gate1")
    engine = MatchingEngine(kb, 0.78)
    text = "# Product\n\n## 非目标\n\n- 不支持在线支付流程。"

    result = engine.match(text, "gate1")
    ids = [item["scenario"]["id"] for item in result["matched_scenarios"]]
    payment = next(item for item in kb["scenarios"] if item["id"] == "G1-BIZ-004")
    score = engine.score_scenario(text, payment, "gate1")

    assert "G1-BIZ-004" not in ids
    assert score.matched_evidence == []
    assert score.negative_evidence == ["不支持在线支付流程。"]
    assert score.score_breakdown["negative_evidence_adjustment"] == 1.0


def test_generic_api_terms_do_not_imply_unrelated_gate1_scenarios():
    kb = KnowledgeBaseService().load("gate1")
    text = """# API Design

`POST /api/reviews`

- Authentication: OAuth2.0 Bearer Token
- Rate Limit: token bucket per user
- Input Schema: project_id, documents, threshold
- Protocol: REST with OpenAPI
"""

    result = MatchingEngine(kb, 0.78).match(text, "gate1")
    ids = {item["scenario"]["id"] for item in result["matched_scenarios"]}

    assert "G1-BIZ-017" not in ids
    assert "G1-BIZ-018" not in ids
    assert "G1-BIZ-020" not in ids


def test_weak_indicator_score_is_not_raised_to_threshold():
    kb = {
        "matching_policy": {
            "score_formula": {
                "semantic_similarity": 0.35,
                "keyword_match": 0.25,
                "business_context": 0.2,
                "negative_evidence_adjustment": 0.1,
                "llm_confidence": 0.1,
            }
        },
        "scenarios": [
            {
                "id": "S-001",
                "name": "Marker scenario",
                "problem_scenario": "Does the marker exist?",
                "category": "Test",
                "business_indicators": ["rare_marker"],
                "negative_indicators": [],
                "risk_identification": [],
                "security_control_requirements": [],
            }
        ],
    }
    engine = MatchingEngine(kb, 0.78)

    score = engine.score_scenario("rare_marker", kb["scenarios"][0], "gate1")
    result = engine.match("rare_marker", "gate1")

    assert score.final_score < 0.78
    assert score.final_score != engine.threshold
    assert result["matched_scenarios"] == []


def _upload_test_kb() -> dict:
    return {
        "matching_policy": {
            "score_formula": {
                "semantic_similarity": 0.35,
                "keyword_match": 0.25,
                "business_context": 0.2,
                "negative_evidence_adjustment": 0.1,
                "llm_confidence": 0.1,
            }
        },
        "scenarios": [
            {
                "id": "S-UPLOAD",
                "name": "File upload",
                "problem_scenario": "Does the system upload files?",
                "category": "File Upload",
                "business_indicators": ["upload files"],
                "negative_indicators": ["does not support file upload"],
                "risk_identification": [],
                "security_control_requirements": ["Validate file types"],
            }
        ],
    }


def test_llm_fabricated_quote_is_rejected():
    kb = _upload_test_kb()
    document = "Users can upload files."
    engine = MatchingEngine(kb, 0.78)
    base = engine.match(document, "gate1")
    llm_result = {
        "matched": True,
        "matched_scenarios": [
            {
                "scenario_id": "S-UPLOAD",
                "llm_confidence": 0.99,
                "matched_reason": "Upload is supported.",
                "matched_evidence": ["Administrators upload executable files."],
                "optimized_security_controls": [],
            }
        ],
    }

    merged = LLMMatchingService._merge_llm_result(kb, base, llm_result, 0.78, "gate1", document)

    assert merged["matched_scenarios"] == []
    assert merged["llm_rejected_match_count"] == 1


def test_llm_verified_quote_contributes_only_its_weighted_score():
    kb = _upload_test_kb()
    document = "Users can upload files."
    engine = MatchingEngine(kb, 0.78)
    base = engine.match(document, "gate1")
    llm_result = {
        "matched": True,
        "matched_scenarios": [
            {
                "scenario_id": "S-UPLOAD",
                "llm_confidence": 0.95,
                "matched_reason": "The quote directly states the capability.",
                "matched_evidence": ["Users can upload files."],
                "optimized_security_controls": ["Validate file types"],
            }
        ],
    }

    merged = LLMMatchingService._merge_llm_result(kb, base, llm_result, 0.78, "gate1", document)
    item = merged["matched_scenarios"][0]

    assert item["score_breakdown"]["llm_confidence"] == 0.95
    assert item["final_score"] == engine.recalculate_score(item["score_breakdown"], "gate1")
    assert item["final_score"] != 0.95
    assert item["matched_evidence"] == ["Users can upload files."]


def test_llm_source_prefixed_quote_is_canonicalized_and_verified():
    kb = _upload_test_kb()
    document = "Users can upload files."
    engine = MatchingEngine(kb, 0.78)
    llm_result = {
        "matched": True,
        "matched_scenarios": [
            {
                "scenario_id": "S-UPLOAD",
                "llm_confidence": 0.95,
                "matched_evidence": ["specs/product.md: “Users can upload files.”"],
            }
        ],
    }

    merged = LLMMatchingService._merge_llm_result(
        kb,
        engine.match(document, "gate1"),
        llm_result,
        0.78,
        "gate1",
        document,
    )

    assert merged["matched_scenarios"][0]["matched_evidence"] == ["Users can upload files."]


def test_llm_quote_from_negated_requirement_is_rejected():
    kb = _upload_test_kb()
    document = "The product does not support upload files."
    engine = MatchingEngine(kb, 0.78)
    base = engine.match(document, "gate1")
    llm_result = {
        "matched": True,
        "matched_scenarios": [
            {
                "scenario_id": "S-UPLOAD",
                "llm_confidence": 0.99,
                "matched_evidence": [document],
            }
        ],
    }

    merged = LLMMatchingService._merge_llm_result(kb, base, llm_result, 0.78, "gate1", document)

    assert merged["matched_scenarios"] == []
    assert merged["llm_rejected_match_count"] == 1
