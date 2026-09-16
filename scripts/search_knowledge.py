from de_assistant.retrieval.retriever import Retriever


def main() -> None:
    query = "What is the difference between OLTP and OLAP?"

    print("=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    retriever = Retriever(limit=5)

    results = retriever.retrieve(query)

    for index, result in enumerate(results, start=1):
        print("\n" + "-" * 80)
        print(f"[{index}] Score: {result.score:.4f}")
        print(f"Title   : {result.title}")
        print(f"Heading : {result.heading}")
        print(f"Source  : {result.source}")
        print()
        print(result.content[:700])


if __name__ == "__main__":
    main()