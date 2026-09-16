from unittest.mock import patch

from de_assistant.retrieval.retriever import Retriever


class FakeResult:
    score = 0.91
    payload = {
        "content": "OLAP is designed for analytical workloads.",
        "source": "knowledge/test.md",
        "title": "Data Modeling",
        "heading": "OLAP",
        "metadata": {
            "domain": "data-engineering",
        },
    }


def test_retriever() -> None:
    with patch(
        "de_assistant.retrieval.retriever.embed_query",
        return_value=[0.1, 0.2, 0.3],
    ), patch(
        "de_assistant.retrieval.retriever.get_client",
    ) as mock_client, patch(
        "de_assistant.retrieval.retriever.search",
        return_value=[FakeResult()],
    ):
        retriever = Retriever(limit=5)

        results = retriever.retrieve(
            "What is OLAP?"
        )

    assert len(results) == 1
    assert results[0].score == 0.91
    assert results[0].heading == "OLAP"
    assert results[0].source == "knowledge/test.md"

    mock_client.assert_called_once()