from de_assistant.retrieval.context import build_context
from de_assistant.retrieval.retriever import Retriever


def main() -> None:
    query = "What is the difference between OLTP and OLAP?"

    retriever = Retriever(limit=5)

    results = retriever.retrieve(query)

    context = build_context(results)

    print("=" * 80)
    print("LLM CONTEXT")
    print("=" * 80)

    print(context.text)

    print("=" * 80)
    print("SOURCES")
    print("=" * 80)

    for index, source in enumerate(
        context.sources,
        start=1,
    ):
        print(
            f"[{index}] "
            f"{source.title} → "
            f"{source.heading}"
        )


if __name__ == "__main__":
    main()