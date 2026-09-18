from unittest.mock import patch

from de_assistant.retrieval.retriever import Retriever


class FakeResult:
    def __init__(self, score=0.91, payload=None):
        self.score = score
        self.payload = payload or {
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
    ), patch(
        "de_assistant.retrieval.retriever.keyword_search",
        return_value=[],
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


def test_retriever_hybrid_search_combines_scores() -> None:
    with patch(
        "de_assistant.retrieval.retriever.embed_query",
        return_value=[0.1, 0.2, 0.3],
    ), patch(
        "de_assistant.retrieval.retriever.get_client",
    ), patch(
        "de_assistant.retrieval.retriever.search",
        return_value=[FakeResult(score=0.91)],
    ), patch(
        "de_assistant.retrieval.retriever.keyword_search",
        return_value=[
            {
                "chunk_id": "chunk-1",
                "content": "OLAP is designed for analytical workloads.",
                "source": "knowledge/test.md",
                "title": "Data Modeling",
                "heading": "OLAP",
                "metadata": {"domain": "data-engineering"},
                "score": 0.75,
            }
        ],
    ):
        retriever = Retriever(limit=5, hybrid_weight=0.7, keyword_weight=0.3)

        results = retriever.retrieve("What is OLAP?")

    assert len(results) == 1
    assert results[0].score == 0.862
    assert results[0].heading == "OLAP"


def test_retriever_filters_under_threshold() -> None:
    with patch(
        "de_assistant.retrieval.retriever.embed_query",
        return_value=[0.1, 0.2, 0.3],
    ), patch(
        "de_assistant.retrieval.retriever.get_client",
    ), patch(
        "de_assistant.retrieval.retriever.search",
        return_value=[FakeResult(score=0.30)],
    ), patch(
        "de_assistant.retrieval.retriever.keyword_search",
        return_value=[],
    ):
        retriever = Retriever(limit=5, min_score=0.5)

        results = retriever.retrieve("What is OLAP?")

    assert results == []