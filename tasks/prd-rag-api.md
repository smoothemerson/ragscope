# PRD: RAG API with MLflow Evaluation Dashboard

## Introduction

A portfolio-grade Q&A API that lets users upload PDF/text documents and ask questions about them using Retrieval-Augmented Generation (RAG). The project's differentiator is an integrated MLflow evaluation dashboard that tracks both operational metrics (latency, token count) and LLM-as-judge quality scores (faithfulness, relevance, answer correctness) for every query.

**Stack:** FastAPI · ChromaDB · LangChain · Ollama (local LLM) · MLflow · Docker Compose

This is a self-contained, fully offline system — no external API keys required. It is designed as a portfolio/demo project that showcases end-to-end MLflow observability on a RAG pipeline.

---

## Goals

- Build a working RAG pipeline: ingest documents at runtime, retrieve relevant chunks, generate answers with a local LLM (Ollama)
- Expose a clean REST API (FastAPI) with two core endpoints: `POST /ingest` and `POST /query`
- Log every query as an MLflow run with operational + quality metrics
- Ship a `docker-compose.yml` that boots the entire system (API, ChromaDB, Ollama, MLflow) with a single command
- Keep scope minimal and completable — no auth, no multi-tenancy, no custom frontend

---

## User Stories

### US-001: Project scaffold and Docker Compose setup
**Description:** As a developer, I want a working project structure and Docker Compose file so that all services start together with one command.

**Acceptance Criteria:**
- [x] Repository has the following structure:
  ```
  /app          # FastAPI application code
  /tasks        # PRD lives here
  docker-compose.yml
  Dockerfile
  requirements.txt
  README.md
  ```
- [x] `docker-compose.yml` defines four services: `api`, `chromadb`, `ollama`, `mlflow`
- [x] MLflow bind mounts: `./mlflow/data:/mlflow/data` and `./mlflow/artifacts:/mlflow/artifacts` are declared in `docker-compose.yml`
- [x] `./mlflow/data` and `./mlflow/artifacts` directories are created automatically (documented in README as created automatically by Docker on first startup)
- [ ] `docker compose up` starts all services without errors *(runtime verification required)*
- [ ] MLflow UI is accessible at `http://localhost:5000` *(runtime verification required)*
- [ ] FastAPI docs are accessible at `http://localhost:8000/docs` *(runtime verification required)*
- [x] ChromaDB is accessible internally at `http://chromadb:8001` (host port 8001 → internal port 8000; API connects to `chromadb:8000`)
- [x] Ollama is accessible internally at `http://ollama:11434`
- [x] On startup, the `api` service automatically pulls three Ollama models before accepting requests: `OLLAMA_MODEL` (default `llama3.2`), `OLLAMA_JUDGE_MODEL` (default `mistral`), and `OLLAMA_EMBED_MODEL` (default `nomic-embed-text`) by calling `ollama pull` via the Ollama HTTP API
- [x] The API does not start accepting requests until all three models are confirmed available (implemented via `asynccontextmanager` lifespan handler in `app/main.py`)

---

### US-002: Document ingestion endpoint
**Description:** As a developer integrating the API, I want to upload a PDF or plain-text file via `POST /ingest` so that its content is chunked, embedded, and stored in ChromaDB for retrieval.

**Acceptance Criteria:**
- [x] `POST /ingest` accepts `multipart/form-data` with a `file` field
- [x] Accepts `.pdf` and `.txt` file types; returns HTTP 400 with descriptive error for other types
- [x] PDF text is extracted using LangChain's `PyPDFLoader`; plain text is loaded with `TextLoader`
- [x] Text is split into chunks using LangChain's `RecursiveCharacterTextSplitter` (chunk size: 500 tokens, overlap: 50 tokens)
- [x] Each chunk is embedded using Ollama's embedding model (`nomic-embed-text`) and stored in ChromaDB collection named `documents`
- [x] Successful response returns HTTP 200 with JSON: `{"status": "ok", "chunks_stored": <int>, "filename": "<string>"}`
- [x] If ChromaDB is unreachable, returns HTTP 503 with error message
- [ ] Linting passes (`ruff check`) *(runtime verification required)*

---

### US-003: Query endpoint with RAG pipeline
**Description:** As a developer, I want to send a question to `POST /query` and receive an answer grounded in the ingested documents so that the API demonstrates functional RAG.

**Acceptance Criteria:**
- [x] `POST /query` accepts JSON body: `{"question": "<string>", "top_k": <int, default 4>}`
- [x] Returns HTTP 422 if `question` is missing or empty (enforced via `Field(..., min_length=1)` in Pydantic model)
- [x] Retrieves the top-k most relevant chunks from ChromaDB using cosine similarity
- [x] Passes retrieved chunks + question to Ollama LLM (`llama3.2` or configurable via `OLLAMA_MODEL` env var) using a LangChain `RetrievalQA` chain
- [x] Response JSON: `{"answer": "<string>", "sources": ["<chunk text>", ...], "query_id": "<uuid>"}` — sources is a plain list of chunk text strings, no metadata or scores
- [x] If no documents have been ingested, returns HTTP 404 with message: `"No documents found. Please ingest documents first."`
- [x] End-to-end latency (from request received to response sent) is recorded for MLflow logging (US-004)
- [ ] Linting passes (`ruff check`) *(runtime verification required)*

---

### US-004: MLflow operational metrics logging
**Description:** As a developer reviewing system performance, I want every query to be logged as an MLflow run with operational metrics so that I can inspect latency and retrieval behavior in the MLflow UI.

**Acceptance Criteria:**
- [x] Each call to `POST /query` creates one MLflow run under experiment name `rag-evaluation`
- [x] The following are logged to MLflow for each run:
  - **Parameters:** `question`, `top_k`, `model_name`, `query_id`
  - **Metrics:** `latency_ms` (float), `num_chunks_retrieved` (int), `answer_length_chars` (int)
  - **Artifacts:** `answer.txt` containing the full answer text
- [x] MLflow run is created even if the LLM returns an error (log `error=true` as a tag)
- [x] MLflow experiment `rag-evaluation` is auto-created on first run if it does not exist
- [ ] Runs are visible in the MLflow UI at `http://localhost:5000` under the `rag-evaluation` experiment *(runtime verification required)*
- [ ] Linting passes (`ruff check`) *(runtime verification required)*

---

### US-005: LLM-as-judge quality evaluation
**Description:** As a developer, I want quality scores (faithfulness, answer relevance, context relevance) logged to MLflow so that I can evaluate RAG answer quality beyond operational metrics.

**Acceptance Criteria:**
- [x] After generating an answer, the system runs three LLM-as-judge evaluations using a **separate** Ollama model (configured via `OLLAMA_JUDGE_MODEL`, default: `mistral`):
  - **Faithfulness** (0.0–1.0): Is the answer supported by the retrieved context? Prompt asks the judge LLM to score how well the answer is grounded in the provided chunks.
  - **Answer Relevance** (0.0–1.0): Does the answer address the question? Prompt asks the judge LLM to score relevance of the answer to the question.
  - **Context Relevance** (0.0–1.0): Are the retrieved chunks relevant to the question? Prompt asks the judge LLM to score how relevant the retrieved context is.
- [x] The judge model (`OLLAMA_JUDGE_MODEL`) is invoked independently from the generation model (`OLLAMA_MODEL`) — they use separate `OllamaLLM` singleton instances (`_judge_llm` in `app/evaluate.py`, `_llm` in `app/query.py`)
- [x] Each score is parsed from the judge LLM's response as a float between 0.0 and 1.0
- [x] If parsing fails (malformed LLM output), the score is logged as `-1.0` and a warning tag is added to the MLflow run
- [x] All three scores are logged as MLflow metrics on the same run created in US-004: `faithfulness_score`, `answer_relevance_score`, `context_relevance_score`
- [x] Judge prompts are defined as constants in `app/prompts.py` (not hardcoded inline)
- [ ] Linting passes (`ruff check`) *(runtime verification required)*

---

### US-006: Health check and API documentation
**Description:** As a developer, I want a health check endpoint and auto-generated API docs so that I can verify the service is running and understand available endpoints.

**Acceptance Criteria:**
- [x] `GET /health` returns HTTP 200 with JSON: `{"status": "ok", "chromadb": "ok"|"error", "ollama": "ok"|"error"}`
- [x] Health check pings ChromaDB's `GET /api/v1/heartbeat` and Ollama's `GET /api/tags` to determine their status
- [x] FastAPI auto-generated docs at `http://localhost:8000/docs` show all endpoints with request/response schemas
- [x] All endpoints have summary strings and response model annotations
- [ ] Linting passes (`ruff check`) *(runtime verification required)*

---

### US-007: README and usage documentation
**Description:** As a portfolio reviewer, I want a clear README so that I can understand and run the project without prior knowledge of the codebase.

**Acceptance Criteria:**
- [x] README includes: project description, architecture diagram (ASCII), prerequisites, quickstart (`docker compose up`), example `curl` commands for `/ingest`, `/query`, and `/health`
- [x] README explains what the MLflow dashboard shows and how to access it
- [x] README documents all environment variables (`OLLAMA_MODEL`, `CHROMA_HOST`, `MLFLOW_TRACKING_URI`, etc.)
- [x] README includes a "How it works" section explaining the RAG pipeline steps

---

## Functional Requirements

- **FR-1:** `POST /ingest` must accept multipart file upload, extract text, chunk it, embed with Ollama, and store in ChromaDB
- **FR-2:** `POST /query` must embed the question, retrieve top-k chunks from ChromaDB, and generate an answer via an Ollama LLM using LangChain
- **FR-3:** Every query must produce exactly one MLflow run containing operational metrics (latency, chunk count, answer length) and quality scores (faithfulness, answer relevance, context relevance)
- **FR-4:** LLM-as-judge scoring must use a dedicated Ollama model (`OLLAMA_JUDGE_MODEL`, separate from `OLLAMA_MODEL`) with structured prompts that ask for a single float score
- **FR-5:** `GET /health` must check and report the status of ChromaDB and Ollama dependencies
- **FR-6:** `docker compose up` must start all four services (api, chromadb, ollama, mlflow) and make them accessible on their respective ports without manual setup
- **FR-7:** The Ollama model name must be configurable via the `OLLAMA_MODEL` environment variable (default: `llama3.2`)
- **FR-8:** All API responses must use consistent JSON schemas with documented FastAPI response models
- **FR-9:** The system must use ChromaDB's HTTP client (not in-memory) so that the vector store persists across API restarts
- **FR-10:** On startup, the `api` service must pull all three required Ollama models (`OLLAMA_MODEL`, `OLLAMA_JUDGE_MODEL`, `OLLAMA_EMBED_MODEL`) via the Ollama HTTP API (`POST /api/pull`) before the FastAPI application begins accepting requests
- **FR-11:** MLflow data and artifacts must be bind-mounted to `./mlflow/data` and `./mlflow/artifacts` on the host so the developer can inspect them directly

---

## Non-Goals

- No user authentication or API keys
- No multi-tenancy (all users share one ChromaDB collection)
- No document deletion or collection management endpoints
- No streaming responses from the LLM
- No custom frontend — MLflow's built-in UI is the only dashboard
- No cloud deployment (AWS, GCP, etc.) — Docker Compose on a single machine only
- No support for non-English documents
- No fine-tuning or model training of any kind
- No caching of query results

---

## Technical Considerations

### Service Ports (Docker Compose)
| Service   | Internal Port | Host Port |
|-----------|---------------|-----------|
| api       | 8000          | 8000      |
| chromadb  | 8000          | 8001      |
| ollama    | 11434         | 11434     |
| mlflow    | 5000          | 5000      |

### Key Environment Variables
| Variable              | Default                        | Description                             |
|-----------------------|--------------------------------|-----------------------------------------|
| `OLLAMA_MODEL`        | `llama3.2`                     | Ollama model for answer generation      |
| `OLLAMA_JUDGE_MODEL`  | `mistral`                      | Ollama model for LLM-as-judge scoring   |
| `OLLAMA_EMBED_MODEL`  | `nomic-embed-text`             | Ollama model for embeddings             |
| `CHROMA_HOST`         | `chromadb`                     | ChromaDB service hostname               |
| `CHROMA_PORT`         | `8000`                         | ChromaDB service port                   |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000`           | MLflow tracking server URI              |

### LangChain Components
- **Loader:** `PyPDFLoader` for PDF, `TextLoader` for `.txt`
- **Splitter:** `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)`
- **Embeddings:** `OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)`
- **Vector store:** `Chroma` with HTTP client pointing to ChromaDB container
- **LLM:** `OllamaLLM(model=OLLAMA_MODEL)`
- **Chain:** `RetrievalQA.from_chain_type`

### MLflow Backend
MLflow must be configured with a SQLite backend for persistent storage across restarts:
- `--backend-store-uri sqlite:////mlflow/data/mlflow.db`
- `--default-artifact-root /mlflow/artifacts`
- Both paths must be bind-mounted to host directories in `docker-compose.yml` (e.g., `./mlflow/data` and `./mlflow/artifacts`) so the developer can inspect the SQLite file and artifact files directly on their machine

### MLflow Run Structure
Each `/query` call produces one run:
- **Experiment:** `rag-evaluation`
- **Tags:** `query_id`, `generation_model`, `judge_model`
- **Params:** `question`, `top_k`
- **Metrics:** `latency_ms`, `num_chunks_retrieved`, `answer_length_chars`, `faithfulness_score`, `answer_relevance_score`, `context_relevance_score`
- **Artifacts:** `answer.txt`

### LLM-as-Judge Prompt Strategy
Each judge prompt must:
1. Provide the question, retrieved context, and generated answer
2. Ask the model to output ONLY a single float between 0.0 and 1.0
3. Include an example of the expected output format

Example faithfulness prompt structure:
```
You are evaluating an AI answer. Rate how well the answer is supported by the provided context.
Context: {context}
Question: {question}
Answer: {answer}
Output only a single number between 0.0 and 1.0. Example: 0.85
Score:
```

---

## Success Metrics

- `docker compose up` brings all four services online with zero manual steps
- `POST /ingest` successfully stores chunks for a 10-page PDF in under 30 seconds
- `POST /query` returns an answer in under 60 seconds on consumer hardware (M1/M2 Mac or modern Linux)
- Every query produces a visible MLflow run with all 6 metrics populated (no `-1.0` scores on valid queries)
- The project README is clear enough for a developer unfamiliar with the codebase to run it in under 10 minutes

---

## Open Questions

None — all questions resolved.
