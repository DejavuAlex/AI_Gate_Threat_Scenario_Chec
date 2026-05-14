import json
import re
from typing import Any

from .. import config

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class LLMClient:
    """OpenAI-compatible LLM client.

    The project is configured for Azure/OpenAI-compatible gateways through
    OPENAI_BASE_URL and OPENAI_API_KEY environment variables. This class never
    reads secrets from source-controlled files other than a local .env loaded by
    config.py.
    """

    def __init__(self):
        self.enabled = config.AI_LLM_ENABLED
        self.provider = config.AI_PROVIDER
        self.model = config.OPENAI_MODEL
        self.base_url = config.OPENAI_BASE_URL
        self.api_key = config.OPENAI_API_KEY
        self.temperature = config.LLM_MATCHING_TEMPERATURE
        self.timeout = config.LLM_MATCHING_TIMEOUT_SECONDS

    def is_available(self) -> bool:
        return bool(self.enabled and self.provider == "openai" and self.api_key and self.base_url and self.model)

    def _client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The installed openai package does not provide OpenAI. Install dependencies with: pip install -r requirements-dev.txt") from exc
        return OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        content = content.strip()
        match = _JSON_FENCE_RE.search(content)
        if match:
            content = match.group(1).strip()
        return json.loads(content)

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("LLM is not enabled or not fully configured")

        user_content = json.dumps(user_payload, ensure_ascii=False, indent=2)
        client = self._client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
        except Exception:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )

        content = response.choices[0].message.content or "{}"
        return self._parse_json(content)
