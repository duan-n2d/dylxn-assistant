from dataclasses import dataclass
from typing import Any

from de_assistant.retrieval.embeddings import embed_query
from de_assistant.retrieval.keyword_store import keyword_search
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
        hybrid_weight: float = 0.7,
        keyword_weight: float = 0.3,
        min_score: float = 0.0,
    ) -> None:
        self.limit = limit
        self.hybrid_weight = hybrid_weight
        self.keyword_weight = keyword_weight
        self.min_score = min_score
        self.client = get_client()

    def _normalize_keyword_score(self, score: float | None) -> float:
        if score is None:
            return 0.0

        value = float(score)
        return max(value, 0.0)

    def _build_chunk(
        self,
        content: str,
        source: str,
        title: str,
        heading: str | None,
        metadata: dict[str, Any],
        score: float,
    ) -> RetrievedChunk:
        return RetrievedChunk(
            score=float(score),
            content=content,
            source=source,
            title=title,
            heading=heading,
            metadata=metadata,
        )

    def _identity(
        self,
        content: str,
        source: str,
        title: str,
        heading: str | None,
    ) -> str:
        raw = f"{source}|{title}|{heading or ''}|{content}"
        return raw.strip()

    def retrieve(
        self,
        query: str,
    ) -> list[RetrievedChunk]:
        query_vector = embed_query(query)

        semantic_results = search(
            self.client,
            query_vector,
            limit=max(self.limit * 3, self.limit),
        )

        keyword_results = keyword_search(
            query,
            limit=max(self.limit * 3, self.limit),
        )

        keyword_by_identity: dict[str, float] = {
            self._identity(
                str(item.get("content", "")),
                str(item.get("source", "")),
                str(item.get("title", "")),
                item.get("heading"),
            ): self._normalize_keyword_score(item.get("score"))
            for item in keyword_results
        }

        fused: dict[str, tuple[RetrievedChunk, float]] = {}

        for result in semantic_results:
            payload = result.payload or {}
            content = str(payload.get("content", ""))
            source = str(payload.get("source", ""))
            title = str(payload.get("title", ""))
            heading = payload.get("heading")
            identity = self._identity(content, source, title, heading)
            semantic_score = float(result.score)
            keyword_score = keyword_by_identity.get(identity, 0.0)

            if keyword_score > 0:
                combined_score = (
                    semantic_score * self.hybrid_weight
                    + keyword_score * self.keyword_weight
                )
            else:
                combined_score = semantic_score

            if combined_score < self.min_score:
                continue

            chunk = self._build_chunk(
                content=content,
                source=source,
                title=title,
                heading=heading,
                metadata=payload.get("metadata", {}),
                score=combined_score,
            )
            fused[identity] = (chunk, combined_score)

        for item in keyword_results:
            content = str(item.get("content", ""))
            source = str(item.get("source", ""))
            title = str(item.get("title", ""))
            heading = item.get("heading")
            identity = self._identity(content, source, title, heading)
            if identity in fused:
                continue

            keyword_score = self._normalize_keyword_score(item.get("score"))
            combined_score = keyword_score * self.keyword_weight

            if combined_score < self.min_score:
                continue

            chunk = self._build_chunk(
                content=content,
                source=source,
                title=title,
                heading=heading,
                metadata=item.get("metadata", {}),
                score=combined_score,
            )
            fused[identity] = (chunk, combined_score)

        chunks = [chunk for chunk, _ in sorted(
            fused.values(),
            key=lambda pair: pair[1],
            reverse=True,
        )][: self.limit]

        return chunks