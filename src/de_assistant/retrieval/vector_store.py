import hashlib
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from de_assistant.ingestion.chunker import Chunk


DEFAULT_COLLECTION = "knowledge"
DEFAULT_VECTOR_SIZE = 384
DEFAULT_STORAGE_PATH = Path("data/qdrant")


def make_point_id(chunk_id: str) -> str:
    """
    Generate a deterministic UUID for a chunk.
    """
    digest = hashlib.sha256(chunk_id.encode("utf-8")).hexdigest()

    return str(
        uuid.UUID(digest[:32])
    )


def get_client(
    storage_path: Path = DEFAULT_STORAGE_PATH,
) -> QdrantClient:
    """
    Create a persistent local Qdrant client.
    """
    storage_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return QdrantClient(
        path=str(storage_path),
    )


def create_collection(
    client: QdrantClient,
    collection_name: str = DEFAULT_COLLECTION,
    vector_size: int = DEFAULT_VECTOR_SIZE,
) -> None:
    """
    Create the collection if it does not already exist.
    """
    collections = client.get_collections()

    existing_names = {
        collection.name
        for collection in collections.collections
    }

    if collection_name in existing_names:
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )


def upsert_chunks(
    client: QdrantClient,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    collection_name: str = DEFAULT_COLLECTION,
) -> None:
    """
    Store chunk vectors and retrieval metadata in Qdrant.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks must match number of embeddings."
        )

    points = []

    for chunk, embedding in zip(
        chunks,
        embeddings,
        strict=True,
    ):
        payload = {
            "chunk_id": chunk.id,
            "source": chunk.source,
            "title": chunk.title,
            "heading": chunk.heading,
            "content": chunk.content,
            "metadata": chunk.metadata,
        }

        points.append(
            PointStruct(
                id=make_point_id(chunk.id),
                vector=embedding,
                payload=payload,
            )
        )

    client.upsert(
        collection_name=collection_name,
        points=points,
    )


def search(
    client: QdrantClient,
    query_vector: list[float],
    limit: int = 5,
    collection_name: str = DEFAULT_COLLECTION,
):
    """
    Search the knowledge index.
    """
    return client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
        with_payload=True,
    ).points