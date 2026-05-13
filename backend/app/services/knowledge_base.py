import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import KNOWLEDGE_BASE_DIR


class KnowledgeBaseService:
    def _path(self, gate: str) -> Path:
        normalized = gate.lower()
        if normalized not in {"gate1", "gate2"}:
            raise ValueError("gate must be gate1 or gate2")
        return KNOWLEDGE_BASE_DIR / normalized / f"default-{normalized}-knowledge-base.json"

    def load(self, gate: str) -> dict[str, Any]:
        path = self._path(gate)
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_manual_update(self, gate: str, content: dict[str, Any], updated_by: str, change_reason: str, version: str) -> dict[str, Any]:
        """Only API/UI calls should use this method; the review engine never calls it."""
        next_content = deepcopy(content)
        next_content["llm_editable"] = False
        next_content["knowledge_base_version"] = version
        next_content.setdefault("audit", {})
        next_content["audit"]["last_updated_by"] = updated_by
        next_content["audit"]["last_change_reason"] = change_reason
        next_content["audit"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()

        path = self._path(gate)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(next_content, ensure_ascii=False, indent=2), encoding="utf-8")
        return next_content
