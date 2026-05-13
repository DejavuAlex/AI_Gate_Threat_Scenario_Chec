from pathlib import Path
from typing import Iterable

from ..config import REPO_ROOT


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
