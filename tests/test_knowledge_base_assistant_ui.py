from pathlib import Path


def test_golden_kb_assistant_ui_keeps_generation_and_sync_as_separate_actions():
    html = (Path(__file__).parents[1] / "backend" / "app" / "static" / "index.html").read_text(encoding="utf-8")

    assert 'id="kbAssistantChat"' in html
    assert 'id="kbAssistantDraft"' in html
    assert "askKbAssistant()" in html
    assert "applyKbAssistantDraft()" in html
    assert "/assistant/propose" in html
    assert "onclick=\"saveKb()\"" in html
    assert "Confirm & Sync KB" in html
