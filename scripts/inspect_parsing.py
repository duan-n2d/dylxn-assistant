from de_assistant.ingestion.loader import load_markdown_files
from de_assistant.ingestion.parser import parse_markdown


def main() -> None:
    files = load_markdown_files("knowledge")

    total_documents = 0

    for path in files:
        documents = parse_markdown(path)

        print("\n" + "=" * 80)
        print(path)
        print("=" * 80)

        for i, document in enumerate(documents, start=1):
            print(f"\n[{i}] {document.heading}")
            print(f"Content: {document.content[:200]!r}")
            print(f"Metadata: {document.metadata}")

        total_documents += len(documents)

    print("\n" + "=" * 80)
    print(f"Files: {len(files)}")
    print(f"Documents: {total_documents}")


if __name__ == "__main__":
    main()