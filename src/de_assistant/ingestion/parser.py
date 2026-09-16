from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt
import yaml

from de_assistant.ingestion.models import Document


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from a Markdown document.
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)

    if len(parts) < 3:
        return {}, text

    _, raw_frontmatter, body = parts

    metadata = yaml.safe_load(raw_frontmatter) or {}

    if not isinstance(metadata, dict):
        metadata = {}

    return metadata, body.lstrip()


def parse_markdown(path: Path) -> list[Document]:
    """
    Parse a Markdown file into heading-aware Documents.
    """
    text = path.read_text(encoding="utf-8")

    metadata, body = parse_frontmatter(text)

    md = MarkdownIt()
    tokens = md.parse(body)

    title = metadata.get("title")

    documents: list[Document] = []

    current_heading: str | None = None
    current_heading_level: int | None = None
    current_content: list[str] = []

    inside_heading = False
    heading_buffer: list[str] = []

    def flush_document() -> None:
        nonlocal current_content

        content = "\n".join(current_content).strip()

        if not content:
            current_content = []
            return

        document_metadata = {
            **metadata,
        }

        if current_heading_level is not None:
            document_metadata["heading_level"] = current_heading_level

        documents.append(
            Document(
                source=str(path),
                title=title or current_heading or path.stem,
                heading=current_heading,
                content=content,
                metadata=document_metadata,
            )
        )

        current_content = []

    for token in tokens:
        # ---------------------------------------------------------
        # Heading
        # ---------------------------------------------------------
        if token.type == "heading_open":
            flush_document()

            inside_heading = True
            heading_buffer = []

            current_heading_level = int(token.tag[1])

            continue

        if token.type == "heading_close":
            current_heading = " ".join(heading_buffer).strip()

            if title is None and current_heading_level == 1:
                title = current_heading

            inside_heading = False
            heading_buffer = []

            continue

        # ---------------------------------------------------------
        # Inline text
        # ---------------------------------------------------------
        if token.type == "inline":
            text_content = token.content.strip()

            if inside_heading:
                heading_buffer.append(text_content)
            elif text_content:
                current_content.append(text_content)

            continue

        # ---------------------------------------------------------
        # Fenced code block
        # ---------------------------------------------------------
        if token.type == "fence":
            code = token.content.rstrip()

            language = token.info.strip()

            if language:
                current_content.append(
                    f"```{language}\n{code}\n```"
                )
            else:
                current_content.append(
                    f"```\n{code}\n```"
                )

            continue

        # ---------------------------------------------------------
        # Indented code block
        # ---------------------------------------------------------
        if token.type == "code_block":
            current_content.append(
                f"```\n{token.content.rstrip()}\n```"
            )

            continue

    # Flush final section
    flush_document()

    return documents