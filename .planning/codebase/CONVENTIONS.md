# Coding Conventions

**Analysis Date:** 2026-05-11

## Naming Patterns

**Files:**
- `snake_case.py` throughout — e.g., `log_manager.py`, `ingest.py`, `test_health_api.py`
- Test files always prefixed with `test_` — e.g., `test_query_service.py`
- Module names match the domain concept they represent: `health.py`, `query.py`, `ingest.py`

**Functions:**
- `snake_case` for all functions — e.g., `check_health`, `ingest_document`, `handle_query`
- Async service functions use descriptive verb phrases: `check_health()`, `ingest_document()`, `handle_query()`
- Private helper functions prefixed with `_` — e.g., `_get_vectorstore()`, `_get_int_env()`, `_log_with_extra()`
- Route handler functions use short, generic names matching their HTTP action: `ingest()`, `query()`, `health()`

**Variables:**
- `snake_case` for locals — e.g., `tmp_path`, `total_bytes`, `collection_count`, `safe_top_k`
- Module-level constants in `UPPER_SNAKE_CASE` — e.g., `ALLOWED_EXTENSIONS`, `TEMPLATE`, `LOG_LEVEL`
- Environment variable constants in `UPPER_SNAKE_CASE` in `src/utils/env.py` — e.g., `OLLAMA_MODEL`, `API_KEY`, `MAX_UPLOAD_SIZE_BYTES`
- Private singletons use `_` prefix + `snake_case` — e.g., `_llm` in `src/services/query.py`
- Unused injected dependency named `_`:
  ```python
  async def ingest(file: UploadFile = File(...), _: None = Depends(verify_api_key)):
  ```

**Classes:**
- `PascalCase` for all classes
- Pydantic request/response models use `Request`/`Response` suffix — e.g., `QueryRequest`, `QueryResponse`, `IngestResponse`, `HealthResponse`
- Utility classes use descriptive names — e.g., `CustomLogger`

**Test helper functions inside test files:**
- Module-level private factory helpers use `_` prefix — e.g., `_make_httpx_cls()` in `tests/unit/test_health_service.py` and `tests/integration/test_health_api.py`

## Code Style

**Linting:**
- Tool: `ruff==0.15.6` (listed as a project dependency in `pyproject.toml`)
- No `[tool.ruff]` section in `pyproject.toml` — ruff runs with default settings
- CI enforces `ruff check .` on every push and PR to `main` via `.github/workflows/lint.yml`
- No `# noqa` suppression comments present in the codebase

**Formatting style indicators (inferred from code):**
- 4-space indentation throughout
- Multi-argument imports use parenthesized multi-line form with trailing comma:
  ```python
  from src.utils.env import (
      CHROMA_COLLECTION_NAME,
      CHROMA_PERSIST_DIR,
      OLLAMA_BASE_URL,
      OLLAMA_EMBED_MODEL,
  )
  ```
- Multi-clause `with` statements use backslash continuation:
  ```python
  with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
       patch("src.services.health.OllamaEmbeddings"), \
       patch("src.services.health.Chroma", return_value=mock_vs):
  ```

## Import Organization

**Order observed consistently across all source and test files:**
1. Standard library — `import os`, `import asyncio`, `import logging`, `import tempfile`
2. Third-party packages — `from fastapi import ...`, `from langchain_chroma import ...`, `from pydantic import ...`
3. Internal `src.*` imports — `from src.models import ...`, `from src.utils.env import ...`

**Path convention:** All internal imports use the full `src.*` package path. `pythonpath = ["."]` in `pyproject.toml` makes this work without installing the package.

**No `__all__` exports** — modules expose their public API implicitly. `__init__.py` files are all empty.

## Type Annotations

All public functions carry full type annotations on parameters and return types:
```python
def _get_int_env(name: str, default: int) -> int: ...
async def check_health() -> HealthResponse: ...
async def ingest_document(file: UploadFile) -> IngestResponse: ...
async def handle_query(request: QueryRequest) -> QueryResponse: ...
```

**Union types** use Python 3.10+ `X | Y` syntax (not `Optional[X]`):
```python
x_api_key: str | None = Header(...)
raise_exc: Exception | None = None
_llm: ChatOllama | None = None
```

**Collection types** use built-in lowercase forms, not `typing` imports:
```python
sources: list[str] = []
context_chunks: list[str]
```

Pydantic models use `Field` for constraints:
```python
question: str = Field(..., min_length=1, max_length=5000)
top_k: int = Field(default=4, ge=1, le=20)
```

## Error Handling

**Strategy:** Raise `fastapi.HTTPException` directly from service functions — errors propagate unchanged through routers.

**HTTP status codes used:**
- `400` — validation failures (unsupported file type, empty file, wrong content type)
- `401` — authentication failure
- `404` — no documents in vectorstore
- `413` — upload too large
- `500` — unexpected pipeline failure

**Standard service-level pattern** (`src/services/query.py`):
```python
try:
    # ... business logic ...
    return QueryResponse(answer=answer, sources=sources)
except HTTPException:
    raise                          # pass through domain errors unchanged
except Exception as exc:
    logger.error(f"Query pipeline error: {exc}")
    raise HTTPException(status_code=500, detail="Internal query pipeline error.")
```

**Non-fatal errors** are caught, logged as a warning, and swallowed so the main response is still returned (`src/services/evaluate.py`):
```python
except Exception as exc:
    logger.warning(f"Judge evaluation failed (answer still returned): {exc}")
```

**Health checks** never raise — they accumulate `"ok"` / `"error"` status strings and always return a structured `HealthResponse`.

**Silent fallback pattern** for non-critical sub-checks:
```python
try:
    collection_count = vectorstore._collection.count()
except Exception:
    collection_count = 0
```

## Logging

**Framework:** Standard library `logging` wrapped by `CustomLogger` in `src/utils/log_manager.py`.

**Singleton import:** A single `logger` instance is imported and reused across all modules:
```python
from src.utils.log_manager import logger

logger.info("Starting up — pulling required Ollama models...")
logger.warning(f"Timed out while pulling Ollama model {model}: {exc}")
logger.error(f"Query pipeline error: {exc}")
```

**Log levels and when to use them:**
- `info` — lifecycle events (startup, model ready, MLflow setup)
- `warning` — non-fatal recoverable errors (timeout during model pull, failed evaluation)
- `error` — unexpected failures in request paths (before converting to HTTP 500)

**Format:** `%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s`

**F-string interpolation** is the universal pattern for log messages.

## Comments and Docstrings

**Docstrings** are present only in `src/utils/log_manager.py` on `CustomLogger` and its methods:
```python
class CustomLogger:
    """A wrapper class around the standard Python logger instance"""

    def info(self, message: str) -> None:
        """Logs a message with level INFO"""
```

**Service and route functions have no docstrings** — the code is self-documenting via type annotations and descriptive naming.

**No inline comments** — there are zero `# TODO`, `# FIXME`, `# HACK`, or explanatory inline comments in the codebase.

## Module Design

**No barrel re-exports** — `__init__.py` files are empty in all packages. Importers must use the full module path.

**One responsibility per file:** Each service file owns exactly one domain operation:
- `src/services/health.py` — health check
- `src/services/ingest.py` — document ingestion
- `src/services/query.py` — RAG query pipeline
- `src/services/evaluate.py` — LLM judge evaluation

**Module-level state** is used sparingly and isolated — only `src/services/query.py` uses a module-level singleton (`_llm`) guarded by a `get_llm()` accessor function.

**Constants** are declared at module level, not inside classes or functions:
- `ALLOWED_EXTENSIONS`, `ALLOWED_CONTENT_TYPES` in `src/services/ingest.py`
- `TEMPLATE`, `_llm` in `src/services/query.py`

## Environment Configuration Convention

All environment variables are centralized in `src/utils/env.py`. No other module calls `os.getenv()` directly. They import named constants:
```python
from src.utils.env import (
    CHROMA_COLLECTION_NAME,
    OLLAMA_BASE_URL,
    MAX_UPLOAD_SIZE_BYTES,
)
```

`src/utils/env.py` validates eagerly at import time — raises `RuntimeError` immediately if `API_KEY` is unset.

---

*Convention analysis: 2026-05-11*
