import re
from pathlib import Path
from typing import Iterable

from ..config import REPO_ROOT

STORY_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
STORY_ID_RE = re.compile(r"\b(?:US|Story|STORY|REQ|FR|NFR)[-_: ]?\d+\b", re.IGNORECASE)


def read_documents(paths: Iterable[str]) -> tuple[str, list[dict[str, str]]]:
    docs: list[dict[str, str]] = []
    all_text: list[str] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = REPO_ROOT / raw
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8")
        else:
            content = ""
        docs.append({"path": raw, "content": content})
        all_text.append(f"\n--- {raw} ---\n{content}")
    return "\n".join(all_text), docs


def _story_id(title: str, fallback_index: int) -> str:
    match = STORY_ID_RE.search(title or "")
    if match:
        return match.group(0).replace(" ", "-")
    return f"STORY-{fallback_index:03d}"


def extract_stories(docs: list[dict[str, str]]) -> list[dict[str, str]]:
    """Extract reviewable story/requirement chunks from Markdown-like documents.

    If a document has headings, each heading section becomes one story chunk. If
    no headings are present, the whole document is treated as one reviewable
    item so story-level scoring still works for plain text specs.
    """
    stories: list[dict[str, str]] = []
    index = 1
    for doc in docs:
        content = doc.get("content") or ""
        path = doc.get("path") or ""
        if not content.strip():
            continue
        matches = list(STORY_HEADING_RE.finditer(content))
        if not matches:
            title = Path(path).name or f"Document {index}"
            stories.append({"story_id": _story_id(title, index), "title": title, "document_path": path, "content": content})
            index += 1
            continue
        for pos, match in enumerate(matches):
            start = match.start()
            end = matches[pos + 1].start() if pos + 1 < len(matches) else len(content)
            section = content[start:end].strip()
            title = match.group(2).strip()
            if not section:
                continue
            stories.append({"story_id": _story_id(title, index), "title": title, "document_path": path, "content": section})
            index += 1
    return stories
