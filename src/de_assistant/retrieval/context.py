from dataclasses import dataclass

from de_assistant.config import settings
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
    remaining = settings.context_max_chars

    for index, chunk in enumerate(chunks, start=1):
        section = f"""[Source {index}]
Title: {chunk.title}
Section: {chunk.heading or "Root"}
Source: {chunk.source}

{chunk.content}
    """
        if remaining <= 0:
            break
        sections.append(section[:remaining])
        remaining -= len(section)

    return Context(
        text="\n\n".join(sections),
        sources=chunks,
    )