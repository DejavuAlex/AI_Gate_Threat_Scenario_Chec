from backend.app.services.knowledge_base import KnowledgeBaseService
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
