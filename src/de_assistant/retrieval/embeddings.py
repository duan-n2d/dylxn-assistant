from functools import lru_cache

from sentence_transformers import SentenceTransformer


DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


@lru_cache(maxsize=1)
def get_embedding_model(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_documents(
    texts: list[str],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list[list[float]]:
    model = get_embedding_model(model_name)

    passages = [
        f"passage: {text}"
        for text in texts
    ]

    embeddings = model.encode(
        passages,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return embeddings.tolist()


def embed_query(
    query: str,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list[float]:
    model = get_embedding_model(model_name)

    embedding = model.encode(
        f"query: {query}",
        normalize_embeddings=True,
    )

    return embedding.tolist()