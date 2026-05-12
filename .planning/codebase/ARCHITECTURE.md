<!-- refreshed: 2026-05-11 -->
# Architecture

**Analysis Date:** 2026-05-11

## System Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│                     HTTP Clients / Users                         │
│          X-API-Key header required for /ingest, /query           │
└───────────────────────────────┬──────────────────────────────────┘
                                │  HTTP :8000
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│              FastAPI Application  (src/main.py)                  │
│   lifespan: MLflow autolog + Ollama model pre-pull               │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │              API Layer  (src/api/router.py)              │   │
│   │   POST /ingest   POST /query   GET /health               │   │
│   │   Depends(verify_api_key) on /ingest, /query             │   │
│   │                    (src/security.py)                     │   │
│   └──────────┬───────────────────┬──────────────────────────┘   │
│              │                   │                               │
│   ┌──────────▼──────┐  ┌─────────▼───────┐  ┌────────────────┐  │
│   │services/ingest  │  │ services/query  │  │services/health │  │
│   │(src/services/   │  │(src/services/   │  │(src/services/  │  │
│   │ ingest.py)      │  │ query.py)       │  │ health.py)     │  │
│   └──────────┬──────┘  └────┬────────────┘  └───────┬────────┘  │
│              │              │                        │           │
│              │       ┌──────▼────────┐               │           │
│              │       │services/      │               │           │
│              │       │evaluate.py    │               │           │
│              │       └──────┬────────┘               │           │
└──────────────┼──────────────┼────────────────────────┼───────────┘
               │              │                        │
       ┌───────▼───────┐   ┌──▼──────────┐    ┌───────▼───────┐
       │  ChromaDB     │   │   Ollama    │    │   MLflow      │
       │  (embedded,   │   │  :11434     │    │  :5000        │
       │  /chroma/data)│   │  3 models   │    │  (tracking)   │
       └───────────────┘   └─────────────┘    └───────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app | Application entry point; lifespan hooks; router registration | `src/main.py` |
| API router | HTTP route definitions; auth dependency injection | `src/api/router.py` |
| security | `X-API-Key` header verification as FastAPI dependency | `src/security.py` |
| Pydantic models | Request/response schema definitions and validation | `src/models.py` |
| ingest service | File validation, parsing, chunking, embedding, Chroma storage | `src/services/ingest.py` |
| query service | Vector retrieval, LLM prompt/invoke, answer assembly, evaluation trigger | `src/services/query.py` |
| evaluate service | LLM-as-judge scoring via MLflow GenAI + DeepEval scorers | `src/services/evaluate.py` |
| health service | Probe Ollama and Chroma connectivity; return status | `src/services/health.py` |
| tracking/setup | MLflow tracking URI, experiment name, autolog configuration | `src/tracking/setup.py` |
| env utils | Typed environment variable loading from `.env` with defaults | `src/utils/env.py` |
| log_manager | Shared `CustomLogger` wrapper around Python `logging` | `src/utils/log_manager.py` |

## Pattern Overview

**Overall:** Layered service architecture within a single FastAPI process

**Key Characteristics:**
- Three clear layers: API (routing + auth) → Services (business logic) → Infrastructure (Chroma, Ollama, MLflow)
- Services are plain async Python functions — no classes, no dependency injection framework beyond FastAPI `Depends`
- All configuration read from environment variables at module import time via `src/utils/env.py`
- ChromaDB is embedded in-process (no separate network service); Ollama and MLflow are external Docker services
- LLM instance cached as a module-level singleton (`_llm` in `src/services/query.py`)

## Layers

**API Layer:**
- Purpose: HTTP routing and request/response serialization; enforces authentication
- Location: `src/api/router.py`, `src/security.py`
- Contains: `APIRouter`, route handler functions, `Depends(verify_api_key)` guards
- Depends on: `src/models.py` (schemas), `src/security.py` (auth), `src/services/*` (handlers)
- Used by: `src/main.py` (mounts the router via `app.include_router`)

**Service Layer:**
- Purpose: Business logic — document processing, RAG pipeline, health checks, evaluation
- Location: `src/services/ingest.py`, `src/services/query.py`, `src/services/evaluate.py`, `src/services/health.py`
- Contains: Async handler functions called directly by router handlers; LangChain orchestration
- Depends on: `src/utils/env.py` (config), `src/models.py` (return types), LangChain libraries, `httpx`
- Used by: `src/api/router.py`

**Schema Layer:**
- Purpose: Pydantic models for all API request and response shapes
- Location: `src/models.py`
- Contains: `IngestResponse`, `QueryRequest`, `QueryResponse`, `HealthResponse`
- Depends on: Nothing internal
- Used by: Router handlers, service return values

**Cross-Cutting Utilities:**
- Purpose: Configuration and logging shared by all layers
- Location: `src/utils/env.py`, `src/utils/log_manager.py`
- Contains: Typed env var constants, `CustomLogger` wrapper
- Depends on: Nothing internal; `python-dotenv` for `.env` loading
- Used by: All service modules and `src/main.py`

**Tracking Layer:**
- Purpose: MLflow initialization at startup (autolog, experiment selection)
- Location: `src/tracking/setup.py`
- Contains: `mlflow_autolog()` called once during lifespan
- Depends on: `src/utils/env.py`, `mlflow`
- Used by: `src/main.py` (in `lifespan` context manager)

## Data Flow

### Ingestion Pipeline (POST /ingest)

1. Client uploads multipart file with `X-API-Key` header → `src/api/router.py:17`
2. `verify_api_key` dependency checks header against `API_KEY` env var → `src/security.py:6`
3. `ingest_document()` validates file extension (`.pdf`, `.txt` only) → `src/services/ingest.py:27`
4. File streamed into `tempfile.NamedTemporaryFile`; size checked against `MAX_UPLOAD_SIZE_BYTES` → `src/services/ingest.py:34`
5. Content-type validated against allowed MIME types per extension → `src/services/ingest.py:60`
6. File loaded: `PyPDFLoader` (PDF) or `TextLoader` (TXT) → `src/services/ingest.py:74`
7. `RecursiveCharacterTextSplitter` splits into chunks (size=4000, overlap=20) → `src/services/ingest.py:81`
8. `OllamaEmbeddings` embeds chunks via Ollama (`OLLAMA_EMBED_MODEL`) → `src/services/ingest.py:67`
9. `Chroma.add_documents()` stores embeddings to `CHROMA_PERSIST_DIR` → `src/services/ingest.py:89`
10. Returns `IngestResponse(status, chunks_stored, filename)` → `src/services/ingest.py:91`

### Query Pipeline (POST /query)

1. Client sends JSON `{question, top_k}` with `X-API-Key` header → `src/api/router.py:24`
2. Pydantic validates `QueryRequest` (question 1–5000 chars, top_k 1–20) → `src/models.py:10`
3. `handle_query()` initializes Chroma vectorstore; checks `_collection.count()` → `src/services/query.py:52`
4. HTTP 404 raised if collection is empty → `src/services/query.py:59`
5. `vectorstore.as_retriever(k=min(top_k, MAX_TOP_K)).invoke(question)` retrieves chunks → `src/services/query.py:66`
6. Context assembled by joining chunk `page_content` fields; truncated to `MAX_CONTEXT_CHARS` → `src/services/query.py:71`
7. `PromptTemplate | ChatOllama` LangChain sequence generates answer (temperature=0, pt-BR) → `src/services/query.py:75`
8. If sources found: `run_judge_evaluations()` fires as synchronous side-effect → `src/services/query.py:83`
9. Judge scores logged to MLflow via `mlflow.genai.evaluate()` → `src/services/evaluate.py:31`
10. Returns `QueryResponse(answer, sources)` → `src/services/query.py:89`

### Health Check (GET /health)

1. No authentication required → `src/api/router.py:30`
2. `check_health()` probes `GET {OLLAMA_BASE_URL}/api/tags` with 5s timeout → `src/services/health.py:18`
3. Probes Chroma by instantiating collection and calling `_collection.count()` → `src/services/health.py:27`
4. Returns `HealthResponse(status, chromadb, ollama)` with `"ok"` or `"error"` per dependency → `src/services/health.py:39`

### Application Startup (lifespan)

1. `mlflow_autolog()` sets tracking URI, experiment `ragscope`, enables autolog → `src/tracking/setup.py:7`
2. `pull_model()` streams `POST {OLLAMA_BASE_URL}/api/pull` for each of three models → `src/main.py:17`
3. Pull failures are caught and logged as warnings; startup continues → `src/main.py:47`

**State Management:**
- Module-level `_llm: ChatOllama | None` singleton in `src/services/query.py:20` — lazily initialized on first query, reused thereafter
- All other infrastructure (Chroma, Ollama client) instantiated fresh per-request
- No in-process session, user, or request state beyond the singleton LLM
- All env vars loaded once at module import time in `src/utils/env.py`; `API_KEY` absence raises `RuntimeError` immediately

## Key Abstractions

**Service functions:**
- Purpose: Each service module exports one or two top-level async functions — these are the sole interface between the API layer and business logic
- Examples: `ingest_document()` in `src/services/ingest.py`, `handle_query()` in `src/services/query.py`, `check_health()` in `src/services/health.py`
- Pattern: Called directly by router handlers; return Pydantic model instances

**LangChain `RunnableSequence`:**
- Purpose: Compose prompt template and LLM into a single invocable pipeline
- Examples: `prompt | llm` assembled and called at `src/services/query.py:78`
- Pattern: Synchronous `.invoke()` called inside async handler (blocks the event loop)

**FastAPI `Depends`:**
- Purpose: Declarative dependency injection for authentication
- Examples: `Depends(verify_api_key)` in `src/api/router.py:17, 24`
- Pattern: Guard function raises `HTTPException(401)` on failure; route handler parameter typed as `_: None`

**`CustomLogger`:**
- Purpose: Thin wrapper over Python stdlib `logging` with `stacklevel=3` to preserve correct call-site reporting through the wrapper layer
- Examples: `logger` singleton exported from `src/utils/log_manager.py:73`
- Pattern: All modules import `from src.utils.log_manager import logger` and call `.info()`, `.warning()`, `.error()`

## Entry Points

**API Server:**
- Location: `src/main.py`
- Triggers: `uvicorn src.main:app --host 0.0.0.0 --port 8000` (via `CMD` in `Dockerfile`)
- Responsibilities: Creates `FastAPI` app, registers lifespan hook (MLflow + model pull), mounts router

**Router:**
- Location: `src/api/router.py`
- Triggers: Imported by `src/main.py:6`; handles all three routes
- Responsibilities: Maps HTTP verbs/paths to service functions; applies auth dependency

## Architectural Constraints

- **Async model:** FastAPI runs async handlers; LangChain's `RunnableSequence.invoke()` in `src/services/query.py:79` is synchronous and blocks the event loop during LLM inference — no other requests are served during generation
- **Single worker:** The `Dockerfile` CMD does not set `--workers`; Uvicorn defaults to 1 worker, consistent with the module-level LLM singleton and embedded Chroma
- **Global state:** Module-level `_llm` singleton (`src/services/query.py:20`); all env vars in `src/utils/env.py` loaded at import time
- **Circular imports:** None detected; dependency graph is acyclic — API → Services → Utils → stdlib/external
- **Embedded Chroma:** ChromaDB runs inside the API process with filesystem persistence — not a network service; Chroma is re-instantiated per request without connection pooling
- **Private Chroma internals:** `vectorstore._collection.count()` accessed directly in `src/services/query.py:55` and `src/services/health.py:35`

## Anti-Patterns

### Blocking I/O inside async handlers

**What happens:** `RunnableSequence.invoke()` in `src/services/query.py:79` is synchronous and called directly inside `async def handle_query()` without `run_in_executor`
**Why it's wrong:** Blocks the Uvicorn event loop during LLM inference; no other requests can be served during generation
**Do this instead:** Use `await asyncio.get_event_loop().run_in_executor(None, sequence.invoke, {...})` or LangChain's `ainvoke` equivalent

### Private Chroma internals accessed directly

**What happens:** `vectorstore._collection.count()` is called in `src/services/query.py:55` and `src/services/health.py:35` using the private `_collection` attribute
**Why it's wrong:** Depends on Chroma's internal implementation; will silently break across Chroma version upgrades
**Do this instead:** Wrap the count call in a try/except that fails safe (partially done in `query.py`); use a public API if one becomes available

### No vectorstore connection pooling

**What happens:** `Chroma(...)` is instantiated fresh on every ingest and query request in `src/services/ingest.py:68` and `src/services/query.py:39`
**Why it's wrong:** Redundant initialization overhead on every request; inconsistent with the cached LLM pattern
**Do this instead:** Cache a shared vectorstore singleton alongside `_llm`, protected by the same lazy-init pattern

## Error Handling

**Strategy:** Raise `HTTPException` with typed status codes inside service functions; catch broad `Exception` at service boundaries and re-raise as HTTP 500

**Patterns:**
- File validation errors → `HTTPException(400)` in `src/services/ingest.py`
- File too large → `HTTPException(413)` in `src/services/ingest.py:48`
- Auth failure → `HTTPException(401)` in `src/security.py:8`
- Empty collection → `HTTPException(404)` in `src/services/query.py:61`
- Any unhandled exception in query pipeline → caught at `src/services/query.py:91`; logged; re-raised as HTTP 500
- Evaluation failures are non-fatal: caught and logged as warnings in `src/services/evaluate.py:33`
- Startup failures (model pull) are non-fatal: logged as warnings in `src/main.py:47`; startup continues

## Cross-Cutting Concerns

**Logging:** `CustomLogger` wrapper in `src/utils/log_manager.py`; singleton `logger` instance imported by `src/main.py`, `src/services/query.py`, `src/services/evaluate.py`, and `src/tracking/setup.py`; output to stdout; format: `YYYY-MM-DD HH:MM:SS | LEVEL | module:lineno | message`
**Validation:** Pydantic field constraints on `QueryRequest` (`min_length`, `max_length`, `ge`, `le`); manual extension/MIME/size checks in `src/services/ingest.py`; FastAPI returns HTTP 422 automatically on Pydantic schema mismatch
**Authentication:** Header-based static API key via `verify_api_key` FastAPI dependency in `src/security.py`; applied to `/ingest` and `/query`; `/health` is intentionally unauthenticated

---

*Architecture analysis: 2026-05-11*
