# Codebase Structure

**Analysis Date:** 2026-05-11

## Directory Layout

```
/workspace/
├── src/                          # All application source code
│   ├── main.py                   # FastAPI app, lifespan hooks, router mount
│   ├── models.py                 # Pydantic request/response schemas
│   ├── security.py               # API key verification (FastAPI Depends)
│   ├── api/
│   │   ├── __init__.py
│   │   └── router.py             # Route definitions: /ingest, /query, /health
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ingest.py             # Upload → validate → chunk → embed → store
│   │   ├── query.py              # Question → retrieve → generate → evaluate
│   │   ├── evaluate.py           # LLM-as-judge scoring via MLflow GenAI
│   │   └── health.py             # Ollama + Chroma connectivity probes
│   ├── tracking/
│   │   ├── __init__.py
│   │   └── setup.py              # MLflow autolog, tracking URI, experiment name
│   └── utils/
│       ├── __init__.py
│       ├── env.py                # Typed env var constants with defaults
│       └── log_manager.py        # CustomLogger wrapper, singleton logger
│
├── tests/                        # Test suite (three tiers)
│   ├── conftest.py               # Session fixtures: TestClient, auth_headers, make_upload_file
│   ├── unit/
│   │   ├── test_models.py        # Pydantic schema validation tests
│   │   ├── test_security.py      # verify_api_key unit tests
│   │   ├── test_ingest_service.py# ingest_document() unit tests (mocked loaders)
│   │   ├── test_query_service.py # handle_query() unit tests (mocked vectorstore/LLM)
│   │   └── test_health_service.py# check_health() unit tests
│   ├── integration/
│   │   ├── test_ingest_api.py    # POST /ingest HTTP integration tests
│   │   ├── test_query_api.py     # POST /query HTTP integration tests
│   │   └── test_health_api.py    # GET /health HTTP integration tests
│   └── e2e/
│       └── test_rag_flow.py      # Multi-step RAG user flow tests
│
├── docs/                         # Manual project documentation
│   ├── architecture.md           # System architecture narrative
│   ├── configuration.md          # Environment variable reference
│   └── api.md                    # API endpoint reference
│
├── tasks/                        # Product and task tracking
│   ├── prd-rag-api.md            # Product requirements document
│   └── todo.md                   # Task checklist
│
├── scripts/
│   └── ralph/                    # Ralph GSD agent workspace
│       ├── CLAUDE.md             # Ralph agent instructions
│       ├── ralph.sh              # Ralph agent shell script
│       └── progress.txt          # Agent progress log
│
├── .planning/                    # GSD planning artifacts (auto-managed)
│   └── codebase/
│       ├── ARCHITECTURE.md       # Architectural analysis (this project)
│       ├── STRUCTURE.md          # Directory structure analysis (this file)
│       ├── STACK.md              # Technology stack analysis
│       ├── INTEGRATIONS.md       # External integration analysis
│       ├── CONVENTIONS.md        # Coding conventions analysis
│       ├── TESTING.md            # Testing pattern analysis
│       └── CONCERNS.md           # Technical debt and concerns
│
├── .github/
│   └── workflows/
│       └── lint.yml              # Ruff lint on push/PR to main
│
├── .claude/
│   └── skills/
│       ├── prd/                  # PRD writing skill for Claude
│       └── ralph/                # Ralph refactoring agent skill
│
├── .devcontainer/
│   └── Dockerfile                # Dev container definition
│
├── .zed/                         # Zed editor settings
├── .deepeval/                    # DeepEval configuration cache
│
├── pyproject.toml                # Project metadata, dependencies, pytest config
├── requirements.txt              # Pinned pip dependencies (for Docker)
├── Dockerfile                    # Production container: python:3.14-slim, appuser
├── docker-compose.yml            # Multi-service orchestration (api, ollama, mlflow)
├── README.md                     # Project overview and quickstart
└── .gitignore                    # Excludes .env, __pycache__, volumes, etc.
```

## Directory Purposes

**`src/`:**
- Purpose: All application source code; nothing outside this directory is imported at runtime
- Contains: FastAPI app, route handlers, service logic, utilities, models, security, tracking
- Key files: `main.py` (entry point), `api/router.py` (endpoints), `services/` (domain logic), `utils/env.py` (config)

**`src/api/`:**
- Purpose: HTTP API layer — route definitions and auth wiring
- Contains: `APIRouter` with all three route handlers; `Depends(verify_api_key)` applied inline
- Key files: `router.py`

**`src/services/`:**
- Purpose: Business logic — one module per domain capability
- Contains: Document ingestion pipeline, RAG query pipeline, LLM-as-judge evaluation, dependency health checks
- Key files: `ingest.py`, `query.py`, `evaluate.py`, `health.py`

**`src/utils/`:**
- Purpose: Cross-cutting infrastructure shared by all layers
- Contains: Env var constants (loaded once at import), `CustomLogger` wrapper singleton
- Key files: `env.py`, `log_manager.py`

**`src/tracking/`:**
- Purpose: Observability and experiment tracking initialization
- Contains: One-time MLflow setup called from `lifespan` in `src/main.py`
- Key files: `setup.py`

**`tests/`:**
- Purpose: Three-tier test suite (unit, integration, e2e)
- Contains: `conftest.py` with shared fixtures; unit tests that mock external deps; integration tests that exercise HTTP endpoints via `TestClient`; e2e tests that simulate full user flows
- Key files: `conftest.py`, `unit/test_query_service.py`, `integration/test_ingest_api.py`

**`docs/`:**
- Purpose: Human-readable project documentation maintained by hand
- Contains: Architecture narrative (`architecture.md`), environment variable guide (`configuration.md`), API endpoint reference (`api.md`)
- Note: More detailed than `.planning/codebase/` — written for human developers, not AI agents

**`tasks/`:**
- Purpose: Product requirements and task tracking
- Contains: PRD (`prd-rag-api.md`), active TODO list (`todo.md`)

**`scripts/ralph/`:**
- Purpose: Workspace for the Ralph GSD refactoring agent
- Generated: Partially (progress.txt); `CLAUDE.md` and `ralph.sh` are manually maintained
- Committed: Yes

**`.planning/codebase/`:**
- Purpose: Auto-generated codebase analysis documents consumed by `/gsd-plan-phase` and `/gsd-execute-phase`
- Generated: Yes — by `/gsd-map-codebase` command
- Committed: Yes

## Key File Locations

**Entry Points:**
- `src/main.py` — FastAPI app instance, lifespan hooks, Ollama model warm-up, router mount
- `Dockerfile` — Container build; `CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- `docker-compose.yml` — Orchestrates api, ollama (cpu/gpu-amd/gpu-nvidia profiles), mlflow services

**Configuration:**
- `src/utils/env.py` — All runtime constants; loaded at import time; `API_KEY` absence raises `RuntimeError`
- `pyproject.toml` — Python version (`>=3.13.8`), dependency list, pytest settings
- `requirements.txt` — Pinned pip dependencies used in `Dockerfile`
- `.env` (not tracked) — Runtime secrets; loaded by `python-dotenv` in `src/utils/env.py`

**Core Logic:**
- `src/api/router.py` — The three API endpoints with auth wiring
- `src/services/ingest.py` — Full ingestion pipeline: validate → load → chunk → embed → store
- `src/services/query.py` — Full query pipeline: retrieve → generate → evaluate; module-level `_llm` singleton
- `src/services/evaluate.py` — MLflow GenAI `evaluate()` with DeepEval scorers
- `src/security.py` — `verify_api_key()` dependency function
- `src/models.py` — `IngestResponse`, `QueryRequest`, `QueryResponse`, `HealthResponse`

**Testing:**
- `tests/conftest.py` — Shared `client`, `auth_headers`, `make_upload_file` fixtures
- `tests/unit/` — Direct service function tests with `unittest.mock` patches
- `tests/integration/` — HTTP endpoint tests using `TestClient` with mocked service internals
- `tests/e2e/` — Full flow tests against the live `TestClient`

## Naming Conventions

**Files:**
- Service modules: lowercase, single domain word — `ingest.py`, `query.py`, `evaluate.py`, `health.py`
- Setup/config modules: `setup.py` (tracking), `env.py` (utils)
- Test files: `test_<domain>_<layer>.py` — e.g., `test_ingest_service.py`, `test_ingest_api.py`

**Directories:**
- `src/services/` — one file per domain capability
- `src/api/` — HTTP boundary; always imports from services, never the reverse
- `src/utils/` — pure infrastructure with no domain knowledge
- `tests/unit/`, `tests/integration/`, `tests/e2e/` — strict tier separation

**Functions:**
- Async service handlers: `verb_noun()` — `ingest_document()`, `handle_query()`, `check_health()`
- Sync helpers: `get_llm()`, `_get_vectorstore()` (private with leading underscore)
- FastAPI dependencies: `verify_api_key()` (imperative verb phrase)

**Classes:**
- Pydantic models: `PascalCase` matching HTTP concept — `QueryRequest`, `IngestResponse`
- Logger wrapper: `CustomLogger` in `src/utils/log_manager.py`

## Where to Add New Code

**New API endpoint (e.g., DELETE /document):**
1. Add route handler to `src/api/router.py` with `@router.delete(...)` and `Depends(verify_api_key)`
2. Add request/response schemas to `src/models.py` if needed
3. Create `src/services/delete.py` with an async handler function
4. Add unit tests in `tests/unit/test_delete_service.py`
5. Add integration tests in `tests/integration/test_delete_api.py`

**New service module:**
- Implementation: `src/services/<feature>.py` — export one or two top-level async functions
- Import in router: `from src.services.<feature> import <handler>`
- Logging: `from src.utils.log_manager import logger`
- Config: `from src.utils.env import <CONSTANT>`

**New environment variable:**
1. Add to `src/utils/env.py` using `os.getenv("VAR_NAME", default)` or `_get_int_env("VAR_NAME", default)`
2. Add validation if required (see `API_KEY` check at end of `src/utils/env.py`)
3. Import in consuming module: `from src.utils.env import VAR_NAME`
4. Add to `docker-compose.yml` environment section for the `api` service

**New utility:**
- Shared infrastructure: `src/utils/<name>.py`
- Tracking/observability: `src/tracking/<name>.py`

**New test:**
- Unit test (mocked, no HTTP): `tests/unit/test_<module>.py`, mark `@pytest.mark.unit`
- Integration test (HTTP via TestClient): `tests/integration/test_<endpoint>_api.py`, mark `@pytest.mark.integration`
- E2E test (multi-step flow): `tests/e2e/test_<flow>.py`, mark `@pytest.mark.e2e`

## Special Directories

**`.planning/`:**
- Purpose: GSD planning artifacts — codebase maps, phase research, roadmap, requirements
- Generated: Auto-created by `/gsd-map-codebase` and `/gsd-plan-phase`
- Committed: Yes (tracks project state for AI agents)

**`.github/workflows/`:**
- Purpose: GitHub Actions CI
- Contents: `lint.yml` — runs `ruff check .` on push and PR to `main`
- Committed: Yes

**`.claude/skills/`:**
- Purpose: Reusable GSD agent skill definitions
- Contents: `prd/` and `ralph/` skill directories with `SKILL.md` index files
- Committed: Yes

**`mlflow/data/` and `mlflow/artifacts/` (Docker volume mounts):**
- Purpose: MLflow backend SQLite DB and artifact storage
- Generated: Yes — created by docker-compose on first run
- Committed: No — excluded by `.gitignore`; lives only in Docker volumes

**`chroma_data/` (Docker named volume):**
- Purpose: Chroma vectorstore persistence across container restarts
- Generated: Yes — managed by docker-compose as named volume `chroma_data`
- Committed: No

---

*Structure analysis: 2026-05-11*
