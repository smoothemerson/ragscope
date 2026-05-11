# Codebase Structure

**Analysis Date:** 2026-05-11

## Directory Layout

```
/workspace/
├── src/                         # Application source code
│   ├── __init__.py             # Package marker (auto-generated)
│   ├── main.py                 # FastAPI app initialization, lifespan
│   ├── models.py               # Pydantic request/response schemas
│   ├── security.py             # API key validation middleware
│   ├── api/                    # HTTP endpoint definitions
│   │   ├── __init__.py
│   │   └── router.py           # FastAPI router with route handlers
│   ├── services/               # Business logic: ingest, query, eval
│   │   ├── __init__.py
│   │   ├── ingest.py           # Document upload and embedding
│   │   ├── query.py            # Q&A pipeline and MLflow logging
│   │   ├── evaluate.py         # LLM-as-judge quality scoring
│   │   └── health.py           # Dependency health checks
│   ├── utils/                  # Infrastructure utilities
│   │   ├── __init__.py
│   │   ├── env.py              # Environment variable parsing
│   │   └── log_manager.py      # Custom logger setup
│   └── tracking/               # Observability and experiment tracking
│       ├── __init__.py
│       └── setup.py            # MLflow autolog initialization
│
├── .planning/                  # Planning artifacts (GSD documents)
│   ├── codebase/              # Auto-generated codebase analysis
│   │   ├── ARCHITECTURE.md    # System layers, data flow, abstractions
│   │   └── STRUCTURE.md       # This file
│   ├── phases/                # Phase-specific research and plans
│   ├── ROADMAP.md             # High-level feature roadmap
│   ├── REQUIREMENTS.md        # PRD and feature requirements
│   └── STATE.md               # Current project state snapshot
│
├── docs/                       # Manual documentation
│   ├── architecture.md         # Detailed architecture overview
│   ├── configuration.md        # Configuration guide
│   └── api.md                  # API endpoint reference
│
├── tasks/                      # Task definitions
│   ├── prd-rag-api.md         # Product requirements document
│   └── todo.md                 # Task checklist
│
├── scripts/                    # Utility scripts
│   └── ralph/                  # Ralph GSD agent workspace
│
├── .github/                    # GitHub workflows and config
│   ├── workflows/
│   │   └── lint.yml            # Linting CI pipeline
│   └── dependabot.yml          # Dependency update automation
│
├── .claude/                    # Claude GSD skills and configuration
│   └── skills/
│       ├── prd/               # PRD documentation skill
│       └── ralph/             # Ralph refactoring agent skill
│
├── .devcontainer/             # Dev container configuration
├── .zed/                      # Zed editor configuration
│
├── pyproject.toml             # Python project metadata and dependencies
├── requirements.txt           # Python dependency pinning
├── Dockerfile                 # Container image definition
├── docker-compose.yml         # Multi-container orchestration
├── README.md                  # Project overview and quickstart
└── .gitignore                 # Git exclude patterns
```

## Directory Purposes

**`src/`:**
- Purpose: All application code for the RAG API
- Contains: FastAPI app, route handlers, service logic, utilities, models, security, tracking
- Key files: `main.py` (entry point), `api/router.py` (endpoints), `services/` (domain logic)

**`src/api/`:**
- Purpose: HTTP API layer (endpoint definitions and request routing)
- Contains: FastAPI router with POST /ingest, POST /query, GET /health handlers
- Key files: `router.py` (all three routes)

**`src/services/`:**
- Purpose: Service layer (business logic for each domain)
- Contains: Document ingestion, query handling, evaluation, health checks
- Key files: `ingest.py` (upload & embed), `query.py` (Q&A pipeline), `evaluate.py` (quality scoring), `health.py` (dependency checks)

**`src/utils/`:**
- Purpose: Infrastructure and cross-cutting concerns
- Contains: Environment configuration, logging setup
- Key files: `env.py` (config vars), `log_manager.py` (logger factory)

**`src/tracking/`:**
- Purpose: Observability and experiment tracking
- Contains: MLflow initialization and autolog setup
- Key files: `setup.py` (MLflow configuration)

**`.planning/`:**
- Purpose: GSD (Guided Software Development) planning artifacts
- Contains: Codebase analysis (ARCHITECTURE.md, STRUCTURE.md), phase research, roadmap, requirements
- Key files: `codebase/` (auto-generated analysis), `ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md`

**`docs/`:**
- Purpose: Manual project documentation
- Contains: Architecture guides, configuration reference, API docs
- Key files: `architecture.md`, `configuration.md`, `api.md`

**`tasks/`:**
- Purpose: Task and product documentation
- Contains: PRD and TODO checklist
- Key files: `prd-rag-api.md` (product requirements), `todo.md` (task checklist)

**`scripts/`:**
- Purpose: Automation and development utilities
- Contains: GSD agent workspaces
- Key files: `ralph/` (refactoring agent)

## Key File Locations

**Entry Points:**
- `src/main.py`: FastAPI app instance, lifespan hooks, Ollama model warm-up
- `docker-compose.yml`: Service orchestration (api, ollama, mlflow)
- `Dockerfile`: Container image for FastAPI API

**Configuration:**
- `pyproject.toml`: Python project metadata, dependency list, Python version
- `requirements.txt`: Pinned Python dependency versions (for reproducibility)
- `.env` (not tracked): Runtime environment variables (API_KEY, model names, URLs)
- `.env.example`: Template for required environment variables
- `src/utils/env.py`: Environment variable parsing and defaults

**Core Logic:**
- `src/api/router.py`: API endpoint definitions (POST /ingest, POST /query, GET /health)
- `src/services/ingest.py`: Document upload, parsing, chunking, embedding, vectorstore persistence
- `src/services/query.py`: Question embedding, retrieval, LLM generation, MLflow logging
- `src/services/evaluate.py`: Quality scoring (relevance, hallucination, safety)
- `src/security.py`: API key authentication
- `src/models.py`: Pydantic schemas (IngestResponse, QueryRequest, QueryResponse, HealthResponse)

**Testing:**
- No test files currently in repository (testing infrastructure not yet implemented)

## Naming Conventions

**Files:**
- `*.py`: Python source files
- `main.py`: FastAPI application entry point
- `router.py`: API route definitions
- `setup.py`: Configuration/initialization modules
- `*.md`: Documentation (no specific prefix convention)

**Directories:**
- `src/`: Source code root
- `src/services/`: Service layer (business logic)
- `src/api/`: API/HTTP layer
- `src/utils/`: Utility modules
- `src/tracking/`: Observability modules
- `.planning/`: GSD planning artifacts (hidden directory)
- `.github/`: GitHub config (hidden directory)
- `.claude/`: Claude GSD config (hidden directory)

**Python Modules:**
- `ingest`, `query`, `evaluate`, `health`: Service module names (lowercase, single domain responsibility)
- `router`: API routing module
- `security`: Authentication/authorization module
- `models`: Data model definitions
- `env`: Environment configuration
- `log_manager`: Logging infrastructure

**Function/Class Names:**
- `ingest_document()`: Async service handler (ingest.py)
- `handle_query()`: Async service handler (query.py)
- `check_health()`: Async service handler (health.py)
- `run_judge_evaluations()`: Async evaluation runner (evaluate.py)
- `verify_api_key()`: Security dependency (security.py)
- `get_llm()`: LLM singleton getter (query.py)
- `CustomLogger`: Logger wrapper class (log_manager.py)

## Where to Add New Code

**New Feature (e.g., document deletion):**
- Primary code: `src/services/delete.py` (new module in services layer)
- API route: Add new endpoint to `src/api/router.py`
- Model: Add response schema to `src/models.py` (if needed)
- Example: POST `/delete/{doc_id}` → `delete_service.delete_document(doc_id)` → delete from Chroma vectorstore

**New Service Module:**
- Location: Create `src/services/[feature_name].py`
- Import: Add import in `src/api/router.py` and use as dependency
- Dependencies: Import from `src/models.py`, `src/utils/`, external SDKs
- Pattern: Define async functions matching signature expected by route handler; use logger from `src/utils/log_manager.py`

**New Utility Function:**
- Shared helpers (env parsing, logging): `src/utils/[module_name].py`
- Tracking/observability: `src/tracking/[module_name].py`
- Import: `from src.utils import [function]` in consuming modules

**New API Endpoint:**
- Location: Add `@router.[method]()` decorator and handler to `src/api/router.py`
- Schema: Define request/response models in `src/models.py`
- Auth: Add `_: None = Depends(verify_api_key)` to handler if protected
- Implementation: Call service function from `src/services/`

**New Environment Variable:**
- Definition: Add parsing in `src/utils/env.py` with `.getenv()` call and default
- Usage: Import constant in consuming modules (e.g., `from src.utils.env import MY_VAR`)
- Validation: If required, add check at module load time (see API_KEY example)

## Special Directories

**`.planning/`:**
- Purpose: GSD (Guided Software Development) planning artifacts
- Generated: Yes (auto-created by `/gsd-map-codebase` and `/gsd-plan-phase` commands)
- Committed: Yes (tracking state, roadmap, requirements; not secrets)
- Contents: ARCHITECTURE.md, STRUCTURE.md (codebase analysis), phase research documents, ROADMAP.md, REQUIREMENTS.md, STATE.md

**`.github/workflows/`:**
- Purpose: GitHub Actions CI/CD pipelines
- Generated: No (manually maintained)
- Committed: Yes
- Contents: `lint.yml` (code linting on push)

**`.claude/skills/`:**
- Purpose: Claude GSD agent skills (reusable task patterns)
- Generated: No (manually maintained)
- Committed: Yes
- Contents: `prd/SKILL.md`, `ralph/SKILL.md` (skill definitions and rules)

**`node_modules/` / Python virtual env:**
- Not present in this repo (Python dependencies installed via pip/requirements.txt, no Node.js)

**`mlflow/data/` and `mlflow/artifacts/` (Docker volumes):**
- Purpose: MLflow backend storage (experiment runs, metrics, artifacts)
- Generated: Yes (created by docker-compose on first run)
- Committed: No (listed in .gitignore, exists only in containers)

**`chroma_data/` (Docker volume):**
- Purpose: Chroma vectorstore persistence
- Generated: Yes (created by docker-compose, persisted by Chroma)
- Committed: No (listed in .gitignore, exists only in containers)

---

*Structure analysis: 2026-05-11*
