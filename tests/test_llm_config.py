from backend.app.services.llm_client import LLMClient


def test_llm_disabled_by_default_or_env_safe():
    client = LLMClient()
    # The test must never require a real key. It only verifies that the client
    # can be constructed and exposes a boolean availability result.
    assert isinstance(client.is_available(), bool)
