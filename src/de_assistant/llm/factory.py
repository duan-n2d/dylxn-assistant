from de_assistant.config import settings
from de_assistant.llm.mock import MockLLM
from de_assistant.llm.ollama import OllamaLLM


def get_llm_client(
    provider: str | None = None,
    *,
    model: str | None = None,
    base_url: str | None = None,
):
    """
    Return the configured LLM implementation for the selected provider.
    """
    provider_name = (provider or settings.llm_provider).lower()

    if provider_name == "mock":
        return MockLLM()

    if provider_name == "ollama":
        return OllamaLLM(
            model=model or settings.ollama_model,
            base_url=base_url or settings.ollama_base_url,
            timeout=settings.ollama_timeout,
            num_predict=settings.ollama_num_predict,
        )

    raise ValueError(
        f"Unsupported LLM provider: {provider_name}. "
        "Expected 'mock' or 'ollama'."
    )
