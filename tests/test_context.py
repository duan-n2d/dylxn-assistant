from de_assistant.retrieval.context import build_context
from de_assistant.retrieval.retriever import RetrievedChunk


def test_build_context() -> None:
    chunks = [
        RetrievedChunk(
            score=0.9,
            content="OLTP supports transactions.",
            source="knowledge/test.md",
            title="Data Modeling",
            heading="OLTP",
            metadata={},
        ),
        RetrievedChunk(
            score=0.8,
            content="OLAP supports analytics.",
            source="knowledge/test.md",
            title="Data Modeling",
            heading="OLAP",
            metadata={},
        ),
    ]

    context = build_context(chunks)

    assert "[Source 1]" in context.text
    assert "[Source 2]" in context.text
    assert "OLTP supports transactions." in context.text
    assert "OLAP supports analytics." in context.text

    assert len(context.sources) == 2
    assert context.sources[0].heading == "OLTP"