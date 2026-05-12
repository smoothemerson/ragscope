# Technology Stack

**Analysis Date:** 2026-05-11

## Languages

**Primary:**
- Python 3.13+ — all application source code under `src/`, all tests under `tests/`
  - `requires-python = ">=3.13.8"` declared in `pyproject.toml`
  - Docker image uses `python:3.14-slim` (`Dockerfile` line 1)

**Secondary:**
- YAML — Docker Compose (`docker-compose.yml`) and GitHub Actions (`.github/workflows/lint.yml`)

## Runtime

**Environment:**
- CPython 3.13 (development venv at `/workspace/.venv/lib/python3.13/`)
- Docker container (production) — `python:3.14-slim` base image

**Package Manager:**
- pip — used for installs (`pip install -r requirements.txt` in `Dockerfile`)
- Lockfile: `requirements.txt` (fully pinned versions); `pyproject.toml` is the canonical dependency declaration

## Frameworks

**Core Web Framework:**
- FastAPI `0.135.3` — HTTP API layer, route definitions, dependency injection
  - Entry point: `src/main.py`
  - Routes: `src/api/router.py`
  - Models/schemas: `src/models.py`

**ASGI Server:**
- Uvicorn `0.41.0` (with `[standard]` extras — includes uvloop and httptools)
  - Start command: `uvicorn src.main:app --host 0.0.0.0 --port 8000` (`Dockerfile` line 21)

**LLM Orchestration:**
- LangChain `1.2.15` — core abstractions (`PromptTemplate`, `RunnableSequence`)
- `langchain-community` `0.4.1` — `PyPDFLoader`, `TextLoader` for document loading (`src/services/ingest.py`)
- `langchain-chroma` `1.1.0` — Chroma vector store integration (`src/services/ingest.py`, `src/services/query.py`, `src/services/health.py`)
- `langchain-ollama` `1.0.1` — `ChatOllama` LLM client, `OllamaEmbeddings` (`src/services/query.py`, `src/services/ingest.py`, `src/services/health.py`)
- `langchain-text-splitters` `1.1.1` — `RecursiveCharacterTextSplitter` with `chunk_size=4000`, `chunk_overlap=20` (`src/services/ingest.py`)

**ML Experiment Tracking:**
- MLflow `3.10.1` — experiment tracking, autologging, GenAI evaluation with scorers
  - Setup: `src/tracking/setup.py`
  - Evaluation pipeline: `src/services/evaluate.py`
  - MLflow server image: `ghcr.io/mlflow/mlflow:latest` (`docker-compose.yml`)
  - Backend store: SQLite at `/mlflow/data/mlflow.db`
  - Artifact root: `/mlflow/artifacts`

**LLM Evaluation:**
- DeepEval `3.8.8`+ (installed: `4.0.0`) — `AnswerRelevancy`, `Hallucination` scorers
  - Integrated via `mlflow.genai.scorers.deepeval` (`src/services/evaluate.py`)
- LiteLLM `1.81.16`+ (installed: `1.83.14`) — LLM proxy/routing layer used by MLflow/DeepEval judge path

**Testing:**
- pytest — test runner configured in `pyproject.toml`
  - `testpaths = ["tests"]`, `pythonpath = ["."]`
  - Custom markers: `unit`, `integration`, `e2e`

**Linting / Formatting:**
- Ruff `0.15.6` — linting and formatting
  - CI enforcement via `.github/workflows/lint.yml`
  - No separate `ruff.toml` or `[tool.ruff]` section — uses Ruff defaults

## Key Dependencies

**Critical:**
- `fastapi==0.135.3` — entire HTTP layer
- `langchain-ollama==1.0.1` — chat completions and embeddings via Ollama
- `langchain-chroma==1.1.0` — vector store (retrieval backbone)
- `mlflow==3.10.1` — evaluation pipeline and experiment dashboard
- `pypdf==6.9.2` — PDF parsing (used by LangChain `PyPDFLoader`)
- `httpx==0.28.1` — async HTTP client for Ollama health checks and model pulls (`src/main.py`, `src/services/health.py`)
- `python-dotenv==1.2.1`+ — environment variable loading (`src/utils/env.py`)
- `pydantic` (transitive via FastAPI) — request/response model validation (`src/models.py`)
- `python-multipart==0.0.24` — multipart form parsing for file upload at `POST /ingest`

**Infrastructure:**
- `deepeval>=3.8.8` — RAG evaluation scorers (Answer Relevancy, Hallucination, Safety)
- `litellm>=1.81.16` — LLM routing used by the judge evaluation path

## Configuration

**Environment:**
- All config loaded via `python-dotenv` in `src/utils/env.py`
- `.env` file at repo root (must exist at runtime; `.env.example` documents structure)
- `API_KEY` is **required** and enforced at import time — startup raises `RuntimeError` if unset (`src/utils/env.py` lines 34-35)

**Key env vars (from `.env.example`):**

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.2` | Primary LLM for query answering |
| `OLLAMA_JUDGE_MODEL` | `mistral` | LLM-as-judge for evaluation |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server URL |
| `CHROMA_PERSIST_DIR` | `/tmp/chroma` | ChromaDB data directory |
| `CHROMA_COLLECTION_NAME` | `ragscope_collection` | ChromaDB collection name |
| `API_KEY` | _(none — required)_ | Shared secret for `X-API-Key` header |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` (10 MB) | Upload size guard |
| `MAX_TOP_K` | `20` | Max retrieval chunks |
| `MAX_CONTEXT_CHARS` | `20000` | Context window truncation limit |
| `COMPOSE_PROFILES` | `cpu` | Hardware profile: `cpu`, `gpu-nvidia`, `gpu-amd` |

**Build:**
- `Dockerfile` — single-stage, `python:3.14-slim`, installs from `requirements.txt`, copies `src/`
- `docker-compose.yml` — multi-service orchestration (API, Ollama CPU/AMD/NVIDIA, MLflow)
- `.devcontainer/` — VS Code Dev Container (Claude Code sandbox, Node-based image)

## Platform Requirements

**Development:**
- Python 3.13.8+ for local development
- Docker + Docker Compose for full stack (Ollama inference + MLflow tracking)
- ~10 GB disk space for Ollama model cache

**Production:**
- Docker container on Linux host
- GPU optional — compose profiles support CPU, AMD ROCm (`ollama/ollama:rocm`), NVIDIA CUDA
- Ports: `8000` (API), `5000` (MLflow UI), `11434` (Ollama — localhost-bound)
- Named Docker volumes: `ollama_data`, `chroma_data`

---

*Stack analysis: 2026-05-11*
