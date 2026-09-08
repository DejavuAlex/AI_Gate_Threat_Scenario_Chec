import base64
import json
import mimetypes
import re
import ssl
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .. import config

# Jira rejects oversized description payloads, and a security report can be long.
MAX_DESCRIPTION_CHARS = 30000

_CODE_FENCE_RE = re.compile(r"^```(\w*)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^(\s*)[-*]\s+(.*)$")
_ORDERED_RE = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_DELIMITER_RE = re.compile(r"^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$")
_TABLE_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
_CELL_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
# Jira renders very wide tables poorly, and report tables can carry long evidence text.
MAX_TABLE_COLUMNS = 12


def _ssl_context() -> ssl.SSLContext | None:
    if config.JIRA_VERIFY_SSL:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


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


def _inline_content(text: str) -> list[dict[str, Any]]:
    """Split a line of text into ADF text nodes, honoring **bold** and `code` spans."""
    if not text:
        return [{"type": "text", "text": ""}]
    tokens: list[dict[str, Any]] = []
    pos = 0
    # Merge bold/code matches in order of appearance.
    combined = sorted(
        [(m.start(), m.end(), "strong", m.group(1)) for m in _BOLD_RE.finditer(text)]
        + [(m.start(), m.end(), "code", m.group(1)) for m in _INLINE_CODE_RE.finditer(text)]
    )
    for start, end, mark, inner in combined:
        if start < pos:
            continue  # overlapping match, skip
        if start > pos:
            tokens.append({"type": "text", "text": text[pos:start]})
        tokens.append({"type": "text", "text": inner, "marks": [{"type": mark}]})
        pos = end
    if pos < len(text):
        tokens.append({"type": "text", "text": text[pos:]})
    return tokens or [{"type": "text", "text": text}]


def _flush_list(items: list[list[dict[str, Any]]], ordered: bool) -> dict[str, Any]:
    return {
        "type": "orderedList" if ordered else "bulletList",
        "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": content}]} for content in items
        ],
    }


def _split_table_row(line: str) -> list[str]:
    """Split one Markdown table row into unescaped cell values."""
    cells = _TABLE_CELL_SPLIT_RE.split(line.strip())
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [cell.replace("\\|", "|").strip() for cell in cells]


def _table_cell(text: str, header: bool) -> dict[str, Any]:
    """Build an ADF table cell, turning <br> separators into separate paragraphs."""
    parts = [part.strip() for part in _CELL_BREAK_RE.split(text)]
    parts = [part for part in parts if part] or [""]
    return {
        "type": "tableHeader" if header else "tableCell",
        "attrs": {},
        "content": [{"type": "paragraph", "content": _inline_content(part)} for part in parts],
    }


def _table_node(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "table", "attrs": {"isNumberColumnEnabled": False, "layout": "default"}, "content": rows}


def _horizontal_table(header: list[str], records: list[list[str]]) -> list[dict[str, Any]]:
    rows = [{"type": "tableRow", "content": [_table_cell(cell, True) for cell in header]}]
    rows += [
        {"type": "tableRow", "content": [_table_cell(cell, False) for cell in record]} for record in records
    ]
    return [_table_node(rows)]


def _vertical_tables(header: list[str], records: list[list[str]]) -> list[dict[str, Any]]:
    """Transpose a wide table into one field/value table per record.

    Jira renders many-column tables as cramped, horizontally clipped columns.
    One vertical table per row keeps every field readable without scrolling.
    """
    blocks: list[dict[str, Any]] = []
    for record in records:
        # The first column is normally the identifier, so it becomes the title row.
        rows = [{"type": "tableRow", "content": [_table_cell(header[0], True), _table_cell(record[0], True)]}]
        rows += [
            {"type": "tableRow", "content": [_table_cell(name, True), _table_cell(value, False)]}
            for name, value in zip(header[1:], record[1:])
        ]
        blocks.append(_table_node(rows))
    return blocks or _horizontal_table(header, records)


def _parse_table(lines: list[str], start: int) -> tuple[list[dict[str, Any]] | None, int]:
    """Parse a GitHub-style Markdown table beginning at ``start``.

    Returns the ADF block(s) for the table and the index of the first line after
    it, or ``(None, start)`` when these lines are not a table.
    """
    if start + 1 >= len(lines):
        return None, start
    if not _TABLE_ROW_RE.match(lines[start]) or not _TABLE_DELIMITER_RE.match(lines[start + 1]):
        return None, start

    header = _split_table_row(lines[start])
    if not header:
        return None, start
    column_count = min(len(header), MAX_TABLE_COLUMNS)

    def normalize(cells: list[str]) -> list[str]:
        trimmed = cells[:column_count]
        return trimmed + [""] * (column_count - len(trimmed))

    header = normalize(header)
    records: list[list[str]] = []
    index = start + 2
    while index < len(lines) and _TABLE_ROW_RE.match(lines[index]) and not _TABLE_DELIMITER_RE.match(lines[index]):
        records.append(normalize(_split_table_row(lines[index])))
        index += 1

    transpose_min = config.JIRA_TABLE_TRANSPOSE_MIN_COLUMNS
    if transpose_min > 0 and column_count > transpose_min:
        return _vertical_tables(header, records), index
    return _horizontal_table(header, records), index


def _markdown_to_adf(text: str) -> dict[str, Any]:
    """Convert a Markdown report into Atlassian Document Format blocks.

    Supports headings, bullet/numbered lists, GitHub-style tables, blockquotes,
    fenced code blocks, and inline bold/code spans, which covers the AI Security
    Gate report format. Wide tables are transposed into vertical field/value
    tables because Jira renders many-column tables poorly. Anything else falls
    back to plain paragraphs so no content is lost.
    """
    body = text[:MAX_DESCRIPTION_CHARS]
    if len(text) > MAX_DESCRIPTION_CHARS:
        body += "\n\n... truncated, see the full report in AI Security Gate."

    blocks: list[dict[str, Any]] = []
    list_items: list[list[dict[str, Any]]] = []
    list_ordered: bool | None = None
    in_code = False
    code_lines: list[str] = []
    code_lang = ""

    def close_list() -> None:
        nonlocal list_items, list_ordered
        if list_items:
            blocks.append(_flush_list(list_items, bool(list_ordered)))
        list_items = []
        list_ordered = None

    lines = body.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        fence = _CODE_FENCE_RE.match(line)
        if fence:
            if in_code:
                blocks.append(
                    {
                        "type": "codeBlock",
                        "attrs": {"language": code_lang} if code_lang else {},
                        "content": [{"type": "text", "text": "\n".join(code_lines)}] if code_lines else [],
                    }
                )
                code_lines = []
                code_lang = ""
                in_code = False
            else:
                close_list()
                in_code = True
                code_lang = fence.group(1)
            continue
        if in_code:
            code_lines.append(line)
            continue

        if _RULE_RE.match(line):
            close_list()
            blocks.append({"type": "rule"})
            continue

        table, table_end = _parse_table(lines, index - 1)
        if table:
            close_list()
            blocks.extend(table)
            index = table_end
            continue

        quote = _BLOCKQUOTE_RE.match(line)
        if quote:
            close_list()
            blocks.append(
                {
                    "type": "blockquote",
                    "content": [{"type": "paragraph", "content": _inline_content(quote.group(1))}],
                }
            )
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            close_list()
            level = min(len(heading.group(1)), 6)
            blocks.append(
                {"type": "heading", "attrs": {"level": level}, "content": _inline_content(heading.group(2))}
            )
            continue

        bullet = _BULLET_RE.match(line)
        ordered = _ORDERED_RE.match(line)
        if bullet or ordered:
            is_ordered = ordered is not None
            match = ordered or bullet
            if list_ordered is not None and list_ordered != is_ordered:
                close_list()
            list_ordered = is_ordered
            list_items.append(_inline_content(match.group(2)))
            continue

        close_list()
        if line.strip():
            blocks.append({"type": "paragraph", "content": _inline_content(line)})
        else:
            blocks.append({"type": "paragraph"})

    close_list()
    if in_code:
        # Unclosed fence at end of report; emit what we have.
        blocks.append({"type": "codeBlock", "content": [{"type": "text", "text": "\n".join(code_lines)}]})
    if not blocks:
        blocks.append({"type": "paragraph"})
    return {"type": "doc", "version": 1, "content": blocks}


def create_issue(summary: str, description: str, labels: list[str] | None = None) -> dict[str, Any]:
    url = _require_config()
    fields: dict[str, Any] = {
        "project": {"key": config.JIRA_PROJECT_KEY},
        "issuetype": {"name": config.JIRA_ISSUE_TYPE},
        "summary": summary[:250],
        "description": _markdown_to_adf(description),
        "labels": labels or [],
    }
    # Without an explicit security level, Jira applies the issue type's
    # configured default, which can be a level the reporting account cannot
    # view, making the created issue invisible to everyone including the
    # reporter. Setting it explicitly avoids that surprise.
    if config.JIRA_SECURITY_LEVEL_ID:
        fields["security"] = {"id": config.JIRA_SECURITY_LEVEL_ID}
    payload = {"fields": fields}
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
        with urllib.request.urlopen(request, timeout=config.JIRA_REQUEST_TIMEOUT, context=_ssl_context()) as response:
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


def attach_file(issue_key: str, file_path: Path, filename: str | None = None) -> dict[str, Any]:
    """Upload a file as an attachment on an existing Jira issue.

    Raises JiraError if the file is missing, too large, or Jira rejects it.
    """
    _require_config()
    if not file_path.exists():
        raise JiraError(f"Cannot attach file, it does not exist: {file_path}")
    return attach_bytes(issue_key, file_path.read_bytes(), filename or file_path.name)


def attach_bytes(issue_key: str, data: bytes, filename: str) -> dict[str, Any]:
    """Upload in-memory content as an attachment on an existing Jira issue."""
    _require_config()
    size = len(data)
    if size > config.JIRA_ATTACHMENT_MAX_BYTES:
        raise JiraError(
            f"Attachment '{filename}' is {size} bytes, exceeding the "
            f"{config.JIRA_ATTACHMENT_MAX_BYTES} byte limit (JIRA_ATTACHMENT_MAX_BYTES)"
        )
    name = filename
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{config.JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/attachments"
    token = base64.b64encode(f"{config.JIRA_EMAIL}:{config.JIRA_API_TOKEN}".encode()).decode()
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            # Required by Jira to allow attachment uploads without a CSRF check.
            "X-Atlassian-Token": "no-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=config.JIRA_ATTACHMENT_TIMEOUT, context=_ssl_context()) as response:
            uploaded = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise JiraError(f"Jira rejected the attachment (HTTP {exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise JiraError(f"Cannot reach Jira to upload attachment: {exc.reason}") from exc
    entry = uploaded[0] if isinstance(uploaded, list) and uploaded else {}
    return {"attachment_id": entry.get("id", ""), "filename": entry.get("filename", name)}
