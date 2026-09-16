from de_assistant.llm.client import LLMClient


class MockLLM:
    """
    Development-only LLM.

    Used to test the RAG pipeline without
    requiring a real local model.
    """

    def generate(
        self,
        prompt: str,
        system: str | None = None,
    ) -> str:
        return (
            "This is a mock response. "
            "The RAG pipeline successfully generated "
            "a prompt for the LLM."
        )