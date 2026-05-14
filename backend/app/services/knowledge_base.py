import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..config import KB_HISTORY_DIR, KNOWLEDGE_BASE_DIR


class KnowledgeBaseService:
    def _path(self, gate: str):
        normalized = gate.lower()
        if normalized not in {"gate1", "gate2"}:
            raise ValueError("gate must be gate1 or gate2")
        return KNOWLEDGE_BASE_DIR / normalized / f"default-{normalized}-knowledge-base.json"

    def _history_dir(self, gate: str):
        normalized = gate.lower()
        if normalized not in {"gate1", "gate2"}:
            raise ValueError("gate must be gate1 or gate2")
        path = KB_HISTORY_DIR / normalized
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load(self, gate: str) -> dict[str, Any]:
        path = self._path(gate)
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_history(self, gate: str, previous: dict[str, Any] | None, next_content: dict[str, Any], updated_by: str, change_reason: str, version: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        history_id = f"kb-change-{gate.lower()}-{version}-{uuid4().hex[:8]}"
        history = {
            "history_id": history_id,
            "gate": gate.lower(),
            "version": version,
            "previous_version": (previous or {}).get("knowledge_base_version"),
            "updated_by": updated_by,
            "change_reason": change_reason,
            "changed_at": now,
            "previous_scenario_count": len((previous or {}).get("scenarios", [])),
            "new_scenario_count": len(next_content.get("scenarios", [])),
            "previous_snapshot": previous,
            "new_snapshot": next_content,
        }
        safe_time = now.replace(":", "").replace("+", "Z")
        path = self._history_dir(gate) / f"{safe_time}-{history_id}.json"
        path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        return history

    def list_history(self, gate: str) -> list[dict[str, Any]]:
        items = []
        for path in self._history_dir(gate).glob("*.json"):
            try:
                history = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            items.append({
                "history_id": history.get("history_id"),
                "gate": history.get("gate"),
                "version": history.get("version"),
                "previous_version": history.get("previous_version"),
                "updated_by": history.get("updated_by"),
                "change_reason": history.get("change_reason"),
                "changed_at": history.get("changed_at"),
                "previous_scenario_count": history.get("previous_scenario_count"),
                "new_scenario_count": history.get("new_scenario_count"),
            })
        items.sort(key=lambda item: item.get("changed_at") or "", reverse=True)
        return items

    def save_manual_update(self, gate: str, content: dict[str, Any], updated_by: str, change_reason: str, version: str) -> dict[str, Any]:
        """Only API/UI calls should use this method; the review engine never calls it."""
        try:
            previous = self.load(gate)
        except Exception:
            previous = None

        next_content = deepcopy(content)
        next_content["llm_editable"] = False
        next_content["knowledge_base_version"] = version
        next_content.setdefault("audit", {})
        next_content["audit"]["last_updated_by"] = updated_by
        next_content["audit"]["last_change_reason"] = change_reason
        next_content["audit"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()

        history = self._write_history(gate, previous, next_content, updated_by, change_reason, version)
        next_content["audit"]["last_history_id"] = history["history_id"]

        path = self._path(gate)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(next_content, ensure_ascii=False, indent=2), encoding="utf-8")
        return next_content
