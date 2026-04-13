# Requirements: RAG Service Test Suite

**Defined:** 2026-04-13
**Core Value:** Every critical code path — ingest, query, and evaluation — is tested and regressions are caught before they reach production.

## v1 Requirements

### Infrastructure

- [ ] **INFRA-01**: pytest is configured with asyncio_mode=auto, asyncio_default_fixture_loop_scope=function, testpaths, markers (unit/integration/e2e), and API_KEY injected via pytest-env so collection never raises RuntimeError
- [ ] **INFRA-02**: Test dependencies added to pyproject.toml: pytest-cov>=6.0, pytest-env>=1.1, pytest-mock>=3.14, pytest-timeout>=2.3, respx>=0.22
- [ ] **INFRA-03**: tests/ directory skeleton created with conftest.py at root and per-tier conftest.py in unit/, integration/, and e2e/
- [ ] **INFRA-04**: pytest-cov configured with fail_under=80, branch=true, concurrency=["thread","greenlet"], source=["src"] — coverage gate enforced in CI

### Unit Tests — API Layer

- [ ] **API-01**: POST /ingest happy path returns 200 with chunks_stored > 0 (mocked externals)
- [ ] **API-02**: POST /ingest rejects disallowed file extensions with 400
- [ ] **API-03**: POST /ingest rejects empty file with 400
- [ ] **API-04**: POST /ingest rejects files exceeding MAX_UPLOAD_SIZE_BYTES with 413
- [ ] **API-05**: POST /query returns 200 with mocked retrieval and LLM response
- [ ] **API-06**: POST /query returns 404 when ChromaDB collection is empty (mock._collection.count explicitly set to 0)
- [ ] **API-07**: POST /query validates top_k bounds (ge=1, le=20) via Pydantic
- [ ] **API-08**: GET /health returns {"status":"ok"} with all deps healthy; reflects degraded status when ChromaDB or Ollama are unavailable

### Unit Tests — Security

- [ ] **SEC-01**: Missing X-API-Key header returns 401
- [ ] **SEC-02**: Wrong X-API-Key value returns 401
- [ ] **SEC-03**: Correct X-API-Key returns 200

### Unit Tests — Ingest Pipeline

- [ ] **INGT-01**: Chunking uses correct chunk_size=4000 and chunk_overlap=20
- [ ] **INGT-02**: vector_store.add_documents() called exactly once with non-empty list
- [ ] **INGT-03**: IngestResponse.chunks_stored equals actual chunk count
- [ ] **INGT-04**: Temp file is cleaned up on successful ingest (exposes known delete=False bug)
- [ ] **INGT-05**: Temp file is cleaned up on every error path (embedding failure, storage failure)

### Unit Tests — Query Pipeline

- [ ] **QRY-01**: Empty collection (count=0) raises HTTP 404 before any LLM call
- [ ] **QRY-02**: Context is truncated at exactly MAX_CONTEXT_CHARS characters
- [ ] **QRY-03**: top_k is clamped to MAX_TOP_K regardless of request value
- [ ] **QRY-04**: run_judge_evaluations is called when sources are present; not called when sources are empty
- [ ] **QRY-05**: Unhandled exception in pipeline returns HTTP 500 with generic message (no stack trace leak)
- [ ] **QRY-06**: get_llm() returns the same instance on repeated calls (singleton behavior verified)
- [ ] **QRY-07**: _llm singleton is reset between tests via autouse fixture (prevents cross-test contamination)

### Unit Tests — MLflow / Evaluation

- [ ] **EVAL-01**: mlflow.genai.evaluate() called with correct inputs/outputs/expectations shape
- [ ] **EVAL-02**: Scorers list contains AnswerRelevancy, Hallucination, and Safety
- [ ] **EVAL-03**: Judge model string is formatted as "ollama:/{OLLAMA_JUDGE_MODEL}" (no double-slash)
- [ ] **EVAL-04**: Exception inside evaluate() is swallowed — query still returns 200
- [ ] **EVAL-05**: mlflow_autolog() is called during lifespan startup

### Integration Tests

- [ ] **INTG-01**: docker-compose.test.yml extends base compose with a test profile — ChromaDB on port 8001, Ollama on port 11435, separate from dev environment
- [ ] **INTG-02**: Real ingest pipeline stores chunks in a live ChromaDB instance (skip if services unavailable)
- [ ] **INTG-03**: Real query retrieval returns results from a pre-seeded ChromaDB collection (no LLM call — keeps integration tier fast)

### E2E Tests

- [ ] **E2E-01**: Full ingest→query round-trip: upload a document, query it, receive a non-empty answer from Ollama
- [ ] **E2E-02**: Auth flow: missing API key returns 401, wrong key returns 401, correct key proceeds
- [ ] **E2E-03**: Error paths: empty collection returns 404, invalid file extension returns 400, oversized file returns 413

### CI Pipeline

- [ ] **CI-01**: GitHub Actions workflow with two-job split: unit tests run without Docker on every push; integration+e2e run with Docker Compose on PR merge
- [ ] **CI-02**: Ollama model cache in CI keyed to model name (avoids re-pulling ~600MB tinyllama on every run)

## v2 Requirements

### Quality Improvements

- **V2-01**: Timing-safe API key comparison — replace `!=` with `hmac.compare_digest` (security fix, low effort, deferred to keep v1 focused on test infrastructure)
- **V2-02**: Replace private `_collection.count()` ChromaDB API with public `len(vectorstore.get()["ids"])` — reduces fragility across ChromaDB minor releases
- **V2-03**: Move `run_judge_evaluations` to `asyncio.to_thread` or FastAPI `BackgroundTasks` — fixes sync blocking of the async event loop

### Extended Coverage

- **V2-04**: Mutation testing with mutmut to verify tests actually catch bugs
- **V2-05**: Property-based tests with Hypothesis for chunking edge cases (empty docs, single-word docs, max-size docs)
- **V2-06**: Contract tests for LangChain/ChromaDB API surface to detect breaking changes on dependency upgrades

## Out of Scope

| Feature | Reason |
|---------|--------|
| Load / performance testing | Separate concern; not blocking regressions |
| Frontend / UI testing | No frontend exists |
| LLM output quality assertions | Non-deterministic; flaky by design |
| Snapshot tests | Brittle for LLM outputs |
| Metric threshold assertions in unit tests | Belongs in evaluation pipeline, not test suite |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |
| INFRA-04 | — | Pending |
| API-01 | — | Pending |
| API-02 | — | Pending |
| API-03 | — | Pending |
| API-04 | — | Pending |
| API-05 | — | Pending |
| API-06 | — | Pending |
| API-07 | — | Pending |
| API-08 | — | Pending |
| SEC-01 | — | Pending |
| SEC-02 | — | Pending |
| SEC-03 | — | Pending |
| INGT-01 | — | Pending |
| INGT-02 | — | Pending |
| INGT-03 | — | Pending |
| INGT-04 | — | Pending |
| INGT-05 | — | Pending |
| QRY-01 | — | Pending |
| QRY-02 | — | Pending |
| QRY-03 | — | Pending |
| QRY-04 | — | Pending |
| QRY-05 | — | Pending |
| QRY-06 | — | Pending |
| QRY-07 | — | Pending |
| EVAL-01 | — | Pending |
| EVAL-02 | — | Pending |
| EVAL-03 | — | Pending |
| EVAL-04 | — | Pending |
| EVAL-05 | — | Pending |
| INTG-01 | — | Pending |
| INTG-02 | — | Pending |
| INTG-03 | — | Pending |
| E2E-01 | — | Pending |
| E2E-02 | — | Pending |
| E2E-03 | — | Pending |
| CI-01 | — | Pending |
| CI-02 | — | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 40 ⚠️

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after initial definition*
