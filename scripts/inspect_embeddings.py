from de_assistant.ingestion.chunker import chunk_documents
from de_assistant.ingestion.loader import load_markdown_files
from de_assistant.ingestion.parser import parse_markdown
from de_assistant.retrieval.embeddings import embed_documents


def main() -> None:
    files = load_markdown_files("knowledge")

    documents = []

    for path in files:
        documents.extend(parse_markdown(path))

    chunks = chunk_documents(documents)

    print("=" * 80)
    print("EMBEDDING INSPECTION")
    print("=" * 80)

    print(f"Files   : {len(files)}")
    print(f"Docs    : {len(documents)}")
    print(f"Chunks  : {len(chunks)}")

    texts = [chunk.content for chunk in chunks]

    print("\nGenerating embeddings...")

    embeddings = embed_documents(texts)

    print("\nEmbedding result:")
    print(f"Vectors : {len(embeddings)}")
    print(f"Dimension: {len(embeddings[0])}")

    print("\nFirst vector:")
    print(embeddings[0][:10])


if __name__ == "__main__":
    main()