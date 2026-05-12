# Testing Patterns

**Analysis Date:** 2026-05-11

## Test Framework

**Runner:**
- pytest (version pinned transitively; configured in `pyproject.toml`)
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest built-in `assert` statements throughout — no separate assertion library

**Mocking:**
- `unittest.mock` standard library — `MagicMock`, `AsyncMock`, `patch`
- No `pytest-mock` — raw `unittest.mock` is used directly everywhere

**Run Commands:**
```bash
pytest                             # Run all tests
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m e2e                     # E2E tests only
pytest tests/unit/                # Run a specific subdirectory
pytest tests/unit/test_models.py  # Run a specific file
```

Coverage is not configured — no `pytest-cov`, no `--cov-fail-under` threshold.

## Test File Organization

**Location:** Separate `tests/` directory at repo root — not co-located with source.

**Structure:**
```
tests/
├── __init__.py
├── conftest.py                         # Shared fixtures (session client, auth_headers, make_upload_file)
├── unit/
│   ├── __init__.py
│   ├── test_models.py                  # Pydantic model validation
│   ├── test_security.py                # verify_api_key() function
│   ├── test_health_service.py          # check_health() service function
│   ├── test_ingest_service.py          # ingest_document() service function
│   └── test_query_service.py           # handle_query() service function
├── integration/
│   ├── __init__.py
│   ├── test_health_api.py              # GET /health via TestClient
│   ├── test_ingest_api.py              # POST /ingest via TestClient
│   └── test_query_api.py              # POST /query via TestClient
└── e2e/
    ├── __init__.py
    └── test_rag_flow.py                # Multi-step user journey flows
```

**Naming:** `test_<domain>_<layer>.py` — e.g., `test_health_service.py` (unit), `test_health_api.py` (integration).

**Test function naming:** Descriptive `test_<verb>_<condition>_<expected_outcome>` — e.g., `test_ingest_empty_file_raises_400`, `test_query_success_returns_answer_and_sources`, `test_health_ollama_connection_error_reports_error`.

## Markers

Three custom markers are declared in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = [
    "unit: unit tests — exercise functions directly without HTTP",
    "integration: integration tests — exercise HTTP endpoints with mocked services",
    "e2e: end-to-end tests — simulate realistic multi-step user sessions",
]
```

**Every test function is marked** — no unmarked tests exist:
```python
@pytest.mark.unit
def test_query_request_defaults():
    ...

@pytest.mark.integration
def test_ingest_missing_api_key_returns_401(client):
    ...

@pytest.mark.e2e
def test_full_rag_user_journey(client, auth_headers):
    ...
```

**Distribution:** 52 unit, 33 integration, 3 e2e = 88 total test functions.

## Shared Fixtures (`tests/conftest.py`)

Three fixtures are shared across all test tiers:

```python
@pytest.fixture(scope="session")
def client():
    from src.main import app
    with patch("src.main.mlflow_autolog"), patch("src.main.pull_model", new=AsyncMock()):
        with TestClient(app) as c:
            yield c

@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-api-key"}

@pytest.fixture
def make_upload_file():
    def _factory(filename: str, content: bytes, content_type: str | None) -> MagicMock:
        mock = MagicMock()
        mock.filename = filename
        mock.content_type = content_type
        mock.read = AsyncMock(side_effect=[content, b""])
        return mock
    return _factory
```

**Key fixture details:**
- `client` is `scope="session"` — one `TestClient` instance shared across all tests. Startup side effects (`mlflow_autolog`, `pull_model`) are patched out at session scope.
- `auth_headers` is function-scoped (default) — returns `{"X-API-Key": "test-api-key"}`.
- `make_upload_file` is a factory fixture — returns a factory function, not a mock directly. Callers invoke it: `mock_file = make_upload_file("doc.txt", b"Hello", "text/plain")`.
- Test API key is set via `os.environ["API_KEY"] = "test-api-key"` at the top of `conftest.py` (before `src.main` is imported) to satisfy `src/utils/env.py`'s startup validation.

## Unit Test Patterns

Unit tests call async service functions using `asyncio.run()` from synchronous test functions — `pytest-asyncio` is not used:

```python
@pytest.mark.unit
def test_health_all_ok():
    mock_httpx_cls = _make_httpx_cls(status_code=200)
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 5

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "ok"
    assert result.chromadb == "ok"
```

**Pattern:** arrange → patch context → `asyncio.run(service_func())` → assert on returned Pydantic model.

**Private test helper factories** are defined at module level in unit test files to reduce boilerplate:
```python
# tests/unit/test_health_service.py
def _make_httpx_cls(status_code: int = 200, raise_exc: Exception | None = None):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_http_client = AsyncMock()
    if raise_exc is not None:
        mock_http_client.get.side_effect = raise_exc
    else:
        mock_http_client.get.return_value = mock_response
    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_cls
```

The same helper is duplicated in `tests/integration/test_health_api.py` — a known redundancy.

## Integration Test Patterns

Integration tests use the shared `client` fixture (`fastapi.testclient.TestClient`) and call HTTP endpoints directly. Services are still mocked at the patch level:

```python
@pytest.mark.integration
def test_ingest_txt_success_returns_200_with_fields(client, auth_headers):
    mock_pages = [MagicMock()]
    mock_chunks = [MagicMock(), MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma") as mock_chroma, \
         patch("src.services.ingest.TextLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks
        mock_chroma.return_value.add_documents = MagicMock()

        resp = client.post(
            "/ingest",
            headers=auth_headers,
            files={"file": ("sample.txt", b"Sample document content", "text/plain")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["chunks_stored"] == 2
    assert data["filename"] == "sample.txt"
```

**Pattern:** use `client.post/get(...)` with `auth_headers` fixture → assert on `resp.status_code` and `resp.json()` fields.

**Schema validation tests** confirm required response keys are present:
```python
assert "status" in data
assert "chunks_stored" in data
assert "filename" in data
```

## E2E Test Patterns

E2E tests simulate complete user workflows in a single test — they chain multiple HTTP calls using the same `client`:

```python
@pytest.mark.e2e
def test_full_rag_user_journey(client, auth_headers):
    # Step 1: Ingest a document
    ingest_resp = client.post("/ingest", headers=auth_headers, files={...})
    assert ingest_resp.status_code == 200

    # Step 2: Query it
    query_resp = client.post("/query", headers=auth_headers, json={...})
    assert query_resp.status_code == 200

    # Step 3: Verify health
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
```

Each step still patches external services (LLM, vectorstore, httpx) within its own `with patch(...)` context. E2E tests verify behavioral contracts across the whole stack, not just individual endpoints.

## Mocking

**Framework:** `unittest.mock` — `patch`, `MagicMock`, `AsyncMock` only.

**What is mocked (always):**
- `src.services.ingest.OllamaEmbeddings` — avoids real embedding calls
- `src.services.ingest.Chroma` — avoids real ChromaDB writes
- `src.services.ingest.TextLoader` / `PyPDFLoader` — avoids real file I/O
- `src.services.ingest.RecursiveCharacterTextSplitter` — avoids real chunking
- `src.services.query._get_vectorstore` — avoids real vectorstore init
- `src.services.query.get_llm` — avoids real LLM instantiation
- `src.services.query.RunnableSequence` — controls LLM response content
- `src.services.query.run_judge_evaluations` — avoids real MLflow evaluation
- `src.services.health.httpx.AsyncClient` — avoids real Ollama HTTP calls
- `src.services.health.Chroma` / `OllamaEmbeddings` — avoids real ChromaDB probe
- `src.main.mlflow_autolog` / `src.main.pull_model` — avoids model download on startup

**What is NOT mocked:**
- Pydantic models — `QueryRequest`, `QueryResponse`, etc. are always instantiated directly to test validation logic
- `src.security.verify_api_key` — real dependency injection is exercised in integration tests
- FastAPI request/response parsing — `TestClient` runs the full ASGI stack

**Async context manager mocking pattern** (for `httpx.AsyncClient`):
```python
mock_cls = MagicMock()
mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
```

**`mock.assert_called_once_with(...)` pattern** — used to verify that fire-and-forget side effects (judge evaluations) were triggered with exact arguments:
```python
mock_eval.assert_called_once_with(
    question="What is the answer?",
    answer="The answer is 42.",
    context_chunks=["Relevant content here"],
)
```

## Error Testing Patterns

**HTTPException testing in unit tests:**
```python
@pytest.mark.unit
def test_ingest_empty_file_raises_400(make_upload_file):
    mock_file = make_upload_file("empty.txt", b"", "text/plain")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ingest_document(mock_file))
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Uploaded file is empty."
```

**HTTP error assertions in integration tests (via response body):**
```python
assert resp.status_code == 401
assert resp.json()["detail"] == "Unauthorized"
```

**Validation error testing (Pydantic):**
```python
with pytest.raises(ValidationError):
    QueryRequest(question="")

with pytest.raises(ValidationError):
    QueryRequest(question="a" * 5001)
```

**FastAPI 422 validation (integration):**
```python
resp = client.post("/query", headers=auth_headers, json={"question": ""})
assert resp.status_code == 422
```

## Boundary Testing Pattern

Model and API boundary values are tested exhaustively — every `ge`, `le`, `min_length`, `max_length` constraint has explicit test cases at and beyond its boundary:

```python
def test_query_request_top_k_min_boundary():    # top_k=1 OK
def test_query_request_top_k_max_boundary():    # top_k=20 OK
def test_query_request_top_k_zero_fails():      # top_k=0 raises ValidationError
def test_query_request_top_k_over_max_fails():  # top_k=21 raises ValidationError
def test_query_request_top_k_negative_fails():  # top_k=-1 raises ValidationError
```

## Test Coverage Gaps

**No coverage tooling configured** — no `pytest-cov`, no `--cov` flags, no CI coverage step.

**Untested areas:**
- `src/utils/env.py` — `_get_int_env()` parsing with malformed strings, missing API_KEY behavior
- `src/utils/log_manager.py` — `setup_logger()` factory, `CustomLogger` level methods
- `src/services/evaluate.py` — `run_judge_evaluations()` (always mocked, never directly tested)
- `src/tracking/setup.py` — `mlflow_autolog()` (always mocked out at startup)
- `src/main.py` — `pull_model()` retry/timeout behavior beyond mock-level patching

**`_make_httpx_cls` is duplicated** across `tests/unit/test_health_service.py` and `tests/integration/test_health_api.py` — should be moved to `tests/conftest.py`.

---

*Testing analysis: 2026-05-11*
