# Technology Stack

**Analysis Date:** 2026-05-11

## Languages

**Primary:**
- Python 3.13.8+ - Backend API and services; primary language for the entire application

**Secondary:**
- YAML - Docker Compose and environment configuration

## Runtime

**Environment:**
- Python 3.13 / 3.14 - Specified in `Dockerfile` and `pyproject.toml`

**Package Manager:**
- pip - Standard Python package manager
- Lockfile: Yes (`requirements.txt` and `pyproject.toml`)

## Frameworks

**Core:**
- FastAPI 0.135.3 - HTTP API framework; async request handling (`src/main.py`, `src/api/router.py`)
- Uvicorn[standard] 0.41.0 - ASGI web server; runs the FastAPI application

**LLM & RAG:**
- LangChain 1.2.15 - RAG orchestration and LLM interactions
- LangChain Community 0.4.1 - Document loaders (PyPDF, TextLoader) in `src/services/ingest.py`
- LangChain Chroma 1.1.0 - Vector store integration in `src/services/ingest.py`, `src/services/query.py`
- LangChain Ollama 1.0.1 - Ollama LLM and embedding models integration (`src/services/query.py`, `src/services/ingest.py`)
- LangChain Text Splitters 1.1.1+ - Document chunking for RAG pipeline

**Testing & Evaluation:**
- MLflow 3.10.1 - Experiment tracking, metrics logging, and LLM evaluation (`src/tracking/setup.py`, `src/services/evaluate.py`)
- DeepEval 3.8.8+ - LLM-as-judge quality scorers (`src/services/evaluate.py`); evaluates answer relevancy, hallucination, and safety

**Build/Dev:**
- Ruff 0.15.6 - Python linter and code formatter

## Key Dependencies

**Critical:**
- FastAPI + Uvicorn - Production-ready async web framework and server; serves all API endpoints at port 8000
- LangChain ecosystem - Provides unified interface for Ollama, Chroma embeddings, document loaders, and prompt templates
- Ollama client (via LangChain Ollama) - Communicates with local Ollama inference service running in Docker at `http://ollama:11434`
- Chroma (via LangChain Chroma) - Embedded vector store for document embeddings; persisted to Docker volume `chroma_data`

**Infrastructure:**
- httpx 0.28.1 - Async HTTP client; used for health checks (`src/services/health.py`) and Ollama model pulling (`src/main.py`)
- python-multipart 0.0.24 - Multipart form data parsing for file uploads in `POST /ingest`
- python-dotenv 1.2.1+ - Environment variable loading from `.env` files (`src/utils/env.py`)
- Pydantic (via FastAPI) - Request/response validation (`src/models.py`): `QueryRequest`, `QueryResponse`, `IngestResponse`, `HealthResponse`
- pypdf 6.9.2 - PDF parsing and extraction for document ingestion (`src/services/ingest.py`)
- LiteLLM 1.81.16+ - LLM routing and fallback (dependency, may be used by MLflow or LangChain)

## Configuration

**Environment:**
- `.env` file required at repository root (see `.env.example`)
- Environment variables loaded via `python-dotenv` in `src/utils/env.py`
- Critical vars: `API_KEY`, `OLLAMA_MODEL`, `OLLAMA_JUDGE_MODEL`, `OLLAMA_EMBED_MODEL`, `COMPOSE_PROFILES` (cpu|gpu-nvidia|gpu-amd)

**Build:**
- `pyproject.toml` - Project metadata and dependency declarations
- `requirements.txt` - Pinned dependency versions for reproducibility
- `Dockerfile` - Docker image build; Python 3.14-slim base, installs system deps and Python packages
- `docker-compose.yml` - Multi-container orchestration: FastAPI API, Ollama (3 hardware profiles), MLflow, Chroma (embedded)

## Platform Requirements

**Development:**
- Docker and Docker Compose required
- ~10 GB free disk space (for Ollama model cache)
- Python 3.13.8+ for local development (not required if using Docker)

**Production:**
- Docker containers run on Linux; FastAPI exposed on port 8000 within container network
- Ollama service requires at least one GPU for gpu-nvidia or gpu-amd profiles; CPU profile available for development
- MLflow tracking server runs in separate container; accessible on port 5000 internally and for local browsing
- Vector database (Chroma) embedded in API container; persisted to named Docker volume `chroma_data`

---

*Stack analysis: 2026-05-11*
