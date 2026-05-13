import json
from pathlib import Path


def test_gate1_knowledge_base_is_valid_json():
    path = Path("knowledge_base/gate1/default-gate1-knowledge-base.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["gate"] == "Gate1"
    assert data["llm_editable"] is False
    assert len(data["scenarios"]) == 22


def test_gate2_knowledge_base_is_valid_json():
    path = Path("knowledge_base/gate2/default-gate2-knowledge-base.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["gate"] == "Gate2"
    assert data["llm_editable"] is False
    assert len(data["scenarios"]) == 22
    assert all("mapped_gate1_scenario_id" in item for item in data["scenarios"])
