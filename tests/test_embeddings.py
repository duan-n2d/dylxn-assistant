from de_assistant.retrieval.embeddings import embed_documents, embed_query


def test_embed_documents() -> None:
    embeddings = embed_documents(
        [
            "Data modeling is the design of data for analytics.",
            "OLTP systems support transactional workloads.",
        ]
    )

    assert len(embeddings) == 2
    assert len(embeddings[0]) > 0
    assert len(embeddings[0]) == len(embeddings[1])


def test_embed_query() -> None:
    embedding = embed_query("What is data modeling?")

    assert len(embedding) > 0