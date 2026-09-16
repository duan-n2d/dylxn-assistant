from dataclasses import dataclass

from de_assistant.llm.client import LLMClient
from de_assistant.llm.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from de_assistant.retrieval.context import (
    Context,
    build_context,
)
from de_assistant.retrieval.retriever import (
    RetrievedChunk,
    Retriever,
)


@dataclass
class RAGResponse:
    answer: str
    sources: list[RetrievedChunk]


class RAGService:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLMClient,
    ) -> None:
        self.retriever = retriever
        self.llm = llm

    def ask(
        self,
        question: str,
    ) -> RAGResponse:
        chunks = self.retriever.retrieve(
            question
        )

        context: Context = build_context(
            chunks
        )

        prompt = build_user_prompt(
            question=question,
            context=context.text,
        )

        answer = self.llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT,
        )

        return RAGResponse(
            answer=answer,
            sources=context.sources,
        )