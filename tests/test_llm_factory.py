from de_assistant.llm.factory import get_llm_client
from de_assistant.llm.mock import MockLLM
from de_assistant.llm.ollama import OllamaLLM


def test_get_llm_client_mock() -> None:
    client = get_llm_client("mock")

    assert isinstance(client, MockLLM)


def test_get_llm_client_ollama() -> None:
    client = get_llm_client("ollama")

    assert isinstance(client, OllamaLLM)


def test_get_llm_client_invalid_provider() -> None:
    try:
        get_llm_client("unknown")
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Unsupported LLM provider" in str(exc)
