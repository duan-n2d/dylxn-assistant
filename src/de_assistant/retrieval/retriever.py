from dataclasses import dataclass
from typing import Any

from de_assistant.retrieval.embeddings import embed_query
from de_assistant.retrieval.vector_store import get_client, search


@dataclass
class RetrievedChunk:
    score: float
    content: str
    source: str
    title: str
    heading: str | None
    metadata: dict[str, Any]


class Retriever:
    def __init__(
        self,
        limit: int = 5,
    ) -> None:
        self.limit = limit
        self.client = get_client()

    def retrieve(
        self,
        query: str,
    ) -> list[RetrievedChunk]:
        query_vector = embed_query(query)

        results = search(
            self.client,
            query_vector,
            limit=self.limit,
        )

        chunks: list[RetrievedChunk] = []

        for result in results:
            payload = result.payload or {}

            chunks.append(
                RetrievedChunk(
                    score=float(result.score),
                    content=payload.get("content", ""),
                    source=payload.get("source", ""),
                    title=payload.get("title", ""),
                    heading=payload.get("heading"),
                    metadata=payload.get("metadata", {}),
                )
            )

        return chunks