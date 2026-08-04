import base64
import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from .. import config

# Jira rejects oversized description payloads, and a security report can be long.
MAX_DESCRIPTION_CHARS = 30000


class JiraNotConfigured(RuntimeError):
    pass


class JiraError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(config.JIRA_BASE_URL and config.JIRA_PROJECT_KEY and config.JIRA_EMAIL and config.JIRA_API_TOKEN)


def settings() -> dict[str, Any]:
    """Non-secret view of the Jira configuration, safe to return to the UI."""
    return {
        "configured": is_configured(),
        "base_url": config.JIRA_BASE_URL,
        "project_key": config.JIRA_PROJECT_KEY,
        "issue_type": config.JIRA_ISSUE_TYPE,
        "missing": [
            name
            for name, value in (
                ("JIRA_BASE_URL", config.JIRA_BASE_URL),
                ("JIRA_PROJECT_KEY", config.JIRA_PROJECT_KEY),
                ("JIRA_EMAIL", config.JIRA_EMAIL),
                ("JIRA_API_TOKEN", config.JIRA_API_TOKEN),
            )
            if not value
        ],
    }


def _require_config() -> str:
    if not is_configured():
        missing = ", ".join(settings()["missing"])
        raise JiraNotConfigured(f"Jira is not configured; missing environment variables: {missing}")
    parsed = urlparse(config.JIRA_BASE_URL)
    if parsed.scheme != "https" or not parsed.netloc:
        raise JiraNotConfigured("JIRA_BASE_URL must be an absolute https:// URL so the API token is never sent in clear text")
    return f"{config.JIRA_BASE_URL}/rest/api/3/issue"


def _adf_document(text: str) -> dict[str, Any]:
    """Wrap plain text into an Atlassian Document Format paragraph block."""
    body = text[:MAX_DESCRIPTION_CHARS]
    if len(text) > MAX_DESCRIPTION_CHARS:
        body += "\n\n... truncated, see the full report in AI Security Gate."
    paragraphs = [
        {"type": "paragraph", "content": [{"type": "text", "text": line}]} if line else {"type": "paragraph"}
        for line in body.split("\n")
    ]
    return {"type": "doc", "version": 1, "content": paragraphs}


def create_issue(summary: str, description: str, labels: list[str] | None = None) -> dict[str, Any]:
    url = _require_config()
    payload = {
        "fields": {
            "project": {"key": config.JIRA_PROJECT_KEY},
            "issuetype": {"name": config.JIRA_ISSUE_TYPE},
            "summary": summary[:250],
            "description": _adf_document(description),
            "labels": labels or [],
        }
    }
    token = base64.b64encode(f"{config.JIRA_EMAIL}:{config.JIRA_API_TOKEN}".encode()).decode()
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=config.JIRA_TIMEOUT_SECONDS) as response:
            created = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise JiraError(f"Jira rejected the request (HTTP {exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise JiraError(f"Cannot reach Jira: {exc.reason}") from exc
    key = created.get("key", "")
    return {
        "issue_key": key,
        "issue_id": created.get("id", ""),
        "issue_url": f"{config.JIRA_BASE_URL}/browse/{key}" if key else "",
    }
