# Roadmap: RAG Service Test Suite

**Milestone:** v1.0 — Full pytest suite covering unit, integration, and e2e tests with CI enforcement
**Created:** 2026-04-13
**Status:** Planning

## Phases

- [x] **Phase 1: Test Infrastructure** - Configure pytest, install dependencies, scaffold test directory tree, enforce coverage gate (completed 2026-04-13)
- [ ] **Phase 2: Unit Tests — API Layer & Security** - Cover all HTTP endpoints and API key auth with mocked externals
- [ ] **Phase 3: Unit Tests — Ingest & Query Pipelines** - Cover chunking, storage, retrieval, context truncation, and singleton behavior
- [ ] **Phase 4: Unit Tests — MLflow / Evaluation** - Cover judge evaluation calls, scorer configuration, and lifespan startup
- [ ] **Phase 5: Docker Profile + Integration & E2E Tests** - Stand up isolated test services, run live pipeline tests, and exercise full round-trips
- [ ] **Phase 6: CI Pipeline** - Automate unit and integration+e2e test runs on GitHub Actions with model caching

---

## Phase Details

### Phase 1: Test Infrastructure
**Goal:** pytest is fully configured and the test directory skeleton exists so all subsequent test tiers can be collected without errors
**Depends on:** Nothing (first phase)
**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. `pytest --collect-only` exits 0 with no RuntimeError — the API_KEY env var is injected automatically by pytest-env
  2. All required test dependencies (pytest-cov, pytest-env, pytest-mock, pytest-timeout, respx) are resolvable via `pip install -e .[test]`
  3. `tests/conftest.py` and per-tier `unit/`, `integration/`, `e2e/` conftest files exist and are importable
  4. Running `pytest --cov` with no tests written yet reports 0% coverage and exits without configuration errors; the `fail_under=80` gate is active
**Plans:** 1/1 plans complete

### Phase 2: Unit Tests — API Layer & Security
**Goal:** Every HTTP endpoint and API key authentication path is verified in isolation with all external services mocked
**Depends on:** Phase 1
**Requirements:** API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, SEC-01, SEC-02, SEC-03
**Success Criteria** (what must be TRUE):
  1. `pytest -m unit tests/unit/` passes with all 11 API and security test cases green and no real network calls made
  2. POST /ingest correctly returns 200, 400 (bad extension), 400 (empty file), and 413 (oversized) depending on input
  3. POST /query returns 200 with mocked retrieval, 404 when collection count is 0, and validates top_k bounds via Pydantic
  4. GET /health reflects healthy status with all deps up and degraded status when ChromaDB or Ollama are unavailable
  5. Missing, wrong, and correct X-API-Key header produce 401, 401, and 200 respectively
**Plans:** TBD
**UI hint**: no

### Phase 3: Unit Tests — Ingest & Query Pipelines
**Goal:** Internal pipeline logic for chunking, temp-file cleanup, context truncation, top_k clamping, and LLM singleton is verified with mocks
**Depends on:** Phase 1
**Requirements:** INGT-01, INGT-02, INGT-03, INGT-04, INGT-05, QRY-01, QRY-02, QRY-03, QRY-04, QRY-05, QRY-06, QRY-07
**Success Criteria** (what must be TRUE):
  1. `pytest -m unit tests/unit/` passes all 12 ingest and query test cases green
  2. Chunking parameters (chunk_size=4000, chunk_overlap=20) and the chunk count reflected in IngestResponse are verified; the known delete=False temp-file bug is exposed by INGT-04
  3. Temp file cleanup is confirmed on both success and every error path (embedding failure, storage failure)
  4. Context truncation at MAX_CONTEXT_CHARS, top_k clamping at MAX_TOP_K, and conditional judge evaluation call are all asserted
  5. The `get_llm()` singleton returns the same instance across calls, and an autouse fixture resets `_llm` between tests so no cross-test contamination occurs
**Plans:** TBD

### Phase 4: Unit Tests — MLflow / Evaluation
**Goal:** The MLflow judge evaluation layer — call shape, scorer list, model string format, exception swallowing, and lifespan autolog — is fully covered
**Depends on:** Phase 1
**Requirements:** EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05
**Success Criteria** (what must be TRUE):
  1. `pytest -m unit tests/unit/` passes all 5 evaluation test cases green
  2. `mlflow.genai.evaluate()` is asserted to receive inputs/outputs/expectations in the correct shape and the scorers list contains exactly AnswerRelevancy, Hallucination, and Safety
  3. The judge model string is asserted to equal `"ollama:/{OLLAMA_JUDGE_MODEL}"` (no double-slash)
  4. An exception inside `evaluate()` is swallowed — the enclosing query endpoint still returns 200
  5. `mlflow_autolog()` is confirmed called during application lifespan startup
**Plans:** TBD

### Phase 5: Docker Profile + Integration & E2E Tests
**Goal:** A test Docker Compose profile runs ChromaDB and Ollama in isolation, enabling live integration tests against real services and full ingest-to-query round-trips
**Depends on:** Phase 1, Phase 2, Phase 3, Phase 4
**Requirements:** INTG-01, INTG-02, INTG-03, E2E-01, E2E-02, E2E-03
**Success Criteria** (what must be TRUE):
  1. `docker-compose -f docker-compose.test.yml up` starts ChromaDB on port 8001 and Ollama on port 11435 without conflicting with the dev environment
  2. `pytest -m integration` with services available stores real chunks in ChromaDB and retrieves results from a pre-seeded collection; tests are skipped cleanly when services are unavailable
  3. `pytest -m e2e` exercises the full ingest→query round-trip: a document is uploaded, queried, and a non-empty answer is returned from Ollama
  4. Auth flow assertions (missing key→401, wrong key→401, correct key→proceeds) pass against the live application
  5. Error path assertions (empty collection→404, bad extension→400, oversized file→413) pass against the live application
**Plans:** TBD

### Phase 6: CI Pipeline
**Goal:** GitHub Actions automates unit tests on every push and integration+e2e tests on PR merge, with Ollama model caching to avoid re-pulling large models
**Depends on:** Phase 5
**Requirements:** CI-01, CI-02
**Success Criteria** (what must be TRUE):
  1. A GitHub Actions workflow file exists with two jobs: unit tests run without Docker on every push; integration+e2e tests run with Docker Compose on PR merge to main
  2. The Ollama model cache step is keyed to the model name — CI logs show a cache hit on the second run, skipping the ~600MB tinyllama download
**Plans:** TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Test Infrastructure | 1/1 | Complete   | 2026-04-13 |
| 2. Unit Tests — API Layer & Security | 0/? | Not started | - |
| 3. Unit Tests — Ingest & Query Pipelines | 0/? | Not started | - |
| 4. Unit Tests — MLflow / Evaluation | 0/? | Not started | - |
| 5. Docker Profile + Integration & E2E Tests | 0/? | Not started | - |
| 6. CI Pipeline | 0/? | Not started | - |

---

## Coverage Validation

All v1 requirements mapped:

| Requirement | Phase |
|-------------|-------|
| INFRA-01 | Phase 1 |
| INFRA-02 | Phase 1 |
| INFRA-03 | Phase 1 |
| INFRA-04 | Phase 1 |
| API-01 | Phase 2 |
| API-02 | Phase 2 |
| API-03 | Phase 2 |
| API-04 | Phase 2 |
| API-05 | Phase 2 |
| API-06 | Phase 2 |
| API-07 | Phase 2 |
| API-08 | Phase 2 |
| SEC-01 | Phase 2 |
| SEC-02 | Phase 2 |
| SEC-03 | Phase 2 |
| INGT-01 | Phase 3 |
| INGT-02 | Phase 3 |
| INGT-03 | Phase 3 |
| INGT-04 | Phase 3 |
| INGT-05 | Phase 3 |
| QRY-01 | Phase 3 |
| QRY-02 | Phase 3 |
| QRY-03 | Phase 3 |
| QRY-04 | Phase 3 |
| QRY-05 | Phase 3 |
| QRY-06 | Phase 3 |
| QRY-07 | Phase 3 |
| EVAL-01 | Phase 4 |
| EVAL-02 | Phase 4 |
| EVAL-03 | Phase 4 |
| EVAL-04 | Phase 4 |
| EVAL-05 | Phase 4 |
| INTG-01 | Phase 5 |
| INTG-02 | Phase 5 |
| INTG-03 | Phase 5 |
| E2E-01 | Phase 5 |
| E2E-02 | Phase 5 |
| E2E-03 | Phase 5 |
| CI-01 | Phase 6 |
| CI-02 | Phase 6 |

**Total:** 40 requirements across 6 phases
