import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_FTS_DB = Path("data/knowledge_fts.db")


def get_connection(
    db_path: Path = DEFAULT_FTS_DB,
) -> sqlite3.Connection:
    """
    Open a SQLite connection with an FTS5 table for keyword search.
    """
    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    connection.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(
            chunk_id UNINDEXED,
            source,
            title,
            heading,
            content,
            metadata,
            tokenize='porter unicode61'
        )
        """
    )

    return connection


def _get_field(value: Any, *keys: str) -> Any:
    for key in keys:
        if isinstance(value, dict) and key in value:
            return value[key]

    return None


def index_chunks(chunks: list[Any]) -> None:
    """
    Store chunk metadata and content into SQLite FTS index.
    """
    if not chunks:
        return

    with get_connection() as connection:
        connection.execute("DELETE FROM chunks_fts")

        for chunk in chunks:
            if hasattr(chunk, "id"):
                chunk_id = getattr(chunk, "id")
                source = getattr(chunk, "source")
                title = getattr(chunk, "title")
                heading = getattr(chunk, "heading")
                content = getattr(chunk, "content")
                metadata = getattr(chunk, "metadata", {})
            else:
                chunk_id = _get_field(chunk, "chunk_id", "id")
                source = _get_field(chunk, "source")
                title = _get_field(chunk, "title")
                heading = _get_field(chunk, "heading")
                content = _get_field(chunk, "content")
                metadata = _get_field(chunk, "metadata", {}) or {}

            connection.execute(
                """
                INSERT INTO chunks_fts (
                    chunk_id,
                    source,
                    title,
                    heading,
                    content,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(chunk_id),
                    str(source or ""),
                    str(title or ""),
                    str(heading or ""),
                    str(content or ""),
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )

        connection.commit()


def keyword_search(
    query: str,
    limit: int = 5,
    db_path: Path = DEFAULT_FTS_DB,
) -> list[dict[str, Any]]:
    """
    Fuse lexical matches with the semantic candidate set.
    Returns a list of match dictionaries with a SQLite BM25 score.
    """
    if not query or not query.strip():
        return []

    normalized = " ".join(query.split())
    if not normalized:
        return []

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                chunk_id,
                source,
                title,
                heading,
                content,
                metadata,
                bm25(chunks_fts) AS score
            FROM chunks_fts
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts)
            LIMIT ?
            """,
            (normalized, limit),
        ).fetchall()

    results: list[dict[str, Any]] = []

    for row in rows:
        metadata = row["metadata"]

        try:
            parsed_metadata = json.loads(metadata) if metadata else {}
        except json.JSONDecodeError:
            parsed_metadata = {}

        results.append(
            {
                "chunk_id": row["chunk_id"],
                "source": row["source"],
                "title": row["title"],
                "heading": row["heading"],
                "content": row["content"],
                "metadata": parsed_metadata,
                "score": float(row["score"]),
            }
        )

    return results
