import re
from pathlib import Path

from markdown_it import MarkdownIt

from de_assistant.ingestion.models import Document


FRONTMATTER_PATTERN = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n?",
    re.DOTALL,
)


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """
    Extract simple YAML-like frontmatter.

    Example:

    ---
    title: Data Modeling
    domain: data-engineering
    tags:
      - dbt
      - dimensional-modeling
    ---
    """
    match = FRONTMATTER_PATTERN.match(text)

    if not match:
        return {}, text

    raw = match.group(1)
    metadata: dict[str, object] = {}

    current_list_key: str | None = None

    for line in raw.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("- ") and current_list_key:
            values = metadata.setdefault(current_list_key, [])
            if isinstance(values, list):
                values.append(stripped[2:].strip())
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not value:
            metadata[key] = []
            current_list_key = key
        else:
            metadata[key] = value.strip("\"'")
            current_list_key = None

    return metadata, text[match.end():]


def parse_markdown(path: str | Path) -> list[Document]:
    """Parse a Markdown file into heading-based documents."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    metadata, markdown = parse_frontmatter(text)

    md = MarkdownIt()
    tokens = md.parse(markdown)

    documents: list[Document] = []

    title = str(metadata.get("title") or path.stem)

    current_heading: str | None = None
    current_content: list[str] = []

    def flush() -> None:
        if not current_content:
            return

        content = "\n".join(current_content).strip()

        if not content:
            return

        documents.append(
            Document(
                source=str(path),
                title=title,
                heading=current_heading,
                content=content,
                metadata=metadata.copy(),
            )
        )

    for token in tokens:
        if token.type == "heading_open":
            flush()
            current_content.clear()

        elif token.type == "inline":
            text_content = token.content.strip()

            if current_heading is None:
                # First heading becomes the document title if no
                # explicit frontmatter title exists.
                if title == path.stem:
                    title = text_content

                current_heading = text_content
            else:
                current_content.append(text_content)

        elif token.type in {"paragraph_close", "heading_close"}:
            continue

        elif token.type == "fence":
            current_content.append(token.content.strip())

        elif token.type == "code_block":
            current_content.append(token.content.strip())

    flush()

    return documents