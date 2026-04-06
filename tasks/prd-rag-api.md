# PRD: RAG API with MLflow Evaluation Dashboard

## Introduction

A portfolio-grade Q&A API that lets users upload PDF/text documents and ask questions about them using Retrieval-Augmented Generation (RAG). The project's differentiator is an integrated MLflow evaluation dashboard that tracks LLM-as-judge quality scores for each query.

**Stack:** FastAPI · Chroma (embedded) · LangChain · Ollama (local LLM) · MLflow · Docker Compose

This is a self-contained, fully offline system — no external API keys required. It is designed as a portfolio/demo project that showcases end-to-end MLflow observability on a RAG pipeline.

---

## Goals

- Build a working RAG pipeline: ingest documents at runtime, retrieve relevant chunks, generate answers with a local LLM (Ollama)
- Expose a clean REST API (FastAPI) with two core endpoints: `POST /ingest` and `POST /query`
- Log every query as an MLflow run with operational + quality metrics
- Ship a `docker-compose.yml` that boots the entire system (API, Ollama, MLflow) with a single command; Chroma runs embedded inside the API container
- Keep scope minimal and completable — no auth, no multi-tenancy, no custom frontend

---

## User Stories

### US-001: Project scaffold and Docker Compose setup
**Description:** As a developer, I want a working project structure and Docker Compose file so that all services start together with one command.

**Acceptance Criteria:**
- [x] Repository has the following structure:
  ```
  /src          # FastAPI application code
  /tasks        # PRD lives here
  docker-compose.yml
  Dockerfile
  requirements.txt
  README.md
  ```
- [x] `docker-compose.yml` defines core runtime services: `api` and `mlflow`, plus profile-based Ollama services and init pull jobs (Chroma is embedded in `api`)
- [x] MLflow bind mounts: `./mlflow/data:/mlflow/data` and `./mlflow/artifacts:/mlflow/artifacts` are declared in `docker-compose.yml`
- [x] `./mlflow/data` and `./mlflow/artifacts` directories are created automatically (documented in README as created automatically by Docker on first startup)
- [x] Chroma runs embedded inside the `api` container; vector data is persisted to a named Docker volume (`chroma_data`) via `CHROMA_PERSIST_DIR=/chroma/data`
- [x] Ollama is accessible internally at `http://ollama:11434`
- [x] On startup, Docker Compose runs an `ollama-pull-llama-*` init service that pulls three Ollama models before the API starts: `OLLAMA_MODEL` (default `llama3.2`), `OLLAMA_JUDGE_MODEL` (default `mistral`), and `OLLAMA_EMBED_MODEL` (default `nomic-embed-text`)
- [x] The API starts after the pull init service completes (configured with `depends_on` + `service_completed_successfully` in `docker-compose.yml`)

---

### US-002: Document ingestion endpoint
**Description:** As a developer integrating the API, I want to upload a PDF or plain-text file via `POST /ingest` so that its content is chunked, embedded, and stored in ChromaDB for retrieval.

**Acceptance Criteria:**
- [x] `POST /ingest` accepts `multipart/form-data` with a `file` field
- [x] Accepts `.pdf` and `.txt` file types; returns HTTP 400 with descriptive error for other types
- [x] PDF text is extracted using LangChain's `PyPDFLoader`; plain text is loaded with `TextLoader`
- [x] Text is split into chunks using LangChain's `RecursiveCharacterTextSplitter` (chunk_size=4 000, chunk_overlap=20, length_function=len, add_start_index=True)
- [x] Each chunk is embedded using Ollama's embedding model (`nomic-embed-text`) and stored in the embedded Chroma vector store
- [x] Successful response returns HTTP 200 with JSON: `{"status": "ok", "chunks_stored": <int>, "filename": "<string>"}`
- [x] If Chroma is inaccessible (e.g. corrupt persist dir), returns HTTP 500 with error message

---

### US-003: Query endpoint with RAG pipeline
**Description:** As a developer, I want to send a question to `POST /query` and receive an answer grounded in the ingested documents so that the API demonstrates functional RAG.

**Acceptance Criteria:**
- [x] `POST /query` accepts JSON body: `{"question": "<string>", "top_k": <int, default 4>}`
- [x] Returns HTTP 422 if `question` is missing or empty (enforced via `Field(..., min_length=1)` in Pydantic model)
- [x] Retrieves the top-k most relevant chunks from ChromaDB using cosine similarity
- [x] Passes retrieved chunks + question to Ollama LLM (`llama3.2` or configurable via `OLLAMA_MODEL` env var) using a LangChain `RunnableSequence` (`PromptTemplate | ChatOllama`)
- [x] Response JSON: `{"answer": "<string>", "sources": ["<chunk text>", ...]}` — sources is a plain list of chunk text strings, no metadata or scores
- [x] If no documents have been ingested, returns HTTP 404 with message: `"No documents found. Please ingest documents first."`
- [x] Query traces and evaluation results are visible in MLflow under experiment `ragscope`

---

### US-004: MLflow tracking and evaluation visibility
**Description:** As a developer reviewing system behavior, I want every query to be tracked in MLflow and quality-evaluated so I can inspect results in the MLflow UI.

**Acceptance Criteria:**
- [x] Startup config sets MLflow tracking URI and experiment name `ragscope`
- [x] Query execution is tracked via `mlflow.autolog()` and MLflow GenAI evaluation output
- [x] MLflow experiment `ragscope` is auto-created on first run if it does not exist

---

### US-005: LLM-as-judge quality evaluation
**Description:** As a developer, I want quality scores logged to MLflow so that I can evaluate RAG answer quality.

**Acceptance Criteria:**
- [x] After generating an answer, the system runs three MLflow GenAI scorers using a separate judge model (`OLLAMA_JUDGE_MODEL`, default `mistral`)
  - `AnswerRelevancy`
  - `Hallucination`
  - `Safety`
- [x] Evaluation is non-fatal: if judge evaluation fails, the API still returns the answer and logs a warning
- [x] Evaluation results are visible in MLflow under the `ragscope` experiment (GenAI section)

---

### US-006: Health check and API documentation
**Description:** As a developer, I want a health check endpoint and auto-generated API docs so that I can verify the service is running and understand available endpoints.

**Acceptance Criteria:**
- [x] `GET /health` returns HTTP 200 with JSON: `{"status": "ok", "chromadb": "ok"|"error", "ollama": "ok"|"error"}`
- [x] Health check verifies Chroma by instantiating the local collection (no HTTP call) and pings Ollama's `GET /api/tags` to determine their status
- [x] FastAPI auto-generated docs at `http://localhost:8000/docs` show all endpoints with request/response schemas
- [x] All endpoints have summary strings and response model annotations

---

### US-007: README and usage documentation
**Description:** As a portfolio reviewer, I want a clear README so that I can understand and run the project without prior knowledge of the codebase.

**Acceptance Criteria:**
- [x] README includes: project description, architecture diagram (ASCII), prerequisites, quickstart (`docker compose up`), example `curl` commands for `/ingest`, `/query`, and `/health`
- [x] README explains what the MLflow dashboard shows and how to access it
- [x] README documents all key environment variables (`OLLAMA_MODEL`, `OLLAMA_JUDGE_MODEL`, `OLLAMA_EMBED_MODEL`, `MLFLOW_TRACKING_URI`, `CHROMA_PERSIST_DIR`)
- [x] README includes a "How it works" section explaining the RAG pipeline steps

---

## Functional Requirements

- **FR-1:** `POST /ingest` must accept multipart file upload, extract text, chunk it, embed with Ollama, and store in ChromaDB
- **FR-2:** `POST /query` must embed the question, retrieve top-k chunks from Chroma, and generate an answer via `ChatOllama` using a LangChain `RunnableSequence`
- **FR-3:** Every query must be tracked in MLflow experiment `ragscope`, with GenAI evaluation results available for inspected runs
- **FR-4:** LLM-as-judge scoring must use a dedicated Ollama model (`OLLAMA_JUDGE_MODEL`, separate from `OLLAMA_MODEL`) via MLflow GenAI scorers
- **FR-5:** `GET /health` must check and report the status of ChromaDB and Ollama dependencies
- **FR-6:** `docker compose up` must start the API, MLflow, and the selected profile-specific Ollama service without manual setup; Chroma is embedded in the api container
- **FR-7:** The Ollama model name must be configurable via the `OLLAMA_MODEL` environment variable (default: `llama3.2`)
- **FR-8:** All API responses must use consistent JSON schemas with documented FastAPI response models
- **FR-9:** The system must use Chroma with `persist_directory` (mounted Docker volume) so that the vector store persists across API restarts
- **FR-10:** On startup, Docker Compose must run an init pull service that downloads required Ollama models (`OLLAMA_MODEL`, `OLLAMA_JUDGE_MODEL`, `OLLAMA_EMBED_MODEL`) before `api` starts
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
| ollama    | 11434         | 11434     |
| mlflow    | 5000          | 5000      |

### Key Environment Variables
| Variable              | Default                        | Description                                               |
|-----------------------|--------------------------------|-----------------------------------------------------------|
| `OLLAMA_MODEL`        | `llama3.2`                     | Ollama model for answer generation                        |
| `OLLAMA_JUDGE_MODEL`  | `mistral`                      | Ollama model for LLM-as-judge scoring                     |
| `OLLAMA_EMBED_MODEL`  | `nomic-embed-text`             | Ollama model for embeddings                               |
| `CHROMA_PERSIST_DIR`  | `/chroma/data`                 | Container path for embedded Chroma data (Docker volume)   |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000`           | MLflow tracking server URI                                |

### LangChain Components
- **Loader:** `PyPDFLoader.load_and_split()` for PDF, `TextLoader` for `.txt`
- **Splitter:** `RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=20, length_function=len, add_start_index=True)`
- **Embeddings:** `OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)`
- **Vector store:** `Chroma(persist_directory=CHROMA_PERSIST_DIR)` — embedded, no separate service
- **LLM:** `ChatOllama(model=OLLAMA_MODEL, temperature=0)`
- **Chain:** `RunnableSequence(PromptTemplate | ChatOllama)` — answer extracted via `.content`

### MLflow Backend
MLflow must be configured with a SQLite backend for persistent storage across restarts:
- `--backend-store-uri sqlite:////mlflow/data/mlflow.db`
- `--default-artifact-root /mlflow/artifacts`
- Both paths must be bind-mounted to host directories in `docker-compose.yml` (e.g., `./mlflow/data` and `./mlflow/artifacts`) so the developer can inspect the SQLite file and artifact files directly on their machine

### MLflow Run Structure
Each `/query` call is tracked in MLflow:
- **Experiment:** `ragscope`
- **Evaluation outputs:** `AnswerRelevancy`, `Hallucination`, `Safety` via MLflow GenAI evaluate API
- **Operational traces:** Captured through `mlflow.autolog()` integration

### LLM-as-Judge Scoring Strategy
Evaluation uses MLflow GenAI scorers with a dedicated judge model:
1. `AnswerRelevancy`
2. `Hallucination`
3. `Safety`

The evaluation call is non-blocking for API correctness: failures log warnings and do not prevent answer responses.

---

## Success Metrics

- `docker compose up` brings all three services online with zero manual steps
- `POST /ingest` successfully stores chunks for a 10-page PDF in under 30 seconds
- `POST /query` returns an answer in under 60 seconds on consumer hardware (M1/M2 Mac or modern Linux)
- Every query produces visible tracking + GenAI evaluation data in MLflow under experiment `ragscope`
- The project README is clear enough for a developer unfamiliar with the codebase to run it in under 10 minutes
