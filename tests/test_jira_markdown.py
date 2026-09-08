"""Unit tests for the Jira Markdown -> ADF converter."""

import pytest

from backend.app import config
from backend.app.services.jira import MAX_TABLE_COLUMNS, _markdown_to_adf


@pytest.fixture(autouse=True)
def keep_tables_horizontal(monkeypatch):
    """Most tests assert on the original layout; transposition is tested explicitly."""
    monkeypatch.setattr(config, "JIRA_TABLE_TRANSPOSE_MIN_COLUMNS", 0)


def _blocks(markdown: str) -> list[dict]:
    return _markdown_to_adf(markdown)["content"]


def _block_types(markdown: str) -> list[str]:
    """Block types, ignoring the empty paragraphs the converter emits for blank lines."""
    return [block["type"] for block in _blocks(markdown) if block.get("content") or block["type"] != "paragraph"]


def _cell_text(cell: dict) -> str:
    return "\n".join(
        "".join(item.get("text", "") for item in paragraph.get("content", []))
        for paragraph in cell["content"]
    )


def test_table_becomes_adf_table_with_header_row():
    markdown = "| Scenario | Score |\n|---|---:|\n| G1-001 | 0.80 |\n| G1-002 | 0.91 |\n"
    table = next(block for block in _blocks(markdown) if block["type"] == "table")

    assert [row["type"] for row in table["content"]] == ["tableRow"] * 3
    assert [cell["type"] for cell in table["content"][0]["content"]] == ["tableHeader"] * 2
    assert [cell["type"] for cell in table["content"][1]["content"]] == ["tableCell"] * 2
    assert _cell_text(table["content"][1]["content"][0]) == "G1-001"
    assert _cell_text(table["content"][2]["content"][1]) == "0.91"


def test_table_cells_unescape_pipes_and_split_line_breaks():
    markdown = "| Control | Evidence |\n|---|---|\n| A \\| B | first<br>second |\n"
    row = next(block for block in _blocks(markdown) if block["type"] == "table")["content"][1]

    assert _cell_text(row["content"][0]) == "A | B"
    assert _cell_text(row["content"][1]) == "first\nsecond"


def test_table_cells_keep_inline_bold_and_code_marks():
    markdown = "| Name | Field |\n|---|---|\n| **RAG** | `vector_store` |\n"
    row = next(block for block in _blocks(markdown) if block["type"] == "table")["content"][1]

    assert row["content"][0]["content"][0]["content"][0]["marks"] == [{"type": "strong"}]
    assert row["content"][1]["content"][0]["content"][0]["marks"] == [{"type": "code"}]


def test_ragged_rows_are_padded_and_extra_columns_dropped():
    header = "| " + " | ".join(f"C{i}" for i in range(MAX_TABLE_COLUMNS + 2)) + " |"
    delimiter = "|" + "---|" * (MAX_TABLE_COLUMNS + 2)
    markdown = f"{header}\n{delimiter}\n| only-one |\n"
    table = next(block for block in _blocks(markdown) if block["type"] == "table")

    assert len(table["content"][0]["content"]) == MAX_TABLE_COLUMNS
    assert len(table["content"][1]["content"]) == MAX_TABLE_COLUMNS
    assert _cell_text(table["content"][1]["content"][-1]) == ""


def test_pipe_lines_without_delimiter_stay_paragraphs():
    markdown = "| not | a table |\nplain text\n"

    assert all(block["type"] != "table" for block in _blocks(markdown))


def test_table_inside_code_fence_is_not_converted():
    markdown = "```\n| a | b |\n|---|---|\n| 1 | 2 |\n```\n"
    blocks = _blocks(markdown)

    assert _block_types(markdown) == ["codeBlock"]
    assert blocks[0]["content"][0]["text"] == "| a | b |\n|---|---|\n| 1 | 2 |"


def test_list_is_closed_before_a_table_starts():
    markdown = "- item one\n| Key | Value |\n|---|---|\n| k | v |\n"

    assert _block_types(markdown) == ["bulletList", "table"]


def test_blockquote_becomes_adf_blockquote():
    blocks = _blocks("> heads up\n")

    assert blocks[0]["type"] == "blockquote"
    assert blocks[0]["content"][0]["content"][0]["text"] == "heads up"


def test_wide_table_is_transposed_into_one_vertical_table_per_row(monkeypatch):
    monkeypatch.setattr(config, "JIRA_TABLE_TRANSPOSE_MIN_COLUMNS", 2)
    markdown = "| ID | Name | Score |\n|---|---|---|\n| G1-001 | Upload | 0.80 |\n| G1-002 | Export | 0.91 |\n"
    tables = [block for block in _blocks(markdown) if block["type"] == "table"]

    assert len(tables) == 2
    first = tables[0]["content"]
    assert all(len(row["content"]) == 2 for row in first)
    assert [_cell_text(row["content"][0]) for row in first] == ["ID", "Name", "Score"]
    assert [_cell_text(row["content"][1]) for row in first] == ["G1-001", "Upload", "0.80"]
    assert _cell_text(tables[1]["content"][1]["content"][1]) == "Export"


def test_narrow_table_keeps_horizontal_layout(monkeypatch):
    monkeypatch.setattr(config, "JIRA_TABLE_TRANSPOSE_MIN_COLUMNS", 5)
    markdown = "| Metric | Score |\n|---|---|\n| Semantic | 0.72 |\n"
    tables = [block for block in _blocks(markdown) if block["type"] == "table"]

    assert len(tables) == 1
    assert [_cell_text(cell) for cell in tables[0]["content"][0]["content"]] == ["Metric", "Score"]


def test_transposed_header_only_table_falls_back_to_horizontal(monkeypatch):
    monkeypatch.setattr(config, "JIRA_TABLE_TRANSPOSE_MIN_COLUMNS", 2)
    markdown = "| A | B | C |\n|---|---|---|\n"
    tables = [block for block in _blocks(markdown) if block["type"] == "table"]

    assert len(tables) == 1
    assert [_cell_text(cell) for cell in tables[0]["content"][0]["content"]] == ["A", "B", "C"]
