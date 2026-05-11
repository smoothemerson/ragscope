<!-- refreshed: 2026-05-11 -->
# Architecture

**Analysis Date:** 2026-05-11

## System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI HTTP Layer                         │
│    `src/main.py` - FastAPI app with lifespan context manager    │
├──────────┬──────────────────────┬──────────────────┬────────────┤
│  POST    │      POST /query     │    GET /health   │ Auth       │
│/ingest   │  `src/api/router.py` │                  │ Middleware │
│          │                      │                  │            │
└────┬─────┴──────────┬───────────┴────────────┬─────┴────────────┘
     │                │                        │
     ▼                ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                         │
│         Services: ingest, query, evaluate, health               │
│   `src/services/ingest.py` | query.py | evaluate.py | health.py│
└─────────────────────────────────────────────────────────────────┘
     │                │                        │
     ▼                ▼                        ▼
┌──────────────┐  ┌──────────────┐  ┌────────────────────┐
│   Chroma     │  │  Ollama LLMs │  │  MLflow Tracking   │
│ (embedded)   │  │  (external)  │  │  (external)        │
│ Vector Store │  │  Services    │  │  Evaluation       │
└──────────────┘  └──────────────┘  └────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Main App** | FastAPI app initialization, lifespan management, Ollama model warm-up | `src/main.py` |
| **Router** | Endpoint definitions, dependency injection for auth | `src/api/router.py` |
| **Ingest Service** | Document upload validation, parsing (PDF/TXT), chunking, embedding, vector storage | `src/services/ingest.py` |
| **Query Service** | Question embedding, retrieval, LLM answer generation, MLflow logging | `src/services/query.py` |
| **Evaluate Service** | LLM-as-judge evaluation with quality scorers (relevance, hallucination, safety) | `src/services/evaluate.py` |
| **Health Service** | Dependency health checks (Chroma, Ollama) | `src/services/health.py` |
| **Security** | API key validation middleware | `src/security.py` |
| **Models** | Pydantic request/response schemas | `src/models.py` |
| **Utils** | Environment configuration, logging infrastructure | `src/utils/` |
| **Tracking** | MLflow initialization and autolog setup | `src/tracking/setup.py` |

## Pattern Overview

**Overall:** Layered Service Architecture with Async/Await Event Loop

**Key Characteristics:**
- **Async-first:** All handlers and services use `async def` with httpx for non-blocking I/O
- **Dependency injection:** FastAPI `Depends()` for auth, services instantiated per-request or on-demand
- **Schema-driven:** Pydantic models enforce request/response contracts
- **Error handling:** HTTPException for API errors, graceful degradation for external failures
- **Global singletons:** LLM instance cached at module level in `query.py`; MLflow config at module level in `tracking/setup.py`

## Layers

**API Layer:**
- Purpose: HTTP endpoint definitions and request/response serialization
- Location: `src/api/router.py`, `src/main.py`
- Contains: FastAPI route handlers, lifespan hooks, OpenAPI schema suppression
- Depends on: Models (schemas), Security (auth), Services (business logic)
- Used by: HTTP clients (curl, SDKs)

**Service Layer:**
- Purpose: Implement domain logic for document ingestion, query handling, evaluation
- Location: `src/services/`
- Contains: Async functions orchestrating LangChain, Ollama, and Chroma interactions
- Depends on: Models (schemas), Utils (env config, logging), External SDKs (LangChain, MLflow, httpx)
- Used by: API layer routes

**Infrastructure Layer:**
- Purpose: Configuration, logging, external service setup
- Location: `src/utils/env.py`, `src/utils/log_manager.py`, `src/tracking/setup.py`
- Contains: Environment variable parsing, custom logger wrapper, MLflow autolog initialization
- Depends on: Python stdlib, python-dotenv, MLflow
- Used by: All service/API layers

**Security Layer:**
- Purpose: Request authentication
- Location: `src/security.py`
- Contains: API key header validation
- Depends on: Utils (env config)
- Used by: API router via `Depends()`

**Data Models:**
- Purpose: Define request/response contract
- Location: `src/models.py`
- Contains: Pydantic BaseModel schemas (IngestResponse, QueryRequest, QueryResponse, HealthResponse)
- Depends on: Pydantic
- Used by: API and Service layers

## Data Flow

### Primary Request Path: POST /query

1. **Entry point** (`src/api/router.py:26`) — FastAPI route handler receives QueryRequest
2. **Authentication** (`src/security.py:6`) — `verify_api_key()` dependency injected; raises HTTPException(401) on mismatch
3. **Service dispatch** (`src/services/query.py:47`) — `handle_query()` async function called
4. **Vector retrieval** (`src/services/query.py:52-66`) — Initialize Chroma vectorstore, retrieve top-k chunks by embedding similarity
5. **LLM generation** (`src/services/query.py:68-80`) — Embed question, build prompt with retrieved context, invoke LangChain RunnableSequence (PromptTemplate | ChatOllama)
6. **Evaluation** (`src/services/query.py:82-87`) — Call MLflow GenAI `evaluate()` with quality scorers (AnswerRelevancy, Hallucination, Safety)
7. **Response** (`src/services/query.py:89`) — Return QueryResponse with answer and source chunks

**Error handling:** HTTPException(500) if query pipeline fails (catch-all in line 94); HTTPException(404) if no documents ingested; HTTPException raised from dependency injection caught and propagated.

### Secondary Path: POST /ingest

1. **Entry point** (`src/api/router.py:17`) — FastAPI route receives file upload, auth dependency injected
2. **Validation** (`src/services/ingest.py:27-65`) — Check file extension (.pdf or .txt), content type, file size (<10MB)
3. **Document loading** (`src/services/ingest.py:74-79`) — Parse with PyPDFLoader or TextLoader
4. **Chunking** (`src/services/ingest.py:81-87`) — Split with RecursiveCharacterTextSplitter (4000 chars, 20 overlap)
5. **Embedding & storage** (`src/services/ingest.py:67-89`) — Initialize Ollama embeddings, store chunks in Chroma vectorstore (persisted to CHROMA_PERSIST_DIR)
6. **Response** (`src/services/ingest.py:91-95`) — Return IngestResponse with chunk count

**Error handling:** HTTPException(400) for unsupported extension or content type; HTTPException(413) for file size exceeded; HTTPException(400) for empty file.

### Tertiary Path: GET /health

1. **Entry point** (`src/api/router.py:35`) — FastAPI route handler
2. **Ollama check** (`src/services/health.py:18-24`) — HTTP GET to `/api/tags` endpoint, marks "error" on timeout or non-200 status
3. **Chroma check** (`src/services/health.py:26-37`) — Attempt to initialize vectorstore and call `count()` on collection
4. **Response** (`src/services/health.py:39-43`) — Return HealthResponse with status, chromadb, ollama fields

**State Management:**
- **LLM instance:** Cached at module level (`_llm`) in `src/services/query.py:20-35`; initialized on first access via `get_llm()`, reused for subsequent requests to avoid re-initialization overhead
- **Vectorstore:** Instantiated fresh per-request in ingest and query services (no caching) to ensure consistency with persisted Chroma data
- **Configuration:** Loaded once at module import time from environment (`src/utils/env.py`); required vars checked at load time (raises RuntimeError if API_KEY empty)

## Key Abstractions

**Vectorstore (Chroma):**
- Purpose: Persist document embeddings and enable semantic retrieval
- Examples: `src/services/ingest.py:68`, `src/services/query.py:40`, `src/services/health.py:30`
- Pattern: LangChain-wrapped Chroma client initialized with embeddings function; supports async `.as_retriever()` for search

**LLM (ChatOllama):**
- Purpose: Generate answers given question + context
- Examples: `src/services/query.py:34`, `src/services/query.py:67`
- Pattern: Cached singleton at module level; wrapped in LangChain RunnableSequence with PromptTemplate for composable chains

**Document Loader:**
- Purpose: Extract text from uploaded files
- Examples: `src/services/ingest.py:75`, `src/services/ingest.py:78`
- Pattern: LangChain loaders (PyPDFLoader, TextLoader) called synchronously; no caching

**Text Splitter:**
- Purpose: Chunk documents into vectorizable segments
- Examples: `src/services/ingest.py:81`
- Pattern: RecursiveCharacterTextSplitter with configurable chunk_size and overlap; applied to loaded documents

**MLflow Evaluator:**
- Purpose: Score query outputs on quality dimensions
- Examples: `src/services/evaluate.py:16-20`
- Pattern: MLflow GenAI `evaluate()` with scorers (AnswerRelevancy, Hallucination, Safety) run asynchronously as background task (evaluation failure doesn't block response)

## Entry Points

**FastAPI Application:**
- Location: `src/main.py:54-64`
- Triggers: `uvicorn src.main:app --host 0.0.0.0 --port 8000` (via docker-compose)
- Responsibilities: Create FastAPI instance, attach router, initialize lifespan context manager

**Lifespan Hook:**
- Location: `src/main.py:35-51`
- Triggers: On app startup and shutdown
- Responsibilities: Configure MLflow, pull Ollama models before accepting requests; warning-level logging on model pull timeout

**API Routes:**
- POST `/ingest` — `src/api/router.py:12-18`
- POST `/query` — `src/api/router.py:21-27`
- GET `/health` — `src/api/router.py:30-36`

## Architectural Constraints

- **Threading:** Single-threaded async event loop (uvicorn default); no worker threads spawned. All I/O is non-blocking via httpx and LangChain async support.
- **Global state:** 
  - LLM singleton at `src/services/query.py:20` (_llm) — thread-safe under GIL + single event loop
  - MLflow tracking URI and experiment name set once at startup (`src/tracking/setup.py:9-10`)
  - Environment config loaded at module import time (`src/utils/env.py`)
- **Circular imports:** None detected; dependency graph is acyclic (API → Services → Utils → stdlib/external)
- **Vectorstore initialization:** Fresh Chroma client per-request (no connection pooling); relies on persistent volume for data durability
- **API key validation:** Must be provided as `X-API-Key` header; empty API_KEY at startup raises RuntimeError

## Anti-Patterns

### Global LLM Singleton Without Locking

**What happens:** `src/services/query.py:20-35` uses module-level `_llm = None` and lazy initialization in `get_llm()` with no synchronization primitive.

**Why it's wrong:** Under concurrent requests, multiple coroutines can simultaneously check `if _llm is None` and both initialize ChatOllama instances, wasting memory and creating race conditions on assignment.

**Do this instead:** Use `asyncio.Lock` to guard initialization:
```python
_llm_lock = asyncio.Lock()
_llm: ChatOllama | None = None

async def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        async with _llm_lock:
            if _llm is None:  # double-check after acquiring lock
                _llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    return _llm
```

### Fresh Vectorstore Per Request (No Connection Pooling)

**What happens:** Every ingest and query request instantiates a new Chroma client (`src/services/ingest.py:68`, `src/services/query.py:40`), establishing redundant connections.

**Why it's wrong:** Creates I/O overhead and doesn't scale to high concurrency; Chroma initialization involves embedding function setup and metadata loading.

**Do this instead:** Cache a shared vectorstore instance with connection pooling, similar to the LLM pattern:
```python
_vectorstore: Chroma | None = None

def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
        _vectorstore = Chroma(...)
    return _vectorstore
```

### Synchronous Document Loading in Async Context

**What happens:** `src/services/ingest.py:75-79` calls PyPDFLoader and TextLoader synchronously inside an async function, blocking the event loop.

**Why it's wrong:** I/O blocking prevents other requests from being processed during PDF parsing. For large documents, this causes noticeable latency spikes.

**Do this instead:** Use `asyncio.to_thread()` to offload blocking I/O:
```python
loader = PyPDFLoader(tmp_path)
pages = await asyncio.to_thread(loader.load_and_split)
```

## Error Handling

**Strategy:** Explicit exception raising with HTTPException for client errors; logging with graceful degradation for external service failures.

**Patterns:**
- **Validation errors:** HTTPException(400) for malformed input (invalid file type, empty file, oversized file)
- **Authorization:** HTTPException(401) for missing/invalid API key
- **Resource not found:** HTTPException(404) when no documents ingested before query
- **External service failure:** HTTPException(500) if Ollama unreachable or query pipeline fails; evaluation failures logged as warning but don't block response
- **Query pipeline errors:** Broad catch-all in `src/services/query.py:93-95` catches all exceptions not explicitly handled and returns 500

## Cross-Cutting Concerns

**Logging:** 
- Implementation: Custom logger wrapper (`src/utils/log_manager.py:30-73`) around stdlib logging
- Usage: `logger.info()`, `.warning()`, `.error()` calls in main.py (model pull), tracking/setup.py (MLflow setup), query.py (pipeline errors), evaluate.py (evaluation failures)
- Format: `%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s`

**Validation:** 
- Pydantic BaseModel for request schemas (`src/models.py`); FastAPI automatically validates and returns 422 on schema mismatch
- File upload validation in ingest service: extension, content-type, size checks before processing
- Query parameter validation: `top_k` field in QueryRequest enforces `ge=1, le=20`

**Authentication:** 
- API key header validation (`src/security.py:6-10`) injected as dependency on /ingest and /query routes
- /health endpoint has no auth requirement (by design, for service monitoring)

---

*Architecture analysis: 2026-05-11*
