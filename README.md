# RAG API with MLflow Evaluation Dashboard

A portfolio-grade Q&A API that lets you upload PDF/text documents and ask questions about them using Retrieval-Augmented Generation (RAG). Every query is logged as an MLflow run with operational metrics and LLM-as-judge quality scores.

**Fully offline — no external API keys required.**

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose                      │
│                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
│  │  FastAPI │───▶│ ChromaDB │    │    MLflow    │   │
│  │  :8000   │    │  :8001   │    │    :5000     │   │
│  └────┬─────┘    └──────────┘    └──────────────┘   │
│       │                                              │
│       ▼                                              │
│  ┌──────────┐                                        │
│  │  Ollama  │  (llama3.2 · mistral · nomic-embed)    │
│  │  :11434  │                                        │
│  └──────────┘                                        │
└─────────────────────────────────────────────────────┘
```

**RAG Pipeline:**
1. User uploads a document → `POST /ingest`
2. Text is extracted, chunked (500 tokens, 50 overlap), and embedded with `nomic-embed-text`
3. Embeddings are stored in ChromaDB
4. User asks a question → `POST /query`
5. Question is embedded and top-k chunks retrieved from ChromaDB
6. Retrieved chunks + question are passed to `llama3.2` via LangChain `RetrievalQA`
7. Answer is returned; metrics and quality scores are logged to MLflow

---

## Prerequisites

- Docker and Docker Compose installed
- ~10 GB free disk space (for Ollama models)

The `./mlflow/data` and `./mlflow/artifacts` directories are created automatically by Docker when the bind mounts are resolved on first startup.

---

## Quickstart

```bash
docker compose up
```

Wait for all three Ollama models to finish pulling (logged in `api` service output). Then:

- FastAPI docs: http://localhost:8000/docs
- MLflow UI: http://localhost:5000

---

## Example Usage

### Ingest a document

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@/path/to/your/document.pdf"
```

```json
{"status": "ok", "chunks_stored": 42, "filename": "document.pdf"}
```

### Query the RAG pipeline

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic of the document?", "top_k": 4}'
```

```json
{
  "answer": "The document covers...",
  "sources": ["chunk text 1", "chunk text 2"],
  "query_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Health check

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "chromadb": "ok", "ollama": "ok"}
```

---

## MLflow Dashboard

Every call to `POST /query` creates one MLflow run under the **rag-evaluation** experiment.

Access the dashboard at **http://localhost:5000** → select `rag-evaluation` experiment.

Each run logs:
- **Parameters:** `question`, `top_k`, `model_name`, `query_id`
- **Metrics:**
  - `latency_ms` — end-to-end query time
  - `num_chunks_retrieved` — number of chunks used for context
  - `answer_length_chars` — length of the generated answer
  - `faithfulness_score` — is the answer grounded in the context? (0–1)
  - `answer_relevance_score` — does the answer address the question? (0–1)
  - `context_relevance_score` — are the retrieved chunks relevant? (0–1)
- **Artifacts:** `answer.txt` — full answer text

Quality scores use a separate LLM judge (`mistral`) that evaluates each query independently.

---

## Environment Variables

| Variable              | Default               | Description                              |
|-----------------------|-----------------------|------------------------------------------|
| `OLLAMA_MODEL`        | `llama3.2`            | Ollama model for answer generation       |
| `OLLAMA_JUDGE_MODEL`  | `mistral`             | Ollama model for LLM-as-judge scoring    |
| `OLLAMA_EMBED_MODEL`  | `nomic-embed-text`    | Ollama model for embeddings              |
| `CHROMA_HOST`         | `chromadb`            | ChromaDB service hostname                |
| `CHROMA_PORT`         | `8000`                | ChromaDB service port                    |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000`  | MLflow tracking server URI               |

Override any variable by setting it before running `docker compose up`:

```bash
OLLAMA_MODEL=llama3.1 docker compose up
```

---

## How It Works

1. **Document Ingestion** (`POST /ingest`):
   - File uploaded as `multipart/form-data`
   - PDF → `PyPDFLoader`; TXT → `TextLoader`
   - Split with `RecursiveCharacterTextSplitter` (chunk_size=500, overlap=50)
   - Embedded with `nomic-embed-text` via Ollama
   - Stored in ChromaDB `documents` collection

2. **Query** (`POST /query`):
   - Question embedded with `nomic-embed-text`
   - Top-k chunks retrieved from ChromaDB by cosine similarity
   - LangChain `RetrievalQA` chain runs `llama3.2` with retrieved context
   - Answer returned with source chunks

3. **MLflow Logging**:
   - Operational metrics logged immediately after query
   - Judge LLM (`mistral`) scores faithfulness, answer relevance, context relevance
   - All metrics visible in MLflow UI

4. **Model Warm-up**:
   - On startup, the API pulls all three Ollama models via `POST /api/pull`
   - FastAPI does not accept requests until all models are confirmed available
