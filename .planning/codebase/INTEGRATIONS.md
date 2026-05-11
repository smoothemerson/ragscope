# External Integrations

**Analysis Date:** 2026-05-11

## APIs & External Services

**Ollama LLM Inference:**
- Ollama - Local open-source LLM inference engine for answer generation and embeddings
  - SDK/Client: `langchain-ollama` (via LangChain)
  - Config: `OLLAMA_BASE_URL` environment variable (default: `http://ollama:11434`)
  - Models configured:
    - `OLLAMA_MODEL` (default: `llama3.2`) - Main generative model for query answering (`src/services/query.py`)
    - `OLLAMA_JUDGE_MODEL` (default: `mistral`) - Judge model for LLM-as-judge evaluation (`src/services/evaluate.py`)
    - `OLLAMA_EMBED_MODEL` (default: `nomic-embed-text`) - Embedding model for document and query embeddings (`src/services/ingest.py`, `src/services/query.py`)
  - Docker service: `ollama-cpu`, `ollama-gpu-amd`, `ollama-gpu-nvidia` (one active per `COMPOSE_PROFILES`)
  - Health check endpoint: `GET /api/tags` at `OLLAMA_BASE_URL` (checked in `src/services/health.py`)

**MLflow Model & Experiment Tracking:**
- MLflow - Open-source ML experiment tracking and model registry
  - SDK/Client: `mlflow` package
  - Tracking URI: `MLFLOW_TRACKING_URI` environment variable (default: `http://mlflow:5000`)
  - Experiment: `ragscope` (created on startup in `src/tracking/setup.py`)
  - Usage: Autolog enabled via `mlflow.autolog()` in `src/tracking/setup.py`
  - GenAI evaluation: `mlflow.genai.evaluate()` called after each query in `src/services/evaluate.py`
  - Docker service: `mlflow` container running at port 5000
  - Metrics logged: Quality scores (answer relevancy, hallucination, safety) via GenAI scorers

## Data Storage

**Databases:**
- Chroma (Vector Database) - Embedded vector store for document chunk embeddings
  - Client: `langchain-chroma` (LangChain integration)
  - Persistence: Persists to `CHROMA_PERSIST_DIR` (default: `/chroma/data` in Docker; `/tmp/chroma` for local runs)
  - Collection: `CHROMA_COLLECTION_NAME` (default: `ragscope_collection`)
  - Used in:
    - `src/services/ingest.py` - Stores document embeddings after ingestion
    - `src/services/query.py` - Retrieves relevant chunks for RAG context
    - `src/services/health.py` - Health check verifies connectivity
  - Docker volume: `chroma_data` - Named volume persists embeddings across container restarts

**File Storage:**
- Local filesystem only - No external blob storage
  - Temporary file uploads stored in system temp during processing (cleaned up after ingestion)
  - No persistent file storage; only embeddings are stored in Chroma

**Caching:**
- In-memory LLM instance - Single `ChatOllama` instance cached in `src/services/query.py` (module-level `_llm` variable)
- Vector store connection reused across requests via `Chroma()` initialization

## Authentication & Identity

**API Authentication:**
- Custom header-based API key authentication
  - Implementation: `src/security.py` - Verifies `X-API-Key` header matches environment variable `API_KEY`
  - Scope: Protects `/ingest` and `/query` endpoints
  - Health endpoint (`/health`) is unauthenticated
  - Enforcement: FastAPI dependency `verify_api_key()` in route handlers

**Auth Provider:**
- Custom (no external provider)
  - No OAuth, JWT, or third-party auth; static API key set via environment variable

## Monitoring & Observability

**Error Tracking:**
- None detected - No external error tracking service (Sentry, LogRocket, etc.)
- Errors logged to console via standard Python logger

**Logs:**
- Console-based logging via Python logger (`src/utils/log_manager.py`)
- MLflow tracks operational metrics and evaluation results; accessible in MLflow UI at port 5000
- Log output from containers captured by Docker daemon

**Distributed Tracing:**
- None - No external tracing service (Jaeger, DataDog, etc.)

## CI/CD & Deployment

**Hosting:**
- Docker Compose - Multi-container deployment model
- Containers run locally or in compatible Docker environments
- API service exposed on port 8000; MLflow UI on port 5000

**CI Pipeline:**
- None detected - No GitHub Actions, GitLab CI, or other CI service configured
- Manual Docker Compose startup via `docker compose up`

## Environment Configuration

**Required env vars:**
- `API_KEY` - Static API key for endpoint protection; must not be empty
- `COMPOSE_PROFILES` - Hardware profile selection; must be exactly one of `cpu`, `gpu-nvidia`, `gpu-amd`
- `OLLAMA_MODEL` - Generative model name (default: `llama3.2`)
- `OLLAMA_JUDGE_MODEL` - Judge model for evaluation (default: `mistral`)
- `OLLAMA_EMBED_MODEL` - Embedding model (default: `nomic-embed-text`)
- `OLLAMA_BASE_URL` - Ollama service endpoint (default: `http://ollama:11434`)
- `MLFLOW_TRACKING_URI` - MLflow tracking server endpoint (default: `http://mlflow:5000`)
- `CHROMA_PERSIST_DIR` - Vector store data directory (default: `/chroma/data` in Docker)
- `CHROMA_COLLECTION_NAME` - Chroma collection name (default: `ragscope_collection`)
- `MAX_UPLOAD_SIZE_BYTES` - File upload size limit (default: 10485760 bytes = 10 MB)
- `MAX_TOP_K` - Maximum retrieval results limit (default: 20)
- `MAX_CONTEXT_CHARS` - Maximum context window for LLM (default: 20000 characters)

**Secrets location:**
- `.env` file in repository root (excluded from git via `.gitignore`)
- Example template: `.env.example` (safe to commit)
- Environment variables passed to Docker containers via `docker-compose.yml` service definitions

## Webhooks & Callbacks

**Incoming:**
- None - No webhook endpoints for external services

**Outgoing:**
- None - API does not call external webhooks or callbacks
- MLflow runs are created as side effects of query execution but no outgoing callbacks

---

*Integration audit: 2026-05-11*
