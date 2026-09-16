from pathlib import Path

from de_assistant.ingestion.chunker import chunk_documents
from de_assistant.ingestion.loader import load_markdown_files
from de_assistant.ingestion.models import Document
from de_assistant.ingestion.parser import parse_frontmatter, parse_markdown


def test_load_markdown_files(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A")
    (tmp_path / "b.md").write_text("# B")
    (tmp_path / "ignore.txt").write_text("ignore")

    files = load_markdown_files(tmp_path)

    assert len(files) == 2


def test_parse_frontmatter() -> None:
    text = """---
title: Test Document
type: tutorial
tags:
  - dbt
  - modeling
---

# Hello

Content.
"""

    metadata, body = parse_frontmatter(text)

    assert metadata["title"] == "Test Document"
    assert metadata["type"] == "tutorial"
    assert metadata["tags"] == ["dbt", "modeling"]
    assert "# Hello" in body


def test_parse_markdown(tmp_path: Path) -> None:
    path = tmp_path / "test.md"

    path.write_text(
        """# Data Modeling

Introduction.

## Fact Tables

Fact table content.

## Dimensions

Dimension content.
""",
        encoding="utf-8",
    )

    documents = parse_markdown(path)

    assert len(documents) == 3
    assert documents[0].heading == "Data Modeling"
    assert documents[1].heading == "Fact Tables"
    assert documents[2].heading == "Dimensions"


def test_chunk_documents() -> None:
    document = Document(
        source="test.md",
        title="Test",
        heading="Section",
        content="A " * 2000,
        metadata={"domain": "data-engineering"},
    )

    chunks = chunk_documents(
        [document],
        max_chars=500,
        overlap_chars=50,
    )

    assert len(chunks) > 1
    assert all(chunk.source == "test.md" for chunk in chunks)
    assert all(chunk.heading == "Section" for chunk in chunks)
