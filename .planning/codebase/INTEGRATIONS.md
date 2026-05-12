# External Integrations

**Analysis Date:** 2026-05-11

## APIs & External Services

**Ollama LLM Inference:**
- Ollama — local open-source LLM inference engine for answer generation and embeddings
  - SDK/Client: `langchain-ollama==1.0.1` (`ChatOllama`, `OllamaEmbeddings`)
  - Config env var: `OLLAMA_BASE_URL` (default: `http://ollama:11434`)
  - Models:
    - `OLLAMA_MODEL` (default: `llama3.2`) — generative LLM used in `src/services/query.py`
    - `OLLAMA_JUDGE_MODEL` (default: `mistral`) — LLM-as-judge used in `src/services/evaluate.py`
    - `OLLAMA_EMBED_MODEL` (default: `nomic-embed-text`) — embeddings used in `src/services/ingest.py`, `src/services/query.py`, `src/services/health.py`
  - Docker images: `ollama/ollama:latest` (CPU/NVIDIA), `ollama/ollama:rocm` (AMD)
  - Docker services: `ollama-cpu`, `ollama-gpu-amd`, `ollama-gpu-nvidia` — one activated per `COMPOSE_PROFILES`
  - Health check: `GET {OLLAMA_BASE_URL}/api/tags` in `src/services/health.py`
  - Model warm-up: `POST {OLLAMA_BASE_URL}/api/pull` called at startup for all three models in `src/main.py`

**MLflow Experiment Tracking:**
- MLflow — open-source ML experiment tracking, GenAI evaluation, and artifact management
  - SDK/Client: `mlflow==3.10.1`
  - Config env var: `MLFLOW_TRACKING_URI` (default: `http://mlflow:5000`)
  - Experiment name: `ragscope` (created at startup in `src/tracking/setup.py`)
  - Autologging: `mlflow.autolog()` called on startup
  - GenAI evaluation: `mlflow.genai.evaluate()` invoked after every query in `src/services/evaluate.py`
  - Docker image: `ghcr.io/mlflow/mlflow:latest`
  - Backend store: SQLite at `/mlflow/data/mlflow.db` (inside mlflow container)
  - Artifact store: `/mlflow/artifacts` (bind-mounted at `./mlflow/artifacts` on host)
  - UI accessible: `http://localhost:5000`

## Data Storage

**Vector Database:**
- ChromaDB — embedded vector store for document chunk embeddings
  - Client: `langchain-chroma==1.1.0`
  - Persistence directory: `CHROMA_PERSIST_DIR` (default: `/tmp/chroma` locally; `/chroma/data` in Docker)
  - Collection: `CHROMA_COLLECTION_NAME` (default: `ragscope_collection`)
  - Used in:
    - `src/services/ingest.py` — stores document embeddings after chunking
    - `src/services/query.py` — retrieves top-k chunks for RAG context
    - `src/services/health.py` — health check calls `vectorstore._collection.count()`
  - Docker volume: `chroma_data` (named volume — persists across container restarts)
  - Chunk config: `chunk_size=4000`, `chunk_overlap=20` (`src/services/ingest.py`)

**File Storage:**
- Local filesystem only — no external blob/object storage
  - Uploaded files land in `tempfile.NamedTemporaryFile` during processing (`src/services/ingest.py`)
  - Temp files are not explicitly deleted after ingestion (minor cleanup concern)
  - No persistent file storage; only vector embeddings are retained

**Caching:**
- In-process LLM instance — `ChatOllama` is lazily instantiated and cached as module-level `_llm` in `src/services/query.py`
- No distributed cache (Redis, Memcached, etc.)

## Authentication & Identity

**API Authentication:**
- Custom shared-secret header auth
  - Implementation: `src/security.py` — `verify_api_key()` dependency checks `X-API-Key` request header against `API_KEY` env var
  - Scope: Protects `POST /ingest` and `POST /query`
  - Unprotected: `GET /health` (no auth dependency)
  - HTTP 401 returned on mismatch
  - `API_KEY` is required; startup raises `RuntimeError` if empty (`src/utils/env.py` lines 34-35)

**Auth Provider:**
- Custom only — no OAuth, JWT, SAML, or third-party identity provider

## Monitoring & Observability

**Experiment Tracking:**
- MLflow UI at `http://localhost:5000` — tracks all query runs with evaluation scores (answer relevancy, hallucination, safety)

**Error Tracking:**
- None — no external service (Sentry, Datadog, etc.)

**Logs:**
- Python standard `logging` module with a custom wrapper `CustomLogger` (`src/utils/log_manager.py`)
- Format: `%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s`
- Level: `INFO` (hardcoded in `src/utils/log_manager.py`)
- Output: stdout (captured by Docker daemon)
- `LOG_FORMAT` env var declared but not yet implemented beyond its declaration

**Distributed Tracing:**
- None — no Jaeger, OpenTelemetry, or similar

## CI/CD & Deployment

**CI Pipeline:**
- GitHub Actions — `.github/workflows/lint.yml`
  - Trigger: push and pull request to `main`
  - Runner: `ubuntu-latest`
  - Python version in CI: `3.11` (note: lower than `requires-python = ">=3.13.8"` in `pyproject.toml`)
  - Steps: checkout → setup Python → `pip install -r requirements.txt` → `ruff check .`

**Dependency Automation:**
- GitHub Dependabot — `.github/dependabot.yml`
  - Monitors: `pip`, `github-actions`, `docker`
  - Schedule: weekly

**Hosting:**
- Docker Compose — multi-container local/self-hosted deployment
  - API container: `ragscope-api` on port `8000`
  - MLflow container: `ragscope-mlflow` on port `5000`
  - Ollama container: `ollama` on port `11434` (localhost-bound)

**Deployment model:**
- No cloud platform integration detected (no AWS, GCP, Azure, Heroku, Fly.io configs)
- No Kubernetes manifests or Helm charts

## Environment Configuration

**Required env vars (startup will fail without these):**
- `API_KEY` — shared secret for `X-API-Key` header auth; enforced at module import time

**Optional env vars with defaults (from `.env.example`):**

| Variable | Default | Notes |
|---|---|---|
| `COMPOSE_PROFILES` | `cpu` | Hardware profile: `cpu`, `gpu-nvidia`, `gpu-amd` |
| `OLLAMA_MODEL` | `llama3.2` | Generative LLM |
| `OLLAMA_JUDGE_MODEL` | `mistral` | Evaluation judge LLM |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server URL |
| `CHROMA_PERSIST_DIR` | `/tmp/chroma` | ChromaDB persistence path |
| `CHROMA_COLLECTION_NAME` | `ragscope_collection` | ChromaDB collection |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` | 10 MB upload cap |
| `MAX_TOP_K` | `20` | Max retrieval results |
| `MAX_CONTEXT_CHARS` | `20000` | Context window truncation |

**Secrets location:**
- `.env` file at repository root (`.gitignore` should exclude it)
- `.env.example` at repository root — safe to commit, documents all vars
- Secrets injected into Docker containers via `environment:` blocks in `docker-compose.yml`

## Webhooks & Callbacks

**Incoming:**
- None — no webhook handler endpoints

**Outgoing:**
- None — no outgoing webhook or callback calls to external services

---

*Integration audit: 2026-05-11*
