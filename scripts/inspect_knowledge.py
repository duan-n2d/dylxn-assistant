from de_assistant.ingestion.loader import load_markdown_files


def main() -> None:
    files = load_markdown_files("knowledge")

    print(f"Found {len(files)} Markdown files:\n")

    for path in files:
        print(path)


if __name__ == "__main__":
    main()