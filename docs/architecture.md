# Architecture

This system is a fully offline Retrieval-Augmented Generation (RAG) API. Documents are ingested, embedded, and stored locally. Questions are answered by retrieving relevant chunks and generating a response via a local language model. Every query is evaluated by a second LLM judge and logged to MLflow.

## Components

| Component | Port | Role |
|-----------|------|------|
| **FastAPI** | `8000` | HTTP API server; hosts the `/ingest`, `/query`, and `/health` endpoints; runs ChromaDB embedded in the same process |
| **Ollama** | `11434` | Local LLM inference engine; serves all three models (generation, embedding, evaluation) |
| **MLflow** | `5000` | Experiment tracking server; records every query as a run with quality scores |

All components run as Docker Compose services. ChromaDB is embedded inside the FastAPI container — there is no separate ChromaDB service.

## Startup Sequence

During startup, the FastAPI app warms up required models before serving requests:

1. `OLLAMA_MODEL` — used for answer generation (default: `llama3.2`)
2. `OLLAMA_JUDGE_MODEL` — used for LLM-as-judge evaluation (default: `mistral`)
3. `OLLAMA_EMBED_MODEL` — used for text embeddings (default: `nomic-embed-text`)

The lifespan startup flow calls Ollama `POST /api/pull` in sequence. On later startups, cached models in `ollama_data` are reused and startup is faster.

Watch the `api` logs. When FastAPI startup completes, the system is ready.

## Ingestion Pipeline

`POST /ingest` processes uploaded documents through the following steps:

```
File upload (multipart/form-data)
  ↓
File type validation
  → .pdf or .txt only
  → HTTP 400 for any other extension
  ↓
Text extraction
  → PDF: PyPDFLoader
  → TXT: TextLoader
  ↓
Chunking
  → RecursiveCharacterTextSplitter
  → chunk_size = 4,000 characters
  → chunk_overlap = 20 characters
  ↓
Embedding
  → OllamaEmbeddings with OLLAMA_EMBED_MODEL
  ↓
Storage
  → ChromaDB collection: ragscope_collection
  → Persisted to chroma_data Docker volume
```

## Query Pipeline

`POST /query` processes questions through the following steps:

```
Incoming question (JSON)
  ↓
Embedding
  → OllamaEmbeddings with OLLAMA_EMBED_MODEL
  ↓
Vector search
  → Cosine similarity in ragscope_collection
  → Retrieves top_k chunks (default: 4)
  → HTTP 404 if collection is empty
  ↓
Context assembly
  → Retrieved chunks joined as plain text
  ↓
Answer generation
  → PromptTemplate | ChatOllama (OLLAMA_MODEL)
  → Temperature: 0 (deterministic)
  → Response language: always Brazilian Portuguese (pt-BR)
  ↓
LLM-as-judge evaluation (if sources were found)
  → See Evaluation section below
  ↓
Response
  → { "answer": "...", "sources": ["chunk1", "chunk2", ...] }
```

## Evaluation

After each query where sources are found, the answer is evaluated by a second LLM acting as a judge:

- **Judge model**: `OLLAMA_JUDGE_MODEL` (default: `mistral`)
- **Scorers** (via MLflow GenAI + DeepEval):
  - `AnswerRelevancy` — does the answer address the question?
  - `Hallucination` — does the answer contain information not supported by the retrieved context?
  - `Safety` — is the answer free of harmful content?
- **Non-fatal**: if evaluation fails for any reason, the answer is still returned to the caller and a warning is logged
- **Results**: visible in the MLflow UI at `http://localhost:5000` under the `ragscope` experiment → GenAI section

## Data Persistence

ChromaDB stores all ingested data in the `chroma_data` Docker named volume. This data **persists across container restarts**. Each new ingest adds to the existing collection — documents are not replaced.

**To reset the vector store only** (keeps Ollama model cache):

```bash
docker compose down
docker volume rm $(docker compose config --volumes | grep chroma)
```

Or by full volume name (replace `<project>` with your Compose project name, typically the directory name):

```bash
docker volume rm <project>_chroma_data
```

**To reset everything** (ChromaDB + Ollama model cache — models will re-download on next startup):

```bash
docker compose down -v
```

## Project Structure

```
src/
├── main.py           # FastAPI app entry point; configures MLflow autolog, model warm-up, and API routes
├── ingest.py         # Document ingestion: file validation, chunking, embedding, ChromaDB storage
├── query.py          # Query handling: embedding, retrieval, LLM generation, evaluation trigger
├── evaluate.py       # LLM-as-judge evaluation using MLflow GenAI scorers
├── health.py         # Health check: verifies Ollama and ChromaDB connectivity
├── models.py         # Pydantic request/response models for all endpoints
├── tracking/
│   └── setup.py      # MLflow autolog configuration; sets experiment name to ragscope
└── utils/
    ├── env.py         # Environment variable loading with defaults
    └── log_manager.py # Shared logger instance
```
