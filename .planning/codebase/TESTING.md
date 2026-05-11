# Testing Patterns

**Analysis Date:** 2026-05-11

## Test Framework

**Status:** No testing framework installed or configured

**Framework:** Not detected
- No pytest, unittest, or testify dependencies in `requirements.txt` or `pyproject.toml`
- No test configuration files found (no `pytest.ini`, `setup.cfg`, `tox.ini`)
- No test files found in repository (no `test_*.py`, `*_test.py`, `conftest.py`)

**Assertion Library:** Not applicable - no tests present

**Run Commands:** No test commands available
- No pytest command documented
- No `python -m unittest` setup
- CI workflow `lint.yml` only runs `ruff check .` (linting only, no tests)

## Test File Organization

**Current State:** No tests currently implemented

**Would-be Pattern (if implemented):**
- Location: Likely separate `tests/` directory at repo root (following Python conventions)
- Alternative: Co-located `test_*.py` files adjacent to source modules in `src/`
- Naming: Would follow `test_<module>.py` or `<module>_test.py` pattern

**Test Collection:** Not applicable until tests are added

## Test Structure

**Current State:** No test examples in codebase

**Observed Testing Needs (based on source code):**

The codebase would benefit from tests covering:

1. **API Layer** (`src/api/router.py`):
   - Route handlers: `POST /ingest`, `POST /query`, `GET /health`
   - Authentication via `verify_api_key` dependency
   - Response model validation

2. **Service Layer** (`src/services/`):
   - `ingest_document()` - file upload validation, chunking, vector storage
   - `handle_query()` - retrieval, LLM prompt construction, judge evaluation
   - `check_health()` - health probe for Ollama and ChromaDB
   - `run_judge_evaluations()` - MLflow evaluation invocation

3. **Models** (`src/models.py`):
   - Pydantic model validation: `QueryRequest` constraints (min_length, max_length, bounds)

4. **Security** (`src/security.py`):
   - API key verification with valid/invalid/missing headers

5. **Utilities** (`src/utils/`):
   - `_get_int_env()` - integer environment variable parsing with defaults
   - Logger initialization and wrapper functionality

## Mocking

**Framework:** Not configured yet

**Would-be Approach:**
- Standard library: `unittest.mock` for simple mocks
- Alternative: `pytest-mock` or `responses` library for HTTP mocking
- LangChain mocking: Mock `Chroma`, `ChatOllama`, `OllamaEmbeddings` from langchain libraries
- HTTPx mocking: Mock `httpx.AsyncClient` for external service calls to Ollama

**What to Mock (recommended):**
- External services: `httpx.AsyncClient` for Ollama API calls
- Vector store: `Chroma` (avoid real vector database in unit tests)
- LLM: `ChatOllama` (avoid real inference during testing)
- Embeddings: `OllamaEmbeddings` (avoid network calls)
- MLflow: `evaluate()` and scorer functions (avoid experiment tracking during testing)
- File I/O: `tempfile.NamedTemporaryFile` (avoid disk writes)

**What NOT to Mock:**
- Pydantic models - test actual validation logic
- Security dependency `verify_api_key()` - test with real dependency injection
- Configuration loading from `src/utils/env` - test with real environment variables

## Fixtures and Factories

**Test Data:** Not yet implemented

**Would-be Pattern:**
- Pydantic models as fixtures: `@pytest.fixture def query_request() -> QueryRequest`
- Sample files: Fixtures for test PDF and text files in `tests/fixtures/`
- Mock responses: Pre-built API responses for Ollama, ChromaDB health checks

**Example (recommended structure):**
```python
# tests/conftest.py
import pytest
from src.models import QueryRequest, IngestResponse

@pytest.fixture
def sample_query_request() -> QueryRequest:
    return QueryRequest(question="What is in the document?", top_k=4)

@pytest.fixture
def sample_upload_file():
    # Mock UploadFile for testing ingest_document()
    pass
```

**Location:** Would live in `tests/conftest.py` or `tests/fixtures/` directory (not yet created)

## Coverage

**Requirements:** None enforced

**Status:**
- No coverage targets defined in `pyproject.toml`
- No coverage configuration file (`coverage.ini`, `.coveragerc`)
- No coverage GitHub Action configured
- Coverage currently 0% (no tests written)

**View Coverage (would use):**
```bash
pytest --cov=src --cov-report=html    # Generate HTML coverage report
pytest --cov=src --cov-report=term    # Terminal coverage summary
```

## Test Types

**Unit Tests:**
- Scope: Individual functions and classes in isolation
- Approach: Mock external dependencies (Ollama, ChromaDB, MLflow)
- Target modules:
  - `src/security.py` - API key validation
  - `src/utils/env.py` - environment variable parsing
  - `src/models.py` - Pydantic validation
  - `src/utils/log_manager.py` - logger setup and wrapper

**Integration Tests:**
- Scope: Service layer with mocked external services
- Approach: Test full flow (ingest, query) with real Pydantic models and mocked HTTP/LLM
- Target modules:
  - `src/services/ingest.py` - file upload → chunking → vector storage
  - `src/services/query.py` - question → retrieval → LLM → response
  - `src/api/router.py` - HTTP routes with dependencies

**E2E Tests:**
- Framework: Not used currently
- Would require: Real Ollama, ChromaDB, MLflow services (Docker Compose)
- Recommended tool: `pytest-docker`, `testcontainers-python`
- Coverage: End-to-end flows with actual ML services

## Common Patterns (Recommended)

**Async Testing:**
```python
# Would use pytest-asyncio for async test support
import pytest

@pytest.mark.asyncio
async def test_handle_query_success(mock_vectorstore):
    """Test successful query with mocked vector store."""
    response = await handle_query(QueryRequest(question="test?"))
    assert response.answer != ""
    assert len(response.sources) > 0
```

**Error Testing:**
```python
# Test error scenarios with HTTPException raising
import pytest
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_ingest_file_too_large():
    """Test rejection of oversized uploads."""
    with pytest.raises(HTTPException) as exc_info:
        await ingest_document(oversized_file)
    assert exc_info.value.status_code == 413
```

**Dependency Injection in Tests:**
```python
# Use FastAPI TestClient with dependency overrides
from fastapi.testclient import TestClient
from src.main import app

def test_query_without_api_key():
    """Test that missing API key returns 401."""
    client = TestClient(app)
    response = client.post("/query", json={"question": "test?"})
    assert response.status_code == 401
```

## Critical Test Gaps

**High Priority Tests Needed:**

1. **API key validation** (`src/security.py`):
   - Missing API key → 401 response
   - Invalid API key → 401 response
   - Valid API key → request proceeds

2. **File upload validation** (`src/services/ingest.py`):
   - Unsupported file type (`.zip`, `.docx`) → 400 response
   - Empty file → 400 response
   - File exceeds `MAX_UPLOAD_SIZE_BYTES` → 413 response
   - Valid PDF/text file → successful ingestion

3. **Query validation** (`src/services/query.py`):
   - No documents ingested → 404 response
   - Valid question → returns answer and sources
   - Top-k parameter bounds (`1 <= top_k <= 20`) enforcement

4. **Health check** (`src/services/health.py`):
   - Ollama unavailable → `ollama: "error"`
   - ChromaDB unavailable → `chromadb: "error"`
   - All services available → all statuses "ok"

5. **Environment configuration** (`src/utils/env.py`):
   - Missing `API_KEY` env var → `RuntimeError` on startup
   - Integer env var parsing with defaults

## Test Infrastructure Plan

**Recommended Setup (Phase 1):**
1. Install pytest: `pip install pytest pytest-asyncio responses`
2. Create `tests/` directory with `conftest.py`
3. Add `[tool.pytest.ini_options]` to `pyproject.toml`
4. Update CI workflow `lint.yml` to include `pytest` step
5. Start with unit tests for security and utilities

**Recommended Setup (Phase 2):**
1. Add `pytest-cov` for coverage reporting
2. Create fixtures for Pydantic models and mock files
3. Write integration tests for service layer
4. Configure coverage thresholds (e.g., `--cov-fail-under=70`)

**Recommended Setup (Phase 3):**
1. E2E tests with `testcontainers-python` or `pytest-docker`
2. Test against real Docker Compose stack
3. Coverage reporting in CI/CD pipeline

---

*Testing analysis: 2026-05-11*
