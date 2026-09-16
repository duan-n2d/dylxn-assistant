# Dylxn Assistant

A local-first **Data Engineering Assistant** built with Python, RAG, vector search, and pluggable LLM backends.

The project is designed to become a personal knowledge assistant for Data Engineering topics such as:

- Data Modeling
- SQL
- Databases
- Data Warehousing
- dbt
- Streaming
- Cloud Data Platforms
- Data Engineering Architecture
- Data Engineering Interviews

The knowledge base is maintained as Markdown files, making it easy to version, review, edit, and rebuild the search index.

---

## Architecture

Current architecture:

```text
                    Markdown Knowledge
                           │
                           ▼
                    Loader / Parser
                           │
                           ▼
                        Chunker
                           │
                           ▼
                    E5 Embeddings
                           │
                           ▼
                        Qdrant
                           │
                           ▼
                       Retriever
                           │
                           ▼
                      RAG Service
                           │
                    ┌──────┴──────┐
                    │             │
                 Context       LLM Client
                                  │
                           ┌──────┴──────┐
                           │             │
                        MockLLM      OllamaLLM
                           │             │
                           └──────┬──────┘
                                  │
                                  ▼
                              FastAPI
                                  │
                                  ▼
                              /ask API
````

### Planned architecture

```text
Markdown
   │
   ▼
Ingestion
   │
   ├── Parser
   ├── Chunker
   └── Metadata
   │
   ▼
Retrieval Layer
   │
   ├── Vector Search ────── Qdrant
   │
   ├── Keyword Search ───── SQLite FTS5
   │
   └── Reranker (optional)
   │
   ▼
RAG
   │
   ├── Context Builder
   ├── Prompt Builder
   └── Citation
   │
   ▼
LLM
   │
   └── Ollama / other local backend
   │
   ▼
FastAPI
   │
   ▼
Streamlit UI / MCP
```

---

## Features

### Current

* Markdown knowledge ingestion
* YAML frontmatter parsing
* Markdown heading-aware parsing
* Semantic chunking
* Local embedding generation
* `multilingual-e5-small` embeddings
* Persistent local Qdrant vector database
* Semantic retrieval
* RAG context construction
* Source metadata and retrieval scores
* Pluggable LLM interface
* Mock LLM for development
* Ollama LLM client
* FastAPI API
* `/health` endpoint
* `/ask` endpoint
* Automated tests

### Planned

* Hybrid search with SQLite FTS5
* Retrieval score fusion
* Reranking
* Real Ollama integration
* Conversation memory
* Streaming responses
* Streamlit UI
* MCP server
* Knowledge graph / entity relationships
* Learning and interview modes
* Better citation rendering
* Evaluation dataset and RAG metrics

---

## Tech Stack

| Component       | Technology                       |
| --------------- | -------------------------------- |
| Language        | Python 3.12                      |
| Package manager | uv                               |
| API             | FastAPI                          |
| Server          | Uvicorn                          |
| Embeddings      | `intfloat/multilingual-e5-small` |
| Vector database | Qdrant                           |
| Markdown parser | markdown-it-py                   |
| Configuration   | pydantic-settings                |
| HTTP client     | HTTPX                            |
| LLM             | Ollama / MockLLM                 |
| Testing         | pytest                           |
| Linting         | Ruff                             |

---

## Project Structure

```text
dylxn-assistant/
│
├── knowledge/
│   └── Data Modeling & dbt/
│       ├── 01-foundation-raw-to-analytical-model.md
│       ├── 02-setup-dbt-core-duckdb.md
│       ├── 03-dimensional-modeling-deep-dive.md
│       ├── Portfolio Projects/
│       │   └── 00-ref.md
│       └── books.md
│
├── src/
│   └── de_assistant/
│       ├── __init__.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   └── main.py
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   ├── models.py
│       │   ├── parser.py
│       │   └── chunker.py
│       │
│       ├── retrieval/
│       │   ├── __init__.py
│       │   ├── embeddings.py
│       │   ├── vector_store.py
│       │   ├── retriever.py
│       │   └── context.py
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── mock.py
│       │   ├── ollama.py
│       │   └── prompts.py
│       │
│       ├── config.py
│       └── rag.py
│
├── scripts/
│   ├── inspect_knowledge.py
│   ├── inspect_parsing.py
│   ├── inspect_chunks.py
│   ├── inspect_embeddings.py
│   ├── build_index.py
│   ├── search_knowledge.py
│   ├── inspect_context.py
│   ├── test_rag.py
│   └── test_ollama.py
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_embeddings.py
│   ├── test_retriever.py
│   └── test_context.py
│
├── data/
│   └── qdrant/
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

---

# Getting Started

## Requirements

* Python 3.12+
* `uv`
* Git

Ollama is **not required** for the current development setup because the project includes `MockLLM`.

---

## 1. Clone the repository

```bash
git clone https://github.com/duan-n2d/dylxn-assistant.git
cd dylxn-assistant
```

---

## 2. Install dependencies

```bash
uv sync
```

---

## 3. Configure environment

Copy the example environment file:

```bash
cp .env.example .env
```

Default configuration:

```env
APP_NAME=Dylxn Assistant
APP_VERSION=0.1.0

RETRIEVAL_LIMIT=5

LLM_PROVIDER=mock

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
```

For Codespaces, keep:

```env
LLM_PROVIDER=mock
```

---

# Knowledge Base

Knowledge is stored as Markdown.

Example:

```markdown
---
title: Change Data Capture
type: concept
domain: data-engineering
tags:
  - cdc
  - ingestion
  - streaming
---

# Change Data Capture

Change Data Capture is a technique for identifying
and propagating changes from a source database.
```

The Markdown files are the **source of truth**.

The Qdrant index is generated data and can be rebuilt at any time.

---

# Build the Vector Index

After adding or modifying knowledge files:

```bash
uv run python scripts/build_index.py
```

This performs:

```text
Markdown
   ↓
Parser
   ↓
Chunks
   ↓
Embeddings
   ↓
Qdrant
```

The local Qdrant database is stored under:

```text
data/qdrant/
```

It should not be committed to Git.

---

# Inspect Knowledge

List knowledge files:

```bash
uv run python scripts/inspect_knowledge.py
```

Inspect parsed Markdown:

```bash
uv run python scripts/inspect_parsing.py
```

Inspect chunks:

```bash
uv run python scripts/inspect_chunks.py
```

Inspect embeddings:

```bash
uv run python scripts/inspect_embeddings.py
```

Inspect retrieved context:

```bash
uv run python scripts/inspect_context.py
```

---

# Semantic Search

Search the knowledge base:

```bash
uv run python scripts/search_knowledge.py
```

Example question:

```text
What is the difference between OLTP and OLAP?
```

Example retrieval:

```text
[1] OLAP — Online Analytical Processing
    score: 0.8594

[2] OLTP — Online Transaction Processing
    score: 0.8492

[3] So sánh nhanh
    score: 0.8338
```

The exact scores may change depending on the embedding model and index.

---

# RAG Pipeline

The RAG service combines:

```text
Question
   │
   ▼
Retriever
   │
   ▼
Top-K knowledge chunks
   │
   ▼
Context Builder
   │
   ▼
Prompt Builder
   │
   ▼
LLM
   │
   ▼
Answer + Sources
```

Run the current end-to-end RAG test:

```bash
uv run python scripts/test_rag.py
```

The current Codespace setup uses `MockLLM`.

Example:

```text
================================================================================
RAG TEST
================================================================================

Question:
What is the difference between OLTP and OLAP?

Answer:
This is a mock response. The RAG pipeline successfully generated
a prompt for the LLM.

Sources:
[1] Data Modeling & dbt → OLAP — Online Analytical Processing
[2] Data Modeling & dbt → OLTP — Online Transaction Processing
[3] Data Modeling & dbt → So sánh nhanh
...
```

This verifies that retrieval, context construction, prompting, and the LLM interface are connected correctly.

---

# FastAPI

Start the API:

```bash
uv run uvicorn de_assistant.api.main:app \
  --reload \
  --host 0.0.0.0 \
  --port 8000
```

---

## Health Check

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "ok"
}
```

---

## Ask a Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the difference between OLTP and OLAP?"}'
```

Example response:

```json
{
  "answer": "This is a mock response. The RAG pipeline successfully generated a prompt for the LLM.",
  "sources": [
    {
      "title": "Data Modeling & dbt - Bài 1: Tư duy nền tảng từ raw data đến analytical model",
      "heading": "OLAP — Online Analytical Processing",
      "source": "knowledge/Data Modeling & dbt/01-foundation-raw-to-analytical-model.md",
      "score": 0.8594
    }
  ]
}
```

---

# API Documentation

When the server is running:

```text
http://localhost:8000/docs
```

FastAPI provides an interactive Swagger UI where you can test `/ask` directly.

OpenAPI JSON:

```text
http://localhost:8000/openapi.json
```

---

# Ollama

The project contains an `OllamaLLM` implementation, but Ollama is not required in Codespaces.

Check whether Ollama is installed:

```bash
ollama --version
```

If Ollama is available locally, configure:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
```

Then the RAG service can use a local model instead of `MockLLM`.

The LLM interface is intentionally separated from the RAG layer:

```text
RAGService
    │
    ▼
LLMClient
    │
    ├── MockLLM
    │
    └── OllamaLLM
```

This allows the application to develop and test without requiring a running LLM server.

---

# Testing

Run all tests:

```bash
uv run pytest
```

Current test suite:

```text
tests/
├── test_context.py
├── test_embeddings.py
├── test_ingestion.py
└── test_retriever.py
```

Run a specific test:

```bash
uv run pytest tests/test_retriever.py
```

---

# Development

Run Ruff:

```bash
uv run ruff check .
```

Format code:

```bash
uv run ruff format .
```

Run tests:

```bash
uv run pytest
```

Recommended development loop:

```text
Edit Markdown
      ↓
Rebuild index
      ↓
Test retrieval
      ↓
Test RAG
      ↓
Run FastAPI
      ↓
Test /ask
```

---

# Design Principles

## 1. Markdown is the source of truth

Knowledge should remain human-readable and Git-versioned.

```text
Markdown → Index
```

Not:

```text
Vector DB → Source of truth
```

The vector index should always be rebuildable.

---

## 2. Local-first

The project is designed to minimize dependence on paid APIs.

Target stack:

```text
Python
Qdrant
SQLite
Sentence Transformers
Ollama
FastAPI
Streamlit
Docker
```

---

## 3. Simple before complex

The initial system intentionally avoids unnecessary infrastructure.

Start with:

```text
Vector RAG
```

Then add:

```text
Hybrid Search
```

Then:

```text
Reranking
```

Then, if the use cases justify it:

```text
Knowledge Graph
```

---

## 4. Pluggable LLM

The RAG layer should not depend directly on a specific model provider.

```python
class LLMClient(Protocol):
    def generate(
        self,
        prompt: str,
        system: str | None = None,
    ) -> str:
        ...
```

This makes it possible to support:

* Mock LLM
* Ollama
* Other local models
* Future hosted providers

without changing the retrieval layer.

---

## 5. Reproducible indexing

The index should be deterministic and rebuildable:

```bash
uv run python scripts/build_index.py
```

This makes the knowledge system easier to debug and version.

---

# Roadmap

## Phase 1 — Foundation

* [x] Repository setup
* [x] Python + uv
* [x] Markdown loader
* [x] Markdown parser
* [x] Metadata extraction
* [x] Chunking
* [x] Embeddings
* [x] Qdrant
* [x] Semantic retrieval
* [x] Context builder
* [x] Prompt builder
* [x] RAG service
* [x] Mock LLM
* [x] FastAPI `/health`
* [x] FastAPI `/ask`

## Phase 2 — Retrieval

* [ ] SQLite FTS5
* [ ] Hybrid retrieval
* [ ] Score fusion
* [ ] Retrieval threshold
* [ ] Reranker
* [ ] Retrieval evaluation dataset

## Phase 3 — Local LLM

* [x] Ollama client
* [ ] LLM factory
* [ ] Configurable LLM provider
* [ ] Local model testing
* [ ] Streaming generation

## Phase 4 — Assistant

* [ ] Conversation history
* [ ] Better citations
* [ ] Ask mode
* [ ] Learn mode
* [ ] Compare mode
* [ ] Design mode
* [ ] Interview mode

## Phase 5 — UI

* [ ] Streamlit application
* [ ] Source viewer
* [ ] Retrieval debugging panel
* [ ] Conversation interface
* [ ] Knowledge explorer

## Phase 6 — MCP

* [ ] MCP server
* [ ] Knowledge search tool
* [ ] RAG tool
* [ ] Knowledge inspection tools

## Phase 7 — Knowledge Graph

Only if graph relationships provide measurable value:

```text
Entity extraction
      ↓
Relationships
      ↓
Graph storage
      ↓
Graph-aware retrieval
```

Potential entities:

```text
Technology
   │
   ├── uses
   ├── replaces
   ├── integrates_with
   ├── alternative_to
   └── commonly_used_with
```

---

# Example Use Cases

### Data Engineering Learning

```text
Explain slowly changing dimensions.
```

### Comparison

```text
Compare Star Schema and Data Vault.
```

### Architecture

```text
Design a CDC pipeline using Kafka and dbt.
```

### SQL

```text
Explain window functions with practical examples.
```

### Interview

```text
What questions should I expect about dimensional modeling?
```

---

# License

This project is currently intended as a personal learning and portfolio project.

```

One small correction from the earlier README direction: **don't claim hybrid search is already implemented**. Your current retriever is semantic/Qdrant-only; SQLite FTS5 should remain under the roadmap until we actually build it.