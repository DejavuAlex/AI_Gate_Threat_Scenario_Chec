from pathlib import Path
from typing import Iterable
import re

from ..config import REPO_ROOT


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


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


def extract_stories(docs: list[dict[str, str]]) -> list[dict[str, str]]:
    """Split requirement/design documents into reviewable story/section units.

    This is intentionally deterministic and lightweight for the MVP. It treats
    Markdown headings as story/section boundaries. If a document has no headings,
    the full document is assessed as one story unit.
    """
    stories: list[dict[str, str]] = []
    counter = 1
    for doc in docs:
        path = doc.get("path", "")
        content = doc.get("content", "") or ""
        matches = list(HEADING_RE.finditer(content))
        if not matches:
            if content.strip():
                stories.append({
                    "story_id": f"S{counter:03d}",
                    "title": Path(path).name or f"Story {counter}",
                    "document_path": path,
                    "content": content.strip(),
                })
                counter += 1
            continue
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
            section = content[start:end].strip()
            title = match.group(2).strip()
            if section:
                stories.append({
                    "story_id": f"S{counter:03d}",
                    "title": title,
                    "document_path": path,
                    "content": section,
                })
                counter += 1
    if not stories:
        stories.append({"story_id": "S001", "title": "Empty or missing documents", "document_path": "", "content": ""})
    return stories
