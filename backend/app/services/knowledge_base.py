import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..config import KB_HISTORY_DIR, KNOWLEDGE_BASE_DIR


class KnowledgeBaseService:
    def _normalize_gate(self, gate: str) -> str:
        normalized = gate.lower()
        if normalized not in {"gate1", "gate2"}:
            raise ValueError("gate must be gate1 or gate2")
        return normalized

    def _safe_kb_id(self, knowledge_base_id: str | None) -> str:
        raw = (knowledge_base_id or "default").strip().lower()
        if raw in {"", "latest"}:
            raw = "default"
        safe = re.sub(r"[^a-z0-9._-]+", "-", raw).strip(".-_")
        if not safe:
            raise ValueError("knowledge_base_id is required")
        return safe

    def _path(self, gate: str, knowledge_base_id: str | None = "default"):
        normalized = self._normalize_gate(gate)
        kb_id = self._safe_kb_id(knowledge_base_id)
        if kb_id == "default":
            return KNOWLEDGE_BASE_DIR / normalized / f"default-{normalized}-knowledge-base.json"
        return KNOWLEDGE_BASE_DIR / normalized / f"{kb_id}-{normalized}-knowledge-base.json"

    def _kb_id_from_path(self, gate: str, path) -> str:
        normalized = self._normalize_gate(gate)
        suffix = f"-{normalized}-knowledge-base.json"
        if path.name == f"default-{normalized}-knowledge-base.json":
            return "default"
        if path.name.endswith(suffix):
            return path.name[: -len(suffix)]
        return path.stem

    def _history_dir(self, gate: str):
        normalized = self._normalize_gate(gate)
        path = KB_HISTORY_DIR / normalized
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load(self, gate: str, knowledge_base_id: str | None = "default") -> dict[str, Any]:
        path = self._path(gate, knowledge_base_id)
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def list_catalog(self, gate: str) -> list[dict[str, Any]]:
        normalized = self._normalize_gate(gate)
        directory = KNOWLEDGE_BASE_DIR / normalized
        directory.mkdir(parents=True, exist_ok=True)
        items = []
        for path in directory.glob("*.json"):
            try:
                content = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            metadata = content.get("metadata", {}) or {}
            items.append({
                "knowledge_base_id": self._kb_id_from_path(normalized, path),
                "gate": content.get("gate") or normalized,
                "name": content.get("name") or metadata.get("name") or path.stem,
                "category": content.get("category") or metadata.get("category") or "General",
                "risk_level": content.get("risk_level") or metadata.get("risk_level") or "Inherited from scenarios",
                "description": content.get("description") or metadata.get("description") or "",
                "version": content.get("knowledge_base_version"),
                "scenario_count": len(content.get("scenarios", [])),
                "path": str(path.relative_to(KNOWLEDGE_BASE_DIR.parent)),
                "updated_at": (content.get("audit", {}) or {}).get("last_updated_at") or metadata.get("uploaded_at"),
            })
        items.sort(key=lambda item: (item["knowledge_base_id"] != "default", item["category"], item["name"]))
        return items

    def _validate_content(self, gate: str, content: dict[str, Any]) -> None:
        if not isinstance(content, dict):
            raise ValueError("knowledge base content must be a JSON object")
        actual_gate = str(content.get("gate") or gate).lower()
        if actual_gate not in {gate.lower(), gate.lower().replace("gate", "gate ")} and actual_gate != gate.lower():
            raise ValueError(f"knowledge base gate must match {gate}")
        if not isinstance(content.get("scenarios"), list):
            raise ValueError("knowledge base content must include a scenarios array")

    def _write_history(self, gate: str, knowledge_base_id: str, previous: dict[str, Any] | None, next_content: dict[str, Any], updated_by: str, change_reason: str, version: str) -> dict[str, Any]:
        normalized = self._normalize_gate(gate)
        now = datetime.now(timezone.utc).isoformat()
        history_id = f"kb-change-{normalized}-{knowledge_base_id}-{version}-{uuid4().hex[:8]}"
        history = {
            "history_id": history_id,
            "gate": normalized,
            "knowledge_base_id": knowledge_base_id,
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
        path = self._history_dir(normalized) / f"{safe_time}-{history_id}.json"
        path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        return history

    def list_history(self, gate: str, knowledge_base_id: str | None = None) -> list[dict[str, Any]]:
        kb_id = self._safe_kb_id(knowledge_base_id) if knowledge_base_id else None
        items = []
        for path in self._history_dir(gate).glob("*.json"):
            try:
                history = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if kb_id and history.get("knowledge_base_id", "default") != kb_id:
                continue
            items.append({
                "history_id": history.get("history_id"),
                "gate": history.get("gate"),
                "knowledge_base_id": history.get("knowledge_base_id", "default"),
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

    def save_manual_update(self, gate: str, content: dict[str, Any], updated_by: str, change_reason: str, version: str, knowledge_base_id: str | None = "default") -> dict[str, Any]:
        """Only API/UI calls should use this method; the review engine never calls it."""
        normalized = self._normalize_gate(gate)
        kb_id = self._safe_kb_id(knowledge_base_id)
        self._validate_content(normalized, content)
        try:
            previous = self.load(normalized, kb_id)
        except Exception:
            previous = None

        next_content = deepcopy(content)
        next_content["llm_editable"] = False
        next_content["gate"] = "Gate1" if normalized == "gate1" else "Gate2"
        next_content["knowledge_base_version"] = version
        if not isinstance(next_content.get("metadata"), dict):
            next_content["metadata"] = {}
        next_content["metadata"]["knowledge_base_id"] = kb_id
        if not isinstance(next_content.get("audit"), dict):
            next_content["audit"] = {}
        next_content["audit"]["last_updated_by"] = updated_by
        next_content["audit"]["last_change_reason"] = change_reason
        next_content["audit"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()

        history = self._write_history(normalized, kb_id, previous, next_content, updated_by, change_reason, version)
        next_content["audit"]["last_history_id"] = history["history_id"]

        path = self._path(normalized, kb_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(next_content, ensure_ascii=False, indent=2), encoding="utf-8")
        return next_content

    def save_uploaded_update(
        self,
        gate: str,
        content: dict[str, Any],
        knowledge_base_id: str,
        updated_by: str,
        change_reason: str,
        version: str | None = None,
        name: str | None = None,
        category: str | None = None,
        risk_level: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_gate(gate)
        kb_id = self._safe_kb_id(knowledge_base_id)
        self._validate_content(normalized, content)
        next_content = deepcopy(content)
        next_content["gate"] = "Gate1" if normalized == "gate1" else "Gate2"
        next_content["llm_editable"] = False
        next_version = version or next_content.get("knowledge_base_version") or "1.0.0"
        next_content["knowledge_base_version"] = next_version
        if name:
            next_content["name"] = name
        if description:
            next_content["description"] = description
        if category:
            next_content["category"] = category
        if risk_level:
            next_content["risk_level"] = risk_level
        if not isinstance(next_content.get("metadata"), dict):
            next_content["metadata"] = {}
        next_content["metadata"].update({
            "knowledge_base_id": kb_id,
            "category": category or next_content.get("category") or next_content["metadata"].get("category") or "General",
            "risk_level": risk_level or next_content.get("risk_level") or next_content["metadata"].get("risk_level") or "Inherited from scenarios",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })
        if name:
            next_content["metadata"]["name"] = name
        if description:
            next_content["metadata"]["description"] = description
        return self.save_manual_update(normalized, next_content, updated_by, change_reason, next_version, kb_id)
