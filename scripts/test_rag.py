from de_assistant.llm.mock import MockLLM
from de_assistant.rag import RAGService
from de_assistant.retrieval.retriever import Retriever


def main() -> None:
    question = (
        "What is the difference between OLTP and OLAP?"
    )

    retriever = Retriever(limit=5)

    llm = MockLLM()

    rag = RAGService(
        retriever=retriever,
        llm=llm,
    )

    response = rag.ask(question)

    print("=" * 80)
    print("RAG TEST")
    print("=" * 80)

    print("\nQuestion:")
    print(question)

    print("\nAnswer:")
    print(response.answer)

    print("\nSources:")

    for index, source in enumerate(
        response.sources,
        start=1,
    ):
        print(
            f"[{index}] "
            f"{source.title} → "
            f"{source.heading}"
        )


if __name__ == "__main__":
    main()