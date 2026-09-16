from collections import Counter

from de_assistant.ingestion.chunker import chunk_documents
from de_assistant.ingestion.loader import load_markdown_files
from de_assistant.ingestion.parser import parse_markdown


def main() -> None:
    files = load_markdown_files("knowledge")

    documents = []

    for path in files:
        documents.extend(parse_markdown(path))

    chunks = chunk_documents(documents)

    print("=" * 80)
    print("KNOWLEDGE INGESTION SUMMARY")
    print("=" * 80)

    print(f"Markdown files : {len(files)}")
    print(f"Documents      : {len(documents)}")
    print(f"Chunks         : {len(chunks)}")

    print("\nChunk size:")
    print(f"  Min: {min(len(c.content) for c in chunks)}")
    print(f"  Max: {max(len(c.content) for c in chunks)}")
    print(
        f"  Avg: "
        f"{sum(len(c.content) for c in chunks) / len(chunks):.0f}"
    )

    print("\nChunks by source:")

    counter = Counter(chunk.source for chunk in chunks)

    for source, count in counter.items():
        print(f"  {source}: {count}")

    print("\nSample chunks:")

    for i, chunk in enumerate(chunks[:10], start=1):
        print("\n" + "-" * 80)
        print(f"[{i}] {chunk.heading}")
        print(f"Source: {chunk.source}")
        print(f"Length: {len(chunk.content)}")
        print(f"Content:\n{chunk.content[:500]}")


if __name__ == "__main__":
    main()
