from dataclasses import dataclass

from de_assistant.retrieval.retriever import RetrievedChunk


@dataclass
class Context:
    text: str
    sources: list[RetrievedChunk]


def build_context(
    chunks: list[RetrievedChunk],
) -> Context:
    """
    Convert retrieved chunks into LLM-ready context.

    Each chunk receives a stable citation number.
    """
    sections: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        sections.append(
            f"""[Source {index}]
Title: {chunk.title}
Section: {chunk.heading or "Root"}
Source: {chunk.source}

{chunk.content}
"""
        )

    return Context(
        text="\n\n".join(sections),
        sources=chunks,
    )