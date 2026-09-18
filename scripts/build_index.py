from de_assistant.ingestion.chunker import chunk_documents
from de_assistant.ingestion.loader import load_markdown_files
from de_assistant.ingestion.parser import parse_markdown
from de_assistant.retrieval.embeddings import embed_documents
from de_assistant.retrieval.keyword_store import index_chunks
from de_assistant.retrieval.vector_store import (
    create_collection,
    get_client,
    upsert_chunks,
)


def main() -> None:
    print("=" * 80)
    print("BUILD KNOWLEDGE INDEX")
    print("=" * 80)

    # ---------------------------------------------------------
    # Load Markdown
    # ---------------------------------------------------------
    files = load_markdown_files("knowledge")

    documents = []

    for path in files:
        documents.extend(
            parse_markdown(path)
        )

    print(f"Markdown files : {len(files)}")
    print(f"Documents      : {len(documents)}")

    # ---------------------------------------------------------
    # Chunk
    # ---------------------------------------------------------
    chunks = chunk_documents(documents)

    print(f"Chunks         : {len(chunks)}")

    # ---------------------------------------------------------
    # Embeddings
    # ---------------------------------------------------------
    print("\nGenerating embeddings...")

    embeddings = embed_documents(
        [chunk.content for chunk in chunks]
    )

    print(
        f"Embedding dimension: {len(embeddings[0])}"
    )

    # ---------------------------------------------------------
    # Qdrant
    # ---------------------------------------------------------
    client = get_client()

    create_collection(
        client,
        vector_size=len(embeddings[0]),
    )

    upsert_chunks(
        client,
        chunks,
        embeddings,
    )

    index_chunks(chunks)

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------
    collection = client.get_collection("knowledge")

    print("\n" + "=" * 80)
    print("INDEX COMPLETE")
    print("=" * 80)

    print(f"Collection : {collection.config.params.vectors.size}")
    print(f"Vectors    : {collection.points_count}")


if __name__ == "__main__":
    main()