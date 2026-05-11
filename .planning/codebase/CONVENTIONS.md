# Coding Conventions

**Analysis Date:** 2026-05-11

## Naming Patterns

**Files:**
- Module files use lowercase with underscores: `log_manager.py`, `env.py`
- Package directories use lowercase with underscores
- Barrel files (`__init__.py`) present but empty in most packages (`src/api/__init__.py`, `src/services/__init__.py`, `src/utils/__init__.py`, `src/tracking/__init__.py`)

**Functions:**
- Use snake_case: `pull_model()`, `handle_query()`, `ingest_document()`, `check_health()`, `verify_api_key()`
- Async functions use same snake_case convention: `async def pull_model()`, `async def check_health()`
- Private functions prefixed with underscore: `_get_vectorstore()`, `_log_with_extra()`, `_get_int_env()`
- Callable variables also use snake_case: `setup_logger()`

**Variables:**
- All local variables use snake_case: `tmp_path`, `total_bytes`, `collection_count`, `safe_top_k`, `source_docs`
- Global module-level variables use UPPERCASE: `TEMPLATE`, `ALLOWED_EXTENSIONS`, `ALLOWED_CONTENT_TYPES`, `LOG_LEVEL`, `LOG_FORMAT`
- Environment variables in uppercase: `OLLAMA_MODEL`, `API_KEY`, `MAX_UPLOAD_SIZE_BYTES`, `MLFLOW_TRACKING_URI`
- Singleton instance variables use lowercase: `_llm`, `standard_logger`, `logger`

**Types/Classes:**
- Pydantic models use PascalCase: `IngestResponse`, `QueryRequest`, `QueryResponse`, `HealthResponse`
- Regular classes use PascalCase: `CustomLogger`
- Type hints use standard Python conventions: `ChatOllama | None`, `list[str]`

## Code Style

**Formatting:**
- No explicit formatter config (no Black, Prettier, or isort configuration)
- Code appears consistently formatted following PEP 8
- Line length appears to be ~88-100 characters based on observed code
- Indentation: 4 spaces throughout

**Linting:**
- Tool: Ruff (v0.15.6 in `pyproject.toml` and `requirements.txt`)
- CI enforcement: GitHub Actions workflow `lint.yml` runs `ruff check .` on push to main and pull requests
- Default ruff configuration (no custom `[tool.ruff]` section in `pyproject.toml`)
- Linting is mandatory before merge to main branch

## Import Organization

**Order (observed across codebase):**
1. Standard library imports: `import tempfile`, `import logging`, `from pathlib import Path`, `from contextlib import asynccontextmanager`
2. Third-party framework imports: `from fastapi import FastAPI`, `from pydantic import BaseModel`
3. Third-party library imports: `from langchain_chroma import Chroma`, `from langchain_ollama import OllamaEmbeddings`
4. Internal package imports: `from src.models import ...`, `from src.services.health import ...`, `from src.utils.env import ...`

**Path Aliases:**
- No alias configuration detected
- Full absolute imports from `src/` root: `from src.api.router import router`, `from src.services.query import handle_query`

**Import patterns:**
- Specific imports preferred: `from src.models import HealthResponse, IngestResponse, QueryRequest, QueryResponse`
- Bulk environment variable imports: `from src.utils.env import (OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL, ...)`
- Single imports for simple modules: `from src.security import verify_api_key`

## Error Handling

**Patterns:**
- FastAPI exceptions for HTTP responses: `raise HTTPException(status_code=400, detail="message")`
- Status codes used: 400 (validation), 401 (auth), 404 (not found), 413 (payload too large), 500 (server error)
- Bare except clauses catch all exceptions, then either re-raise or log: `except Exception as exc:` then `raise HTTPException(...)`
- Specific exception catching for known exceptions: `except httpx.TimeoutException`, `except ValueError:`
- Silent exception suppression in health checks: `except Exception: status = "error"` (no logging)
- Exceptions converted to HTTP responses in service layer, not domain layer

**Example from `src/services/query.py` (lines 51-95):**
```python
try:
    vectorstore = _get_vectorstore()
    try:
        collection_count = vectorstore._collection.count()
    except Exception:
        collection_count = 0
    
    if collection_count == 0:
        raise HTTPException(status_code=404, detail="No documents found...")
    
    # ... query logic ...
    return QueryResponse(answer=answer, sources=sources)

except HTTPException:
    raise
except Exception as exc:
    logger.error(f"Query pipeline error: {exc}")
    raise HTTPException(status_code=500, detail="Internal query pipeline error.")
```

**Anti-pattern observed:** Re-raising caught exceptions unnecessarily (see `src/tracking/setup.py` line 14: `raise e` after logging)

## Logging

**Framework:** Python standard `logging` module with custom wrapper

**Custom logger:** `CustomLogger` class in `src/utils/log_manager.py` wraps standard logger
- Uses `stacklevel=3` to report correct calling module
- Methods: `info()`, `warning()`, `error()`, `debug()`, `critical()`
- Module-level instance: `logger = CustomLogger(standard_logger)`

**Setup:**
- Logger configured in `src/utils/log_manager.py` via `setup_logger()` function
- Format: `"%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"`
- Log level: `logging.INFO` (hardcoded in `src/utils/log_manager.py` line 5)
- Handler: `logging.StreamHandler(sys.stdout)` — logs to stdout

**Usage patterns:**
- Informational messages: `logger.info("message")`
- Warnings: `logger.warning("message")`
- Errors: `logger.error("message")`
- Structured logging: String interpolation with f-strings: `logger.error(f"Query pipeline error: {exc}")`

**When to log:**
- Startup events: model pulling, MLflow configuration
- Warnings for non-critical failures: timeout on model pull, failed evaluations
- Errors for exceptions before conversion to HTTP response
- Health check failures are silent (no logger call)

## Comments

**When to Comment:**
- Single-line docstrings for functions with parameters or return values
- Comments rare in observed code — functionality is straightforward
- No inline comments for complex logic observed

**JSDoc/TSDoc:**
- Python docstrings used only for public functions in utility modules
- Format: Triple-quoted string (PEP 257 style)
- Example from `src/utils/log_manager.py` (lines 9-10):
```python
def setup_logger(name: str) -> logging.Logger:
    """Configures and returns a dedicated, standardized logger instance."""
```

## Function Design

**Size:**
- Functions are concise and focused (10-50 lines typical)
- Async route handlers delegate to service functions (`src/api/router.py`)
- Service functions handle business logic (`src/services/`)

**Parameters:**
- Type hints required for all function parameters
- Defaults used for optional params: `def verify_api_key(x_api_key: str | None = Header(...))`
- Union types (Python 3.10+ style): `str | None` instead of `Optional[str]`

**Return Values:**
- Type hints required: `-> IngestResponse`, `-> QueryResponse`, `-> HealthResponse`
- Pydantic models returned from async handlers
- `None` return for dependency functions: `-> None`

## Module Design

**Exports:**
- No explicit `__all__` lists observed
- All public functions and classes exported implicitly
- Private functions prefixed with underscore

**Barrel Files:**
- Empty `__init__.py` files in packages: `src/api/__init__.py`, `src/services/__init__.py`, `src/utils/__init__.py`, `src/tracking/__init__.py`
- No re-exports from barrel files

**Module organization by concern:**
- `src/api/` - HTTP routing layer
- `src/services/` - Business logic (ingest, query, evaluate, health)
- `src/utils/` - Configuration (env) and utilities (logging)
- `src/tracking/` - Experiment tracking setup (MLflow)
- `src/models.py` - Data models (Pydantic)
- `src/security.py` - Authentication
- `src/main.py` - Application entry point

## Type Annotations

**Style:**
- Type hints on all function signatures (required)
- Modern Python 3.10+ union syntax: `str | None` (used in `src/services/query.py`)
- Built-in collection types: `list[str]`, `dict[str, str]` (no `List`, `Dict` imports)
- Type hints for class attributes in Pydantic models only

**Example from `src/models.py`:**
```python
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(default=4, ge=1, le=20)
```

---

*Convention analysis: 2026-05-11*
