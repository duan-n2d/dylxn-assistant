from dataclasses import dataclass

from de_assistant.ingestion.models import Document


@dataclass
class Chunk:
    id: str
    source: str
    title: str
    heading: str | None
    content: str
    metadata: dict[str, object]


DEFAULT_MAX_CHARS = 1800
DEFAULT_OVERLAP_CHARS = 200


def _split_text(
    text: str,
    max_chars: int,
    overlap_chars: int,
) -> list[str]:
    """
    Split long text while trying to preserve paragraph boundaries.
    """
    if len(text) <= max_chars:
        return [text.strip()]

    paragraphs = text.split("\n\n")

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        candidate = (
            paragraph
            if not current
            else f"{current}\n\n{paragraph}"
        )

        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())

        # Very large individual blocks need a hard split.
        if len(paragraph) > max_chars:
            start = 0

            while start < len(paragraph):
                end = min(start + max_chars, len(paragraph))
                chunks.append(paragraph[start:end].strip())

                if end >= len(paragraph):
                    break

                start = max(end - overlap_chars, start + 1)

            current = ""
        else:
            current = paragraph

    if current:
        chunks.append(current.strip())

    return chunks


def chunk_documents(
    documents: list[Document],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    """
    Convert parsed Documents into retrieval-friendly chunks.
    """
    chunks: list[Chunk] = []

    for document in documents:
        pieces = _split_text(
            document.content,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )

        for index, content in enumerate(pieces):
            chunk_id = (
                f"{document.source}:"
                f"{document.heading or 'root'}:"
                f"{index}"
            )

            metadata = {
                **document.metadata,
                "source": document.source,
                "title": document.title,
                "heading": document.heading,
                "chunk_index": index,
            }

            chunks.append(
                Chunk(
                    id=chunk_id,
                    source=document.source,
                    title=document.title,
                    heading=document.heading,
                    content=content,
                    metadata=metadata,
                )
            )

    return chunks
