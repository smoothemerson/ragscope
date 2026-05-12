# Concerns

**Analysis Date:** 2026-05-11

---

## Security Concerns

**[HIGH] Timing-Attack Vulnerable API Key Comparison**
- Risk: `src/security.py:9` compares API keys with Python `==` operator, which leaks timing information about key length and prefix matches. An attacker with network access can brute-force the key.
- Files: `src/security.py` (line 9)
- Current mitigation: Key loaded from env var; empty key raises `RuntimeError` at startup.
- Recommendations:
  1. Replace `x_api_key != API_KEY` with `not hmac.compare_digest(x_api_key or "", API_KEY)` for constant-time comparison.
  2. Add rate limiting on failed auth attempts (e.g., `slowapi` or `fastapi-limiter`).
  3. Log failed auth attempts — currently silent.

**[HIGH] Prompt Injection — User Input Passed Directly to LLM**
- Risk: `src/services/query.py:79` passes `request.question` verbatim into the prompt. A user can inject instructions that override the system prompt, producing arbitrary LLM output.
- Files: `src/services/query.py` (lines 22-28, 79)
- Current mitigation: None.
- Recommendations:
  1. Add input sanitization before embedding question in prompt template.
  2. Consider prompt guards or content classifiers to detect injection attempts.
  3. Use system prompt separation (separate system/user roles in ChatOllama API).

**[HIGH] PDF Parsing in Main Process (No Sandboxing)**
- Risk: `src/services/ingest.py:75-76` runs `PyPDFLoader` on untrusted uploads in the main API process. A malicious PDF exploit could compromise the container.
- Files: `src/services/ingest.py` (lines 74-79)
- Current mitigation: File size limited to `MAX_UPLOAD_SIZE_BYTES` (default 10MB). No other sandboxing.
- Recommendations:
  1. Run document parsing in an isolated subprocess or worker process.
  2. Add explicit timeout for parsing (currently unbounded).
  3. Add magic-byte validation to confirm file content matches declared extension before loading.

**[MEDIUM] File Upload Validation Bypassable**
- Risk: `src/services/ingest.py:60-65` validates `Content-Type` header, which is client-controlled. A `.txt` file with malicious binary content will pass extension and content-type checks.
- Files: `src/services/ingest.py` (lines 19-23, 60-65)
- Current mitigation: Extension whitelist (`.pdf`, `.txt`); MIME type whitelist.
- Recommendations:
  1. Add magic-byte validation using `python-magic` to confirm actual file format.
  2. Sanitize `filename` to prevent directory traversal sequences in log output.

**[MEDIUM] MLflow Logs Full Document Chunks**
- Risk: `src/services/evaluate.py:22-27` logs full context chunks and answers to MLflow. If MLflow is compromised or exposed externally, all ingested document content is disclosed.
- Files: `src/services/evaluate.py` (lines 22-27)
- Current mitigation: MLflow binds to `127.0.0.1:5000` in `docker-compose.yml`.
- Recommendations:
  1. Hash or truncate context chunks before evaluation logging.
  2. Enforce MLflow authentication if ever exposed on a non-localhost interface.
  3. Document data retention policy for evaluation artifacts.

**[MEDIUM] No Rate Limiting**
- Risk: Authenticated requests are unlimited. A valid API key holder can trigger unlimited LLM inference and disk writes, causing denial of service.
- Files: `src/api/router.py` (all routes)
- Current mitigation: File size cap (`MAX_UPLOAD_SIZE_BYTES`).
- Recommendations:
  1. Add per-key rate limiting using `fastapi-limiter` or `slowapi`.
  2. Enforce `MAX_TOP_K` at the model level (already done in env.py).

---

## Technical Debt

**[HIGH] Temporary Files Never Deleted (Resource Leak)**
- Issue: `src/services/ingest.py:34-35` creates a `NamedTemporaryFile` with `delete=False` and never calls `unlink()` after processing.
- Files: `src/services/ingest.py` (lines 34-55)
- Impact: Each ingested document leaves a file in `/tmp`. Over time, `/tmp` fills and ingestion fails with disk-full errors.
- Fix approach: Wrap temp file lifetime in `try/finally`:
  ```python
  try:
      # ... process file ...
  finally:
      Path(tmp_path).unlink(missing_ok=True)
  ```

**[HIGH] Private LangChain API Used Directly**
- Issue: `vectorstore._collection.count()` is called in two places, accessing a private attribute on the Chroma LangChain wrapper.
- Files: `src/services/query.py:55`, `src/services/health.py:35`
- Impact: Breaks silently on any LangChain or ChromaDB internal refactor. No public API guarantee.
- Fix approach: Use public Chroma client APIs or wrap the count call in a utility function that handles the access centrally and can be swapped if internals change.

**[MEDIUM] LLM Singleton Without Concurrency Guard**
- Issue: `src/services/query.py:20-35` uses a module-level `_llm = None` initialized lazily with no lock.
- Files: `src/services/query.py` (lines 20-35)
- Impact: Under concurrent requests, multiple coroutines can simultaneously check `if _llm is None` and both create ChatOllama instances, wasting memory. The singleton also prevents per-request model swapping.
- Fix approach: Use `asyncio.Lock` with double-checked locking, or inject the LLM via FastAPI `Depends()` so lifecycle is explicit.

**[MEDIUM] Vectorstore Re-initialized Per Request**
- Issue: `_get_vectorstore()` in `src/services/query.py:38-44` and `src/services/health.py:26-34` create fresh Chroma and OllamaEmbeddings instances on every call.
- Files: `src/services/query.py` (lines 38-44), `src/services/health.py` (lines 26-34)
- Impact: Unnecessary I/O and memory allocation per request; Chroma reads from disk on each initialization.
- Fix approach: Cache vectorstore as a module-level singleton (same pattern as `_llm`) or inject via FastAPI lifespan state.

**[MEDIUM] Hard-Coded Prompt Template with Language Constraint**
- Issue: The RAG prompt at `src/services/query.py:22-28` hard-codes `"Always respond in Brazilian Portuguese (pt-br)"`. This is not configurable without a code change.
- Files: `src/services/query.py` (lines 22-28)
- Impact: Cannot change language or prompt behavior without redeployment. Blocks non-Portuguese use cases.
- Fix approach: Move `TEMPLATE` to an env var or config file; strip language directive or make it configurable.

**[MEDIUM] Catch-All Exception Silencing Without Logging**
- Issue: `except Exception:` blocks in health service swallow all errors with no log output.
- Files: `src/services/health.py` (lines 23, 36), `src/services/query.py` (line 56-57)
- Impact: Operators cannot distinguish "Chroma empty" from "Chroma permission error" or "Chroma disk full".
- Fix approach: Log the caught exception at `WARNING` level before setting status to `"error"`.

**[LOW] Synchronous Document Loading Blocks Async Event Loop**
- Issue: `PyPDFLoader.load_and_split()` and `TextLoader.load()` are synchronous calls inside `async def ingest_document()`.
- Files: `src/services/ingest.py` (lines 75-79)
- Impact: Blocks the uvicorn event loop during PDF parsing; concurrent requests queue during large uploads.
- Fix approach: Wrap in `await asyncio.to_thread(loader.load_and_split)`.

**[LOW] Context Truncation Cuts Mid-Sentence**
- Issue: `src/services/query.py:72-73` slices context at `MAX_CONTEXT_CHARS` character boundary, splitting words and sentences arbitrarily.
- Files: `src/services/query.py` (lines 72-73)
- Impact: LLM receives malformed context, reducing answer quality silently.
- Fix approach: Truncate at chunk boundaries (slice `sources` list to only include chunks that fit within budget).

**[LOW] pyproject.toml Unstaged Modification**
- Issue: `pyproject.toml` has an unstaged modification (pytest config added). The `tests/` directory is also untracked. These changes are not committed to `main`.
- Files: `pyproject.toml`, `tests/` directory
- Impact: CI runs against the committed state without the new pytest markers or test files. Tests cannot be collected by CI.
- Fix approach: Stage and commit `pyproject.toml` changes and the full `tests/` directory tree.

---

## Missing Infrastructure

**[HIGH] CI Does Not Run Tests**
- What is missing: `.github/workflows/lint.yml` runs only `ruff check`. No `pytest` step exists in CI.
- Files: `.github/workflows/lint.yml`
- Impact: All unit, integration, and e2e tests are never run automatically. Regressions are only caught manually.
- Fix approach: Add a `pytest` job to the lint workflow or create a separate `test.yml` workflow. Prerequisite: commit `tests/` and `pyproject.toml`.

**[HIGH] No docker-compose.test.yml for Integration/E2E Tests**
- What is missing: The ROADMAP (Phase 5) requires a `docker-compose.test.yml` that starts isolated ChromaDB and Ollama for integration tests. This file does not exist.
- Files: None (missing file)
- Impact: Integration and E2E tests cannot run against real services in CI or locally without conflicting with the development environment.
- Fix approach: Create `docker-compose.test.yml` with Ollama on port 11435 and ChromaDB on port 8001 (isolated profile).

**[HIGH] No Coverage Gate Enforced**
- What is missing: No `--cov-fail-under` flag is configured in `pyproject.toml` pytest settings. The ROADMAP stated an 80% gate should be active.
- Files: `pyproject.toml`
- Impact: Test coverage can fall to 0% without CI failing.
- Fix approach: Add `addopts = "--cov=src --cov-fail-under=80"` to `[tool.pytest.ini_options]` in `pyproject.toml`.

**[MEDIUM] No Unit Tests for `run_judge_evaluations()`**
- What is missing: No test file exercises `src/services/evaluate.py`. The ROADMAP phase 4 requirements (EVAL-01 through EVAL-05) are unimplemented.
- Files: `src/services/evaluate.py` — no corresponding test file in `tests/unit/`
- Impact: Evaluation scorer configuration, judge model string format, and exception swallowing are untested.
- Fix approach: Create `tests/unit/test_evaluate_service.py` with mocked `mlflow.genai.evaluate`.

**[MEDIUM] No Test for LLM Singleton Reset Between Tests**
- What is missing: `tests/unit/test_query_service.py` patches `_get_vectorstore` and `get_llm` but does not reset the `_llm` module global between tests.
- Files: `tests/unit/test_query_service.py`, `src/services/query.py` (line 20)
- Impact: Test order dependency; if a test initializes `_llm`, subsequent tests inherit stale singleton state.
- Fix approach: Add an autouse fixture that resets `src.services.query._llm = None` between tests.

**[MEDIUM] No MLflow Startup Test**
- What is missing: No test verifies that `mlflow_autolog()` is called during app lifespan startup (EVAL-05).
- Files: `src/tracking/setup.py`, `tests/` directory
- Impact: MLflow setup breakage (e.g., tracking URI typo) goes undetected until runtime.
- Fix approach: Add test that patches `mlflow.set_tracking_uri` and `mlflow.autolog`, then triggers the lifespan context.

**[LOW] No Load or Performance Tests**
- What is missing: No test validates query latency, throughput under concurrency, or memory growth during ingestion.
- Files: None
- Impact: Performance regressions are undetectable; no baseline for capacity planning.
- Fix approach: Add a `tests/perf/` directory with locust or pytest-benchmark scripts.

---

## Open Questions

**[HIGH] Planning State Is Lost**
- Context: The files `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, and `.planning/config.json` are staged as deleted in the working tree but not committed. The last committed state (from `89dc97c`) placed the project at "Phase 1 complete, Phase 2-6 not started."
- The `tests/` directory (untracked) contains what appears to be phases 2-4 completed work: unit tests for security, ingest service, query service, health service, and models; integration tests for all three API endpoints; and one e2e test.
- Unresolved: Is this test work the result of phases 2-4 being executed, and the planning files deleted intentionally to be re-created by GSD? Or were they deleted in error?
- Risk: Without `STATE.md` and `ROADMAP.md`, the GSD orchestrator cannot determine which phases are complete and which remain. Running `/gsd-plan-phase` will recreate planning artifacts from scratch.
- Action needed: Confirm whether phases 2-4 are complete before running `/gsd-plan-phase 5` (Docker + integration) or `/gsd-plan-phase 6` (CI pipeline).

**[MEDIUM] Python Version Mismatch Between Dockerfile and pyproject.toml**
- Context: `Dockerfile` builds on `python:3.14-slim` (unreleased as of 2026-05-11). `pyproject.toml` declares `requires-python = ">=3.13.8"`. CI uses `python-version: "3.11"`.
- Unresolved: Which Python version is the true target? 3.14 is pre-release and may not have stable wheels for all dependencies (especially `deepeval`, `langchain-community`).
- Risk: If `python:3.14-slim` image changes (new RC or release), builds may break silently.
- Action needed: Align Dockerfile, pyproject.toml, and CI to the same Python version (recommend `3.13.x`).

**[MEDIUM] MLflow UI Endpoint Conflicts with PRD Non-Goal**
- Context: `tasks/todo.md` line 9 lists "FastAPI docs are accessible at `http://localhost:8000/docs`" as unchecked, but `src/main.py:59-61` explicitly disables `docs_url=None`, `redoc_url=None`, and `openapi_url=None`.
- Unresolved: Is the intent to re-enable FastAPI docs, or was the TODO entry added in error? The PRD (US-006) says docs should be accessible, but the code actively suppresses them.
- Action needed: Decide whether to re-enable OpenAPI docs or remove the TODO item.

**[LOW] Runtime Verification Items Unchecked**
- Context: `tasks/todo.md` lists three unchecked items under "Runtime Verification (US-001)" and two under "MLflow Verification" that require running the full Docker stack.
- Unresolved: These cannot be verified in unit/integration tests. Have they been tested manually?
- Risk: If MLflow evaluation outputs are not visible in the UI, the core differentiator of the project (integrated evaluation dashboard) is broken.

---

## Risks

**[HIGH] Unstaged Test Suite and Config Not in Version Control**
- Risk: The entire test suite (`tests/`) and the pytest configuration additions to `pyproject.toml` are not committed to `main`. A force-push or branch switch would discard all test work.
- Files: `tests/` (untracked), `pyproject.toml` (modified)
- Impact: If work is lost, phases 2-4 must be redone. CI cannot enforce quality gates.
- Mitigation: Commit both immediately before any branch operations.

**[HIGH] MLflow Evaluation Blocks Query Response Latency**
- Risk: `run_judge_evaluations()` in `src/services/evaluate.py` runs synchronously in the query handler. With `mistral` (7B) as judge, evaluation adds 10-30s to every query response.
- Files: `src/services/query.py` (lines 83-87), `src/services/evaluate.py`
- Impact: Users experience 2x-3x longer latency. On slow hardware, queries time out.
- Mitigation path: Move `run_judge_evaluations()` to a FastAPI `BackgroundTasks` call so response returns before evaluation completes.

**[MEDIUM] Docker Compose Startup Can Hang Indefinitely**
- Risk: `pull_model()` in `src/main.py:17-32` uses `timeout=None` on the httpx stream. If Ollama is slow or the model pull stalls, the API never becomes available.
- Files: `src/main.py` (line 22), `docker-compose.yml` (depends_on conditions)
- Impact: `docker compose up` hangs until killed manually; no operator feedback.
- Mitigation path: Add a startup timeout (e.g., 300s) to the httpx stream; log progress during model pull.

**[MEDIUM] Single-Collection ChromaDB Shared by All Users**
- Risk: All ingested documents share one Chroma collection (`CHROMA_COLLECTION_NAME`). There is no document ownership, access control, or namespace isolation.
- Files: `src/services/ingest.py:68-72`, `src/services/query.py:40-44`
- Impact: Any authenticated user can query documents ingested by others; no way to partition content.
- Mitigation path: If multi-tenancy is needed, parameterize collection name per user/session; or document single-tenant-only constraint in README.

**[LOW] `actions/checkout@v6` and `actions/setup-python@v6` Do Not Exist**
- Risk: `.github/workflows/lint.yml` references `actions/checkout@v6` and `actions/setup-python@v6`. As of 2026-05-11, the latest stable versions are `@v4`. Referencing non-existent action versions causes CI to fail.
- Files: `.github/workflows/lint.yml` (lines 14, 16)
- Impact: CI lint workflow fails on every push and PR.
- Mitigation: Change to `actions/checkout@v4` and `actions/setup-python@v5` (latest stable).

**[LOW] MLflow Startup Raises on Failure (Blocks App Start)**
- Risk: `src/tracking/setup.py:13` re-raises the exception from `mlflow_autolog()` setup. If MLflow is unavailable at startup (e.g., service ordering in Compose), the API refuses to start.
- Files: `src/tracking/setup.py` (lines 12-14)
- Impact: Any transient MLflow unavailability prevents the API from booting.
- Mitigation path: Downgrade to `logger.warning()` and continue; MLflow autolog is non-critical for API correctness.

---

*Concerns audit: 2026-05-11*
