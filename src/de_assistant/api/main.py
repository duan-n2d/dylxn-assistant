from fastapi import FastAPI
from pydantic import BaseModel

from de_assistant.config import settings
from de_assistant.llm.factory import get_llm_client
from de_assistant.rag import RAGService
from de_assistant.retrieval.retriever import Retriever


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Personal Data Engineering Assistant",
)


# ---------------------------------------------------------------------------
# RAG service
# ---------------------------------------------------------------------------

retriever = Retriever(
    limit=settings.retrieval_limit,
)

llm = get_llm_client(
    settings.llm_provider,
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
)

rag = RAGService(
    retriever=retriever,
    llm=llm,
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


class SourceResponse(BaseModel):
    title: str
    heading: str | None
    source: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------

@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    response = rag.ask(
        request.question,
    )

    sources = [
        SourceResponse(
            title=source.title,
            heading=source.heading,
            source=source.source,
            score=source.score,
        )
        for source in response.sources
    ]

    return AskResponse(
        answer=response.answer,
        sources=sources,
    )