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

    def _change_summary(self, previous: dict[str, Any] | None, next_content: dict[str, Any] | None) -> dict[str, Any]:
        previous = previous if isinstance(previous, dict) else {}
        next_content = next_content if isinstance(next_content, dict) else {}
        missing = object()

        def scenarios_by_id(snapshot: dict[str, Any]) -> dict[str, Any]:
            scenarios = snapshot.get("scenarios", [])
            if not isinstance(scenarios, list):
                return {}
            result = {}
            for index, scenario in enumerate(scenarios, start=1):
                scenario_id = scenario.get("id") if isinstance(scenario, dict) else None
                key = str(scenario_id).strip() if scenario_id is not None else ""
                result[key or f"#{index}"] = scenario
            return result

        def ordered_keys(previous_value: dict[str, Any], next_value: dict[str, Any]) -> list[str]:
            keys = list(previous_value)
            keys.extend(key for key in next_value if key not in previous_value)
            return keys

        field_changes: list[dict[str, Any]] = []

        def add_field_change(
            path: str,
            previous_value: Any,
            next_value: Any,
            scenario_id: str | None = None,
            field: str | None = None,
        ) -> None:
            if previous_value is missing:
                change_type = "added"
            elif next_value is missing:
                change_type = "removed"
            else:
                change_type = "modified"
            change: dict[str, Any] = {"path": path, "change_type": change_type}
            if scenario_id is not None:
                change["scenario_id"] = scenario_id
                change["field"] = field or ""
            if previous_value is not missing:
                change["previous_value"] = deepcopy(previous_value)
            if next_value is not missing:
                change["new_value"] = deepcopy(next_value)
            field_changes.append(change)

        def compare_fields(
            previous_value: Any,
            next_value: Any,
            path: str,
            scenario_id: str | None = None,
            field: str | None = None,
        ) -> None:
            if previous_value is missing or next_value is missing:
                add_field_change(path, previous_value, next_value, scenario_id, field)
                return
            if isinstance(previous_value, dict) and isinstance(next_value, dict):
                for key in ordered_keys(previous_value, next_value):
                    child_path = f"{path}.{key}" if path else key
                    if child_path in {"audit", "metadata.uploaded_at"}:
                        continue
                    child_field = f"{field}.{key}" if field else key
                    compare_fields(
                        previous_value.get(key, missing),
                        next_value.get(key, missing),
                        child_path,
                        scenario_id,
                        child_field if scenario_id is not None else None,
                    )
                return
            if previous_value != next_value:
                add_field_change(path, previous_value, next_value, scenario_id, field)

        previous_scenarios = scenarios_by_id(previous)
        next_scenarios = scenarios_by_id(next_content)
        modified_scenario_ids = [
            key
            for key in next_scenarios
            if key in previous_scenarios and previous_scenarios[key] != next_scenarios[key]
        ]
        for scenario_id in modified_scenario_ids:
            compare_fields(
                previous_scenarios[scenario_id],
                next_scenarios[scenario_id],
                f"scenarios[{scenario_id}]",
                scenario_id,
            )

        for key in ordered_keys(previous, next_content):
            if key in {"audit", "scenarios"}:
                continue
            compare_fields(previous.get(key, missing), next_content.get(key, missing), key)

        changed_fields = []
        for change in field_changes:
            if change.get("scenario_id") is not None:
                continue
            top_level_field = str(change.get("path") or "").split(".", 1)[0]
            if top_level_field and top_level_field not in changed_fields:
                changed_fields.append(top_level_field)
        return {
            "added_scenario_ids": [key for key in next_scenarios if key not in previous_scenarios],
            "modified_scenario_ids": modified_scenario_ids,
            "removed_scenario_ids": [key for key in previous_scenarios if key not in next_scenarios],
            "changed_fields": changed_fields,
            "field_change_count": len(field_changes),
            "field_changes": field_changes,
        }

    def _history_change_summary(self, history: dict[str, Any]) -> dict[str, Any]:
        change_summary = history.get("change_summary")
        if not isinstance(change_summary, dict) or not isinstance(change_summary.get("field_changes"), list):
            return self._change_summary(history.get("previous_snapshot"), history.get("new_snapshot"))
        result = deepcopy(change_summary)
        result["field_change_count"] = len(result["field_changes"])
        return result

    def _history_summary(self, history: dict[str, Any]) -> dict[str, Any]:
        change_summary = self._history_change_summary(history)
        change_summary["field_changes"] = [
            {
                key: value
                for key, value in change.items()
                if key in {"path", "change_type", "scenario_id", "field"}
            }
            for change in change_summary.get("field_changes", [])
        ]
        return {
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
            "change_summary": change_summary,
        }

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
            "change_summary": self._change_summary(previous, next_content),
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
            items.append(self._history_summary(history))
        items.sort(key=lambda item: item.get("changed_at") or "", reverse=True)
        return items

    def get_history(self, gate: str, history_id: str) -> dict[str, Any]:
        normalized = self._normalize_gate(gate)
        identifier = (history_id or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]+", identifier):
            raise ValueError("invalid history_id")
        for path in self._history_dir(normalized).glob("*.json"):
            try:
                history = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if history.get("history_id") != identifier:
                continue
            if history.get("gate") not in {None, normalized}:
                continue
            result = deepcopy(history)
            result["change_summary"] = self._history_change_summary(history)
            return result
        raise FileNotFoundError(f"knowledge base history record not found: {identifier}")

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
