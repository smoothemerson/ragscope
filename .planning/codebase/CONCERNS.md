# Codebase Concerns

**Analysis Date:** 2026-05-11

## Tech Debt

**Module-level Global State (LLM Singleton):**
- Issue: `_llm` global variable in `src/services/query.py:20` creates mutable shared state initialized lazily on first request
- Files: `src/services/query.py` (line 20-35)
- Impact: 
  - Not thread-safe in production; concurrent requests may trigger duplicate initialization
  - Difficult to mock in testing (no existing test infrastructure)
  - Coupling between module initialization and request handling
  - Cannot easily swap models per-request without refactoring
- Fix approach: Migrate to dependency injection using FastAPI Depends() or create a singleton manager class with explicit lifecycle control

**Private LangChain API Access:**
- Issue: Code directly accesses private `_collection` attribute on Chroma vectorstore
- Files: `src/services/health.py:35`, `src/services/query.py:55`
- Impact: 
  - Breaks if LangChain/Chroma internals change
  - No guarantee this interface exists in future versions
  - LangChain may deprecate or move this API
- Fix approach: Use public Chroma API methods (e.g., `vectorstore.get()` or query methods) or create a wrapper utility function that handles private access centrally

**Temporary File Cleanup Missing:**
- Issue: `src/services/ingest.py:34-35` creates temporary files with `delete=False` but never explicitly deletes them
- Files: `src/services/ingest.py` (line 34-39)
- Impact: 
  - Disk space accumulation over time; stale temp files left in `/tmp`
  - On container restart, old temp files persist if volume is shared
  - May eventually exhaust `/tmp` space and cause ingestion failures
- Fix approach: Use `try/finally` to ensure `Path(tmp_path).unlink()` is called after document processing completes; or use context manager wrapper

**Hard-coded Prompt Template:**
- Issue: RAG prompt template is hard-coded as module-level constant in `src/services/query.py:22-28`
- Files: `src/services/query.py` (line 22-28)
- Impact: 
  - Cannot change prompts without redeploying application
  - No version control over prompt history
  - Prevents A/B testing different prompts
  - Forces language (pt-br) without runtime flexibility
- Fix approach: Move prompt to configuration file or environment variable; consider prompt templating library for versions

**Catch-All Exception Handling:**
- Issue: Multiple `except Exception:` blocks silently swallow errors without logging or context
- Files: `src/services/health.py:23`, `src/services/health.py:36`, `src/services/query.py:56`
- Impact: 
  - Errors are hidden from operators; system appears "healthy" when dependencies are down
  - Difficult to diagnose integration failures
  - Health check returns "ok" for Chroma even when vectorstore is inaccessible
  - Silent failures in collection count check (line 56) mask real issues
- Fix approach: Log exception details with logger.warning(f"...: {exc}"); return specific error status in HealthResponse; use typed exceptions

---

## Known Bugs

**Health Check Always Returns "ok" Status:**
- Symptoms: Health endpoint returns `{"status": "ok", "chromadb": "error", "ollama": "error"}` even when dependencies fail; client cannot distinguish between "some services down" and "all services up"
- Files: `src/services/health.py:39` (status field), `src/api/router.py:35`, `src/models.py:20-23`
- Trigger: Stop ollama or chroma containers and call `/health`; status remains "ok" regardless of component statuses
- Workaround: Clients must check `chromadb` and `ollama` fields individually; recommend returning HTTP 503 when any component is "error"
- Fix approach: Change HealthResponse.status to reflect overall health (e.g., "degraded" or return HTTP 503); use enum for component statuses

**Query Fails Silently on Empty Vectorstore:**
- Symptoms: `handle_query()` catches all exceptions on vectorstore creation (line 56) and masks real errors; collection_count defaults to 0 without clear indication why
- Files: `src/services/query.py:54-63`
- Trigger: If Chroma initialization fails (e.g., permissions, disk full), collection_count = 0 triggers 404 instead of revealing root cause
- Workaround: User must check health endpoint; error message doesn't indicate whether vectorstore is empty vs. inaccessible
- Fix approach: Log exception from line 56; distinguish between "collection doesn't exist" (first ingest) and "vectorstore is broken" (permissions/disk issue)

**Ingestion Does Not Return Filename on Error:**
- Symptoms: `ingest_document()` raises HTTPException before calling any logging; operator doesn't know which file failed
- Files: `src/services/ingest.py:29-32`, `src/services/ingest.py:47-51`
- Trigger: Upload oversized or invalid file; HTTPException is raised with no context about filename
- Workaround: None; user must infer from client-side error handling
- Fix approach: Log filename alongside error; include filename in HTTPException detail

---

## Security Considerations

**Weak API Key Validation:**
- Risk: API_KEY comparison is string equality (==) with no timing attack mitigation; if key is leaked, attacker has full access
- Files: `src/security.py:9`
- Current mitigation: Key is environment variable, not hard-coded; requires header presence
- Recommendations: 
  1. Use `hmac.compare_digest(x_api_key, API_KEY)` to prevent timing attacks
  2. Add rate limiting on auth failures (e.g., FastAPI SlowAPI middleware)
  3. Consider header rate limiting to prevent brute-force key guessing
  4. Log failed auth attempts (currently silent)

**File Upload Validation Incomplete:**
- Risk: Content-type check is bypassable; attacker can send arbitrary binary with .txt extension; no virus/malware scanning
- Files: `src/services/ingest.py:60-65`
- Current mitigation: MIME type whitelist enforced; file extension checked; max size enforced
- Recommendations:
  1. Add file magic bytes validation (check actual file content, not just extension)
  2. Implement virus scanning (e.g., ClamAV) before storing chunks
  3. Sanitize filenames to prevent directory traversal in logs
  4. Consider sandboxing PDF extraction (malicious PDFs can execute code)

**PDF Parsing No Isolation:**
- Risk: PyPDFLoader processes untrusted PDF files in main application process; malicious PDF exploit could compromise API
- Files: `src/services/ingest.py:75-76`
- Current mitigation: None; direct loading into memory
- Recommendations:
  1. Consider sandboxing PDF parsing in isolated process or container
  2. Set timeout for PDF parsing (current: unbounded)
  3. Monitor memory usage during ingestion (PDFs can be memory bombs)
  4. Validate PDF structure before processing

**API Metrics Leakage (MLflow Evaluation):**
- Risk: MLflow logs answers and context chunks; if MLflow is exposed or compromised, all document content is disclosed
- Files: `src/services/evaluate.py:22-27` (context logged), `src/services/query.py:83-87` (evaluation always runs if sources exist)
- Current mitigation: MLflow listens on localhost only in docker-compose
- Recommendations:
  1. Evaluate whether evaluation is necessary for all queries; consider sampling
  2. Hash or truncate context chunks before logging to MLflow
  3. Document MLflow data retention policy
  4. Ensure MLflow authentication is enabled if exposed externally

**Environment Variable Exposure in Logs:**
- Risk: Logger includes module name and line numbers; if logger output is captured by external system, environment config may be exposed
- Files: `src/utils/log_manager.py:18` (format includes file:line)
- Current mitigation: Log goes to stdout, not to external service (currently)
- Recommendations:
  1. If shipping logs externally, redact environment variables
  2. Never log API_KEY, MLFLOW_TRACKING_URI credentials
  3. Consider structured logging (JSON) with field-level redaction

---

## Performance Bottlenecks

**Vectorstore Re-initialization Per Request:**
- Problem: `_get_vectorstore()` in query.py and health checks create fresh Chroma/OllamaEmbeddings instances on every call
- Files: `src/services/query.py:38-44`, `src/services/health.py:26-34`
- Cause: No caching; Chroma constructor reads from disk; OllamaEmbeddings initializes HTTP client each time
- Impact: Each query makes 1-2 extra network roundtrips (Chroma initialization, Ollama health check); health check is very slow (up to 10s)
- Improvement path:
  1. Cache vectorstore instance (similar to `_llm`) with explicit lifecycle
  2. Use shared OllamaEmbeddings instance (currently recreated in every module)
  3. Reduce health check frequency; cache result for 30s

**Context Truncation (No Optimization):**
- Problem: `src/services/query.py:72-73` naively truncates context at MAX_CONTEXT_CHARS boundary; may cut off mid-sentence
- Files: `src/services/query.py:72-73`
- Cause: Simple string slicing without semantic awareness
- Impact: Truncated context may be incoherent, reducing answer quality; no warning to user
- Improvement path:
  1. Truncate at chunk boundaries, not character count
  2. Log how many chunks were included vs. attempted
  3. Consider returning only fully-formed chunks within budget

**MLflow Evaluation Always Blocks Query Response:**
- Problem: `run_judge_evaluations()` is called synchronously after query; if judge model is slow, user waits
- Files: `src/services/query.py:83-87`, `src/services/evaluate.py:9-33`
- Cause: Evaluation is part of request/response cycle
- Impact: Query latency = LLM generation + evaluation time (could be 10-30s extra)
- Improvement path:
  1. Move evaluation to background task (FastAPI BackgroundTasks)
  2. Return answer to user immediately, log evaluation asynchronously
  3. Add optional `?skip_eval=true` parameter to skip scoring

**Large Chunk Sizes Not Configurable Per Model:**
- Problem: Chunk size is hard-coded to 4000 characters regardless of embedding model
- Files: `src/services/ingest.py:81-86`
- Cause: No dynamic configuration based on embedding model context window
- Impact: May be inefficient for models with different optimal chunk sizes
- Improvement path: Make chunk_size environment variable; document recommended size per embedding model

---

## Fragile Areas

**Query Service Module Coupling:**
- Files: `src/services/query.py`
- Why fragile:
  1. Tight coupling between retrieval, LLM chaining, and evaluation logic
  2. Global `_llm` state makes testing impossible without refactoring
  3. Direct dependency on RunnableSequence; if LangChain API changes, entire flow breaks
  4. Multiple instances of vectorstore initialization (lines 52, 70) with no deduplication
- Safe modification:
  1. Extract RunnableSequence construction into separate function (testable in isolation)
  2. Extract vectorstore access into service class (injectable)
  3. Separate evaluation from query response path
- Test coverage: No unit tests; entire query path is integration-only

**Ingest Service File Handling:**
- Files: `src/services/ingest.py`
- Why fragile:
  1. Temporary file created but never cleaned up (resource leak)
  2. Content-type validation is weak (extension-only, no magic bytes)
  3. No rollback if embedding/storage fails (orphaned temp file + partial chunks)
  4. Hard-coded splitter configuration; no retry on transient embedding errors
- Safe modification:
  1. Wrap temp file in context manager with guaranteed cleanup
  2. Add magic bytes validation before loading
  3. Implement transaction-like semantics: validate file, then ingest atomically
  4. Add retry logic with exponential backoff for Ollama timeouts
- Test coverage: No tests; no mock Ollama endpoint

**MLflow Integration Missing Error Boundaries:**
- Files: `src/services/evaluate.py`, `src/tracking/setup.py`
- Why fragile:
  1. `mlflow_autolog()` raises exception if MLflow is unavailable; startup fails
  2. Evaluation errors are silently swallowed (line 32); no retry mechanism
  3. No validation that MLflow tracking URI is reachable before app starts
  4. If MLflow network is slow, entire query response is delayed
- Safe modification:
  1. Change startup autolog to non-fatal (warn, don't raise)
  2. Implement retry with backoff for transient evaluation failures
  3. Add MLflow health check to lifespan; warn if unavailable
  4. Move evaluation off critical path (background task)
- Test coverage: No tests; cannot test without MLflow service running

**Docker Compose Initialization Ordering:**
- Files: `docker-compose.yml`
- Why fragile:
  1. `depends_on` with `condition: service_completed_successfully` requires init service to finish; if pull fails, API never starts
  2. No timeout on model pull (line 20 `timeout=None` in main.py); network hang blocks startup indefinitely
  3. Profile-based service selection is strict; typo in COMPOSE_PROFILES causes no Ollama to start
  4. `init-chroma-perms` runs as root but must succeed before API starts; permission errors are not surfaced clearly
- Safe modification:
  1. Add startup timeout (e.g., 5min) to lifespan; fail fast if models don't pull
  2. Validate COMPOSE_PROFILES env var on startup; exit with clear error if invalid
  3. Log model pull progress with timestamps; make progress visible to operator
  4. Consider init container pattern (separate pod) instead of depends_on
- Test coverage: No integration tests; Compose file is only tested manually

---

## Scaling Limits

**Embedded Chroma Not Designed for Scale:**
- Current capacity: Embedded Chroma stores vectors in-process; default SQLite backend for metadata
- Limit: 
  - Memory grows linearly with chunk count; ~100k chunks = ~1-2GB RAM minimum
  - Single machine; no replication or failover
  - SQLite is single-writer; concurrent ingest may block queries
  - Persistence to Docker volume is not high-availability
- Scaling path:
  1. Migrate to standalone Chroma server (or ChromaDB Kubernetes)
  2. Switch to managed vector database (Pinecone, Qdrant, Weaviate)
  3. Add read-only replicas for query scaling
  4. Implement connection pooling if using external service

**Single LLM Instance (Ollama Model Loading):**
- Current capacity: Ollama loads one model per container; `llama3.2` (7B) + `mistral` (7B) + embeddings = ~20GB VRAM
- Limit: 
  - No model batching; sequential inference only
  - GPU VRAM exhaustion if larger models selected
  - No load balancing; all queries go to single Ollama instance
- Scaling path:
  1. Deploy Ollama as separate microservice with multiple replicas
  2. Add request queue / load balancer in front (e.g., ray serve, vLLM)
  3. Consider smaller quantized models (Q4, Q5) for VRAM savings
  4. Implement inference batching if latency allows

**MLflow Artifact Storage:**
- Current capacity: Bind mounts to local filesystem; default SQLite backend
- Limit:
  - Disk space for artifacts grows ~1-10MB per query (full context + answers stored)
  - At 1000 queries/day, 10GB/day artifact growth; disk full in ~10 days on small VM
  - SQLite is not replicated; single point of failure
- Scaling path:
  1. Configure S3 or GCS as artifact backend (`--default-artifact-root s3://bucket`)
  2. Use managed MLflow (Databricks) or cloud alternatives
  3. Implement artifact retention policy (e.g., delete runs >30d old)
  4. Monitor disk usage; alert when approaching limit

**API Container Single Replica:**
- Current capacity: Single FastAPI instance on port 8000; no horizontal scaling
- Limit:
  - ~100-200 req/s throughput (depends on query complexity)
  - Single instance failure = total outage
  - No load balancing across replicas
- Scaling path:
  1. Deploy API as Kubernetes Deployment with HPA (auto-scale on CPU/latency)
  2. Add load balancer (nginx, Traefik) in front
  3. Implement health check endpoints for orchestrator (already exists: /health)
  4. Add readiness probes (separate from liveness) that check Ollama connectivity

---

## Dependencies at Risk

**LangChain Dependencies (Fragmented Packages):**
- Risk: Project depends on 5 separate LangChain packages (`langchain`, `langchain-community`, `langchain-chroma`, `langchain-ollama`, `langchain-text-splitters`); each has independent versioning
- Impact: 
  - Version conflicts between packages (e.g., langchain 1.2.15 + langchain-community 0.4.1 may not be compatible in future)
  - API breaks when upgrading one package; must coordinate all upgrades
  - Maintenance burden tracking versions across ecosystem
- Migration plan:
  1. Consider alternative frameworks: LlamaIndex, Haystack, or custom RAG
  2. If continuing with LangChain, consolidate to single version constraint
  3. Add integration tests that run against latest LangChain versions (CI gate)
  4. Pin all LangChain packages to same release cadence

**MLflow 3.10.1 (Pre-release State):**
- Risk: MLflow GenAI evaluators (DeepEval integration) are relatively new API; may change in 3.11+
- Impact: 
  - Evaluation code in `src/services/evaluate.py` may break on MLflow update
  - GenAI scorers may be deprecated or replaced
  - No guarantee API stability across minor versions
- Migration plan:
  1. Test MLflow 3.11+ on CI; pin to known-good version
  2. Consider LLM-as-judge alternative (custom scorer) to reduce MLflow dependency
  3. Document breaking changes in MLflow per version

**DeepEval 3.9.5 (Indirect Dependency):**
- Risk: Pulled in by MLflow; used for LLM-as-judge scoring; no direct version control
- Impact: If DeepEval API changes, evaluation silently fails (caught in broad except)
- Migration plan:
  1. Add DeepEval to explicit dependencies with version constraint
  2. Implement custom evaluation if DeepEval becomes unstable
  3. Test evaluation separately from query path

**Python 3.14 (Beta/RC):**
- Risk: Dockerfile builds on `python:3.14-slim`; this version is very new (released Nov 2024); may have stability issues
- Impact:
  - Potential library incompatibility (wheels may not exist for 3.14)
  - Unexpected behavior changes between 3.14.0-RCn and 3.14.0 final
  - Security patches may lag for newer minor versions
- Migration plan:
  1. Downgrade to `python:3.13.8` (fully stable, matches pyproject.toml requirement)
  2. Test on 3.14 before upgrading production
  3. Use multi-stage builds to allow easy version swaps

---

## Missing Critical Features

**No Document Deduplication:**
- Problem: Uploading the same document twice creates duplicate chunks; wastes storage, degrades retrieval relevance
- Blocks: Multi-document apps with potential overlap; no idempotent ingest endpoint
- Recommendation: Hash documents or chunks on ingestion; skip if already present

**No Vectorstore Deletion/Update:**
- Problem: Once documents are ingested, they cannot be removed or updated; only way is delete entire collection
- Blocks: Document lifecycle management; cannot fix stale data without data loss
- Recommendation: Add `DELETE /ingest/{doc_id}` and `PUT /ingest/{doc_id}` endpoints; track document IDs

**No Relevance Feedback Loop:**
- Problem: No way for user to indicate if answer was helpful; evaluation is one-way (judge LLM, no human feedback)
- Blocks: Learning from failures; improving RAG over time
- Recommendation: Add thumbs-up/thumbs-down on answers; log feedback to MLflow; analyze patterns

**No Request Logging (Audit Trail):**
- Problem: No persistent record of who asked what questions or what answers were given (beyond MLflow artifacts)
- Blocks: Compliance, debugging user issues, understanding usage patterns
- Recommendation: Log all ingest/query events with timestamps, user ID (if auth added), inputs/outputs

**No Rate Limiting:**
- Problem: API accepts unlimited requests from any authenticated user; no protection against DoS
- Blocks: Cost control (embedding/LLM inference); service stability
- Recommendation: Add per-key rate limiting using `fastapi-limiter` or similar

**No Input Sanitization (Prompt Injection):**
- Problem: User question passed directly to LLM without sanitization; attacker can inject instructions
- Blocks: Reliable answer quality; system prompt can be overridden
- Recommendation: Add input validation/sanitization; consider prompt guards

**No Graceful Shutdown:**
- Problem: No shutdown hook in lifespan; requests in-flight when container stops may lose data
- Blocks: Zero-downtime deployments; data corruption in evaluation
- Recommendation: Implement shutdown context in lifespan; drain requests before exit

---

## Test Coverage Gaps

**No Unit Tests for Query Service:**
- What's not tested: `handle_query()` logic, vectorstore retrieval, LLM invocation, evaluation calling
- Files: `src/services/query.py`
- Risk: Regressions in core functionality go undetected; difficult to refactor global `_llm` variable
- Priority: **High** - This is the critical path

**No Unit Tests for Ingest Service:**
- What's not tested: File validation, PDF/text parsing, chunking, embedding, storage
- Files: `src/services/ingest.py`
- Risk: Regressions in document processing; no validation that chunks are correctly stored
- Priority: **High** - File handling is complex and error-prone

**No Integration Tests:**
- What's not tested: Full end-to-end flow (ingest → query); Docker Compose service interactions
- Files: All services
- Risk: Integration issues only discovered in production (e.g., Ollama timeout, Chroma connection failure)
- Priority: **High** - Current deployment is integration-heavy

**No Tests for Error Paths:**
- What's not tested: Missing vectorstore, Ollama unavailable, oversized file, invalid content-type, MLflow failure
- Files: All services
- Risk: Error handling code is untested; may not work when needed
- Priority: **Medium** - Most error paths are caught, but coverage is unknown

**No Load/Performance Tests:**
- What's not tested: Query latency, throughput, memory usage, concurrent ingests, vectorstore scaling
- Files: All services
- Risk: Performance regressions go unnoticed until production; no baseline for capacity planning
- Priority: **Medium** - Not critical for MVP, but necessary before scaling

**No Security Tests:**
- What's not tested: API key validation, file upload validation, prompt injection, directory traversal
- Files: `src/security.py`, `src/services/ingest.py`
- Risk: Security vulnerabilities go undetected; easy to introduce new ones during refactoring
- Priority: **Medium** - Especially important if exposing API externally

---

*Concerns audit: 2026-05-11*
