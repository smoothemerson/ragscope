# Phase 1: Test Infrastructure - Research

**Researched:** 2026-04-13
**Domain:** pytest configuration, async test infrastructure, FastAPI test patterns
**Confidence:** HIGH (all critical findings verified against actual codebase files)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | pytest configured with asyncio_mode=auto, asyncio_default_fixture_loop_scope=function, testpaths, markers (unit/integration/e2e), and API_KEY injected via pytest-env so collection never raises RuntimeError | See §pyproject.toml changes and §tests/conftest.py |
| INFRA-02 | Test dependencies added to pyproject.toml: pytest-cov>=6.0, pytest-env>=1.1, pytest-mock>=3.14, pytest-timeout>=2.3, respx>=0.22 | See §Standard Stack and §pyproject.toml diff |
| INFRA-03 | tests/ skeleton with conftest.py at root and per-tier conftest.py in unit/, integration/, e2e/ | See §Directory Skeleton and §conftest.py content |
| INFRA-04 | pytest-cov configured with fail_under=80, branch=true, concurrency=["thread","greenlet"], source=["src"] | See §pyproject.toml changes — [tool.coverage.*] sections |
</phase_requirements>

---

## Summary

Phase 1 sets up the test scaffolding that all subsequent phases depend on. The codebase already has pytest 9.0.2 and pytest-asyncio 1.3.0 in `uv.lock`, but pytest-cov, pytest-env, pytest-mock, pytest-timeout, and respx are absent from both `pyproject.toml` and `uv.lock`. They must be added as `[project.optional-dependencies]` under a `dev` group so `uv sync --extra dev` installs them without polluting the production dependency set.

The single most critical issue is that `src/utils/env.py` raises `RuntimeError("API_KEY is required and must not be empty.")` at **module import time** — not at application startup. Any pytest collection that causes Python to import anything from `src` will fail instantly unless `os.environ["API_KEY"]` is set **before** the first import. The root `tests/conftest.py` must set this environment variable at module level (not inside a fixture) because conftest.py files are executed before collection walks `src/`.

The second critical issue is that `mlflow.autolog()` (called in `src/tracking/setup.py`) patches `httpx` globally. If it runs during tests without mocking, subsequent tests using `httpx.AsyncClient` via `respx` will receive patched transport instead of the respx mock, causing unrelated test failures. The root conftest must patch `src.tracking.setup.mlflow_autolog` before any app import occurs.

**Primary recommendation:** Write the root `conftest.py` to set `API_KEY` at module level and stub `mlflow_autolog` via `monkeypatch`/`unittest.mock.patch` at session scope, then create minimal per-tier conftest.py files that add skip logic and the `_llm` autouse reset fixture in the unit tier.

---

## Standard Stack

### Core Test Libraries

| Library | Required Version | Already in uv.lock | Purpose |
|---------|-----------------|---------------------|---------|
| pytest | 9.0.2 (locked) | YES | Test runner |
| pytest-asyncio | 1.3.0 (locked) | YES | async test support |
| pytest-cov | >=6.0 | NO — add | Coverage with branch support |
| pytest-env | >=1.1 | NO — add | Inject env vars at collection time |
| pytest-mock | >=3.14 | NO — add | `mocker` fixture |
| pytest-timeout | >=2.3 | NO — add | Per-test timeout guard |
| respx | >=0.22 | NO — add | httpx mock router for unit tests |

**Version note:** Exact latest versions could not be verified (network unreachable in this environment). The minimum specifiers from INFRA-02 are the authoritative constraint. `uv add --dev` will resolve the newest compatible release. [ASSUMED: >=6.0/>=1.1/>=3.14/>=2.3/>=0.22 are current minimum-viable specifiers per REQUIREMENTS.md; exact latest PyPI versions unverified.]

### Installation

```bash
# uv: add all dev deps in one command
uv add --optional dev pytest-cov pytest-env pytest-mock pytest-timeout respx

# OR edit pyproject.toml manually then run:
uv sync --extra dev
```

---

## Architecture Patterns

### Recommended Directory Skeleton

```
tests/
├── conftest.py          # Session-scope: API_KEY guard, mlflow stub, app fixture
├── unit/
│   ├── __init__.py
│   ├── conftest.py      # autouse _llm reset, ephemeral chroma fixture
│   └── (test files added in Phase 2/3/4)
├── integration/
│   ├── __init__.py
│   ├── conftest.py      # skip if services unavailable
│   └── (test files added in Phase 5)
└── e2e/
    ├── __init__.py
    ├── conftest.py      # skip if full stack unavailable
    └── (test files added in Phase 5)
```

`__init__.py` files are needed in each tier so pytest can distinguish test modules with the same filename across tiers (e.g., `unit/test_query.py` vs `integration/test_query.py`).

### Pattern: Root conftest.py — Collection-time Environment Guard

**What:** Sets `API_KEY` at module level (before any fixture or test runs) so `src/utils/env.py` never raises during collection.

**Why module level, not a fixture:** Python imports `conftest.py` before it walks the test tree. A `@pytest.fixture` runs only when a test requests it — too late. The `os.environ` assignment at the top of conftest.py is evaluated at import time.

```python
# tests/conftest.py  — module-level guard (VERIFIED: direct analysis of src/utils/env.py line 34-35)
import os
os.environ.setdefault("API_KEY", "test-api-key-for-pytest")

# Must happen before any src.* import to prevent RuntimeError
```

### Pattern: mlflow.autolog Stub at Session Scope

```python
# tests/conftest.py (continued)
from unittest.mock import patch

# Patch before app is imported anywhere in the test session
_mlflow_patcher = patch("src.tracking.setup.mlflow_autolog", return_value=None)
_mlflow_patcher.start()

import pytest

@pytest.fixture(scope="session", autouse=True)
def _stop_mlflow_patcher():
    yield
    _mlflow_patcher.stop()
```

**Why:** `mlflow.autolog()` patches `httpx` globally. If it runs before respx mocks are installed, `httpx.AsyncClient` sends real network traffic instead of being intercepted. Stopping the patcher at session end is good hygiene but is not strictly required for CI correctness.

### Pattern: _llm Singleton Reset in Unit Tier

```python
# tests/unit/conftest.py
import pytest
import src.services.query as query_module

@pytest.fixture(autouse=True)
def reset_llm_singleton():
    """Reset the _llm global between tests to prevent cross-test contamination."""
    query_module._llm = None
    yield
    query_module._llm = None
```

**Why:** `src/services/query.py` exposes a module-level `_llm: ChatOllama | None = None`. `get_llm()` returns the cached instance on the second call. Tests that mock `get_llm` or `ChatOllama.__init__` can leave a real (or partially-mocked) instance in the global, causing the next test to skip initialization and use a stale object. [VERIFIED: direct reading of src/services/query.py lines 20, 32-35]

### Pattern: Integration Tier Skip Logic

```python
# tests/integration/conftest.py
import httpx
import pytest

def _service_available(url: str) -> bool:
    try:
        httpx.get(url, timeout=2.0)
        return True
    except Exception:
        return False

@pytest.fixture(scope="session")
def chroma_available():
    return _service_available("http://localhost:8001/api/v1/heartbeat")

@pytest.fixture(scope="session")
def ollama_available():
    return _service_available("http://localhost:11435/api/tags")

@pytest.fixture(autouse=True)
def skip_if_services_unavailable(chroma_available, ollama_available):
    if not chroma_available or not ollama_available:
        pytest.skip("Integration services (ChromaDB:8001, Ollama:11435) not available")
```

### Pattern: E2E Tier Skip Logic

```python
# tests/e2e/conftest.py
import os
import pytest

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("E2E_BASE_URL", "http://localhost:8000")

@pytest.fixture(autouse=True)
def skip_if_no_stack(base_url):
    import httpx
    try:
        httpx.get(f"{base_url}/health", timeout=3.0)
    except Exception:
        pytest.skip(f"Full stack not available at {base_url}")
```

---

## pyproject.toml Changes (Exact Diff)

The current `pyproject.toml` has only a `[project]` table and no tool configuration. The following additions are required:

```toml
# ADD: optional-dependencies for dev/test tooling
[project.optional-dependencies]
dev = [
  "pytest-cov>=6.0",
  "pytest-env>=1.1",
  "pytest-mock>=3.14",
  "pytest-timeout>=2.3",
  "respx>=0.22",
]

# ADD: pytest configuration
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
markers = [
  "unit: fast, isolated tests with all externals mocked",
  "integration: tests against real services (ChromaDB, Ollama) — requires docker-compose.test.yml",
  "e2e: full stack tests — requires running application",
]
# pytest-env: inject at collection time so src/utils/env.py never raises RuntimeError
env = [
  "API_KEY=test-api-key-for-pytest",
]
timeout = 30

# ADD: coverage main config
[tool.coverage.run]
source = ["src"]
branch = true
concurrency = ["thread", "greenlet"]
omit = ["src/__init__.py", "src/*/__ init__.py"]

# ADD: coverage reporting config
[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = false

# ADD: coverage HTML output
[tool.coverage.html]
directory = "htmlcov"
```

**Key detail on `pytest-env` vs `os.environ` in conftest:** Both are needed. `pytest-env`'s `[tool.pytest.ini_options] env` block sets the variable before pytest processes plugins but the ordering relative to conftest.py module-level code is not guaranteed across all pytest versions. Setting `os.environ.setdefault("API_KEY", "test-api-key-for-pytest")` at the top of `tests/conftest.py` is a belt-and-suspenders defense that ensures the variable is present no matter what. [ASSUMED: exact ordering guarantee between pytest-env plugin and conftest.py module-level execution is not verified against pytest-env 1.1.x release notes — treat both as required.]

---

## Exact conftest.py File Contents

### tests/conftest.py

```python
"""
Root test configuration.

CRITICAL: API_KEY must be set before any src.* import to prevent RuntimeError.
src/utils/env.py raises RuntimeError at module level when API_KEY is empty.
"""
import os

# Set BEFORE any src import — module-level execution happens at collection time
os.environ.setdefault("API_KEY", "test-api-key-for-pytest")

# Stub mlflow.autolog BEFORE app import to prevent httpx global patching
# mlflow.autolog() patches httpx transport; if it runs before respx mocks are
# installed, respx interception is bypassed and tests make real network calls.
from unittest.mock import patch as _patch

_mlflow_patcher = _patch("src.tracking.setup.mlflow_autolog", return_value=None)
_mlflow_patcher.start()

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="session", autouse=True)
def _stop_mlflow_patcher():
    """Tear down the mlflow patcher at end of test session."""
    yield
    _mlflow_patcher.stop()


@pytest.fixture(scope="session")
def app():
    """Application instance — session-scoped, constructed once."""
    from src.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def sync_client(app):
    """Synchronous TestClient for simple request/response tests."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
async def async_client(app):
    """Async HTTPX client — function-scoped for isolation."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-api-key-for-pytest"},
    ) as client:
        yield client
```

### tests/unit/conftest.py

```python
"""
Unit test configuration.

Provides:
- autouse _llm singleton reset between tests (prevents cross-test contamination)
- ephemeral ChromaDB fixture for tests that need a real but isolated store
"""
import pytest
import src.services.query as _query_module


@pytest.fixture(autouse=True)
def reset_llm_singleton():
    """
    Reset the module-level _llm global before and after each test.

    Without this, a test that creates a real ChatOllama instance leaves it
    cached, and the next test's mock of get_llm() or ChatOllama may be
    bypassed. Requirement QRY-07.
    """
    _query_module._llm = None
    yield
    _query_module._llm = None


@pytest.fixture
def ephemeral_chroma():
    """
    Return a chromadb.EphemeralClient for tests that need a real ChromaDB
    instance without any filesystem persistence or external service.
    """
    import chromadb
    client = chromadb.EphemeralClient()
    yield client
    # EphemeralClient holds no persistent state — no cleanup needed
```

### tests/integration/conftest.py

```python
"""
Integration test configuration.

All integration tests require live ChromaDB (port 8001) and Ollama (port 11435)
from docker-compose.test.yml. Tests are skipped automatically when services
are not reachable — this allows the integration tier to be collected without
errors on developer machines that don't have Docker running.
"""
import httpx
import pytest


def _is_reachable(url: str, timeout: float = 2.0) -> bool:
    try:
        httpx.get(url, timeout=timeout)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def chroma_url():
    return "http://localhost:8001"


@pytest.fixture(scope="session")
def ollama_url():
    return "http://localhost:11435"


@pytest.fixture(scope="session")
def services_available(chroma_url, ollama_url):
    chroma_ok = _is_reachable(f"{chroma_url}/api/v1/heartbeat")
    ollama_ok = _is_reachable(f"{ollama_url}/api/tags")
    return chroma_ok and ollama_ok


@pytest.fixture(autouse=True)
def require_services(services_available):
    """Skip every integration test when Docker services are not running."""
    if not services_available:
        pytest.skip(
            "Integration services unavailable — start with: "
            "docker compose -f docker-compose.test.yml up -d"
        )
```

### tests/e2e/conftest.py

```python
"""
E2E test configuration.

E2E tests require the full application stack to be running and accessible.
Set E2E_BASE_URL env var to override the default localhost target.
Tests skip automatically when the stack is unreachable.
"""
import os
import httpx
import pytest


@pytest.fixture(scope="session")
def base_url():
    return os.getenv("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_key():
    return os.getenv("API_KEY", "test-api-key-for-pytest")


@pytest.fixture(scope="session", autouse=True)
def require_stack(base_url):
    """Skip all e2e tests when the application stack is not reachable."""
    try:
        httpx.get(f"{base_url}/health", timeout=3.0)
    except Exception:
        pytest.skip(f"E2E stack not available at {base_url}")


@pytest.fixture(scope="session")
def e2e_client(base_url, api_key):
    """Synchronous HTTPX client pre-configured for E2E calls."""
    with httpx.Client(
        base_url=base_url,
        headers={"X-API-Key": api_key},
        timeout=30.0,
    ) as client:
        yield client
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var injection at collection time | Custom pytest plugin or session fixture | `pytest-env` (`[tool.pytest.ini_options] env`) | Plugins run before conftest.py in the load order in some configurations |
| Async test support | `asyncio.run()` wrappers | pytest-asyncio `asyncio_mode=auto` | Auto mode eliminates per-test `@pytest.mark.asyncio` decoration; already locked in INFRA-01 |
| httpx mocking | `unittest.mock.patch` on httpx internals | `respx` | respx understands httpx's transport layer; patch-based mocks break on httpx internal refactors |
| Coverage branch tracking | Manual call-graph analysis | `[tool.coverage.run] branch=true` + concurrency config | `greenlet` concurrency needed for gevent/async coverage accuracy |
| Test isolation for singletons | Module reload hacks | autouse reset fixture (see unit/conftest.py) | `importlib.reload` has side effects on all importers of the module |

---

## Common Pitfalls

### Pitfall 1: API_KEY RuntimeError at Collection Time

**What goes wrong:** `pytest tests/` raises `RuntimeError: API_KEY is required and must not be empty.` immediately, collecting 0 tests.

**Root cause:** `src/utils/env.py` line 34-35 executes `raise RuntimeError(...)` at module scope when `API_KEY` is falsy. Any import of any `src.*` module during collection triggers it. [VERIFIED: src/utils/env.py lines 29, 34-35]

**How to avoid:** Set `os.environ["API_KEY"]` at the TOP of `tests/conftest.py` before any import from `src.*`. Also add to `[tool.pytest.ini_options] env` in pyproject.toml as a second layer.

**Warning signs:** `RuntimeError` in pytest output before any test ID is printed; `ERRORS` section appearing before `short test summary info`.

### Pitfall 2: mlflow.autolog Corrupts httpx Transport

**What goes wrong:** `respx` mocks are installed but requests still reach the network; `ConnectionRefusedError` on ollama/mlflow URLs during unit tests.

**Root cause:** `mlflow.autolog()` (called in `src/tracking/setup.py`) monkey-patches httpx's `AsyncClient` and `Client` to inject MLflow tracking. This patch overwrites the transport mechanism that respx hooks into. If autolog runs first, respx's router is never consulted. [VERIFIED: src/tracking/setup.py reads; mlflow.autolog behavior is [ASSUMED] based on mlflow>=3.0 httpx integration pattern]

**How to avoid:** Patch `src.tracking.setup.mlflow_autolog` at module level in root `tests/conftest.py` BEFORE importing `src.main`.

**Warning signs:** Unit tests that use respx raise `httpx.ConnectError` to localhost; test output shows real network addresses in error messages.

### Pitfall 3: _llm Singleton Leaks Between Tests

**What goes wrong:** Test A mocks `get_llm()` successfully; Test B (which does NOT mock it) receives the mock left behind by Test A and fails in unexpected ways — or vice versa, Test B creates a real `ChatOllama` that persists into Test C.

**Root cause:** `_llm` is a module-level global in `src/services/query.py`. Python module globals persist for the entire process lifetime. [VERIFIED: src/services/query.py line 20]

**How to avoid:** `autouse=True` fixture in `tests/unit/conftest.py` that sets `query_module._llm = None` before and after every test. (This is requirement QRY-07.)

**Warning signs:** Tests pass in isolation (`pytest tests/unit/test_query.py::test_foo`) but fail when the full suite runs; test ordering affects outcomes.

### Pitfall 4: Missing __init__.py Causes Module Name Collisions

**What goes wrong:** pytest can't distinguish `tests/unit/test_query.py` from `tests/integration/test_query.py`; one silently overrides the other.

**Root cause:** Without `__init__.py`, pytest uses the filename as the module name. Two files with the same name in different directories collide in `sys.modules`.

**How to avoid:** Create `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/e2e/__init__.py` (even empty).

**Warning signs:** `ImportError: import file mismatch` or unexpected test counts when running the full suite.

### Pitfall 5: requires-python Mismatch

**What goes wrong:** `uv sync` fails or installs the wrong resolver; runtime error on Python 3.11 (the current environment) even though pyproject.toml says `>=3.13.8`.

**Root cause:** The current Docker/dev environment runs Python 3.11.2 but pyproject.toml declares `requires-python = ">=3.13.8"`. This is a pre-existing inconsistency in the project. [VERIFIED: `python3 --version` output = 3.11.2; pyproject.toml line 5]

**How to avoid:** Phase 1 should NOT change `requires-python`. Document the discrepancy. Tests should run against whatever Python is available; if uv enforces the constraint, the plan should note that running `uv run pytest` may fail on the dev machine and `python -m pytest` (using the ambient interpreter) should be used as a fallback.

**Warning signs:** `uv sync` prints `requires Python >=3.13.8 but the current Python is 3.11.2`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | YES | 3.11.2 (ambient) | — |
| pytest | Test runner | YES (in uv.lock) | 9.0.2 | — |
| pytest-asyncio | INFRA-01 | YES (in uv.lock) | 1.3.0 | — |
| pytest-cov | INFRA-04 | NO — not in uv.lock | — | Must add |
| pytest-env | INFRA-01 | NO — not in uv.lock | — | Must add |
| pytest-mock | Phase 2+ | NO — not in uv.lock | — | Must add |
| pytest-timeout | INFRA-01 | NO — not in uv.lock | — | Must add |
| respx | Phase 2+ | NO — not in uv.lock | — | Must add |
| chromadb (EphemeralClient) | unit/conftest.py | ASSUMED present (langchain-chroma pulls it) | — | [ASSUMED] |
| Docker | Integration tier | Not checked (Phase 1 scope is config only) | — | N/A Phase 1 |

**Missing dependencies with no fallback (blocking for Phase 1):**
- pytest-cov, pytest-env, pytest-mock, pytest-timeout, respx — must be added via `uv add --optional dev` or manual pyproject.toml edit + `uv sync`

**Python version discrepancy (pre-existing, not introduced by Phase 1):**
- `requires-python = ">=3.13.8"` in pyproject.toml but Python 3.11.2 is the ambient interpreter. `python -m pytest` will work; `uv run pytest` may error. Plan should use `python -m pytest` or note this limitation.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — does not exist yet, Wave 0 creates it |
| Quick run command | `python -m pytest tests/ -x -q --no-header` |
| Full suite command | `python -m pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `pytest --co -q` completes without RuntimeError; asyncio_mode=auto visible in config | smoke | `python -m pytest --co -q 2>&1 \| grep -v "RuntimeError"` | No — Wave 0 |
| INFRA-02 | All 5 packages importable after `uv sync --extra dev` | smoke | `python -c "import pytest_cov, pytest_env, pytest_mock, pytest_timeout, respx"` | No — Wave 0 |
| INFRA-03 | `pytest --co -q` collects 0 tests (no test files yet) with no errors | smoke | `python -m pytest --co -q` returns exit 5 (no tests) not exit 1 (error) | No — Wave 0 |
| INFRA-04 | `pytest --cov=src --cov-fail-under=80` configuration is parseable | smoke | `python -m pytest --co --cov=src -q` starts without config error | No — Wave 0 |

**Note:** Phase 1 has no test functions to write — it IS the infrastructure. Validation is smoke-testing the configuration itself (no errors at collection, imports work, config is parsed). The 80% coverage gate only becomes meaningful when Phase 2+ adds real test functions.

### Sampling Rate

- **Per task commit:** `python -m pytest --co -q` (collection smoke — verifies no RuntimeError)
- **Per wave merge:** `python -m pytest --co -q && python -c "import pytest_cov, pytest_env, pytest_mock, pytest_timeout, respx; print('all imports OK')"` 
- **Phase gate:** Collection clean + all 5 packages importable + config parses without errors

### Wave 0 Gaps

- [ ] `tests/__init__.py` — needed for package discovery
- [ ] `tests/conftest.py` — root conftest (API_KEY guard + mlflow stub)
- [ ] `tests/unit/__init__.py`
- [ ] `tests/unit/conftest.py` — _llm reset autouse fixture
- [ ] `tests/integration/__init__.py`
- [ ] `tests/integration/conftest.py` — service skip logic
- [ ] `tests/e2e/__init__.py`
- [ ] `tests/e2e/conftest.py` — stack skip logic
- [ ] `pyproject.toml` additions: `[project.optional-dependencies]`, `[tool.pytest.ini_options]`, `[tool.coverage.*]`
- [ ] `uv sync --extra dev` to install the 5 new packages

---

## Security Domain

Security enforcement applies, but Phase 1 is configuration-only infrastructure with no application logic changes.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No — test infra only | N/A |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | No | N/A |
| V6 Cryptography | No | N/A |

**Security note for test config:** The `API_KEY=test-api-key-for-pytest` value injected via pytest-env and set in conftest.py must NEVER be the same value as the production API_KEY. Using a clearly fake sentinel value (as shown) is correct. Do not use `.env` file values in test config. [ASSUMED: no CLAUDE.md security directives found — CLAUDE.md not present at /workspace/CLAUDE.md]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `mlflow.autolog()` patches httpx transport globally, breaking respx interception | Common Pitfalls §2 | If wrong, the module-level patcher is harmless extra code; no test breakage |
| A2 | `chromadb.EphemeralClient()` is importable (pulled as transitive dep of langchain-chroma) | unit/conftest.py | If not available, unit tests needing real Chroma will fail — use `mocker.MagicMock()` instead |
| A3 | pytest-env >=1.1 sets env vars before conftest.py module-level code in all configurations | pyproject.toml changes | Belt-and-suspenders `os.environ.setdefault` in conftest.py is the safe fallback |
| A4 | Minimum version specifiers (>=6.0, >=1.1, etc.) from REQUIREMENTS.md are current — exact latest PyPI versions not verified (network unavailable) | Standard Stack | If specifiers resolve to incompatible versions, `uv sync` will report conflicts |
| A5 | Python version discrepancy (3.11.2 ambient vs >=3.13.8 declared) will not block `python -m pytest` but may block `uv run pytest` | Environment Availability | If uv enforces the constraint strictly, all uv-based test commands fail; workaround is to use python -m pytest directly |

---

## Open Questions

1. **uv vs pip for dev dependency installation**
   - What we know: pyproject.toml uses uv (uv.lock present), but no `[project.optional-dependencies]` group exists yet
   - What's unclear: Whether the project's CI uses `uv sync --extra dev` or a separate `pip install -r requirements-dev.txt` pattern
   - Recommendation: Add `[project.optional-dependencies] dev = [...]` to pyproject.toml; `uv sync --extra dev` is the canonical uv approach

2. **Python 3.11 vs 3.13 discrepancy**
   - What we know: `requires-python = ">=3.13.8"` but ambient Python is 3.11.2
   - What's unclear: Whether this is intentional (production uses 3.13, dev uses 3.11) or a copy-paste error
   - Recommendation: Do NOT change requires-python in Phase 1. Document the discrepancy. Use `python -m pytest` in all Phase 1 task commands (bypasses uv Python resolution).

---

## Sources

### Primary (HIGH confidence — verified by direct file reading)
- `/workspace/src/utils/env.py` — API_KEY RuntimeError at module scope (lines 29, 34-35)
- `/workspace/src/services/query.py` — `_llm` singleton pattern (lines 20-35)
- `/workspace/src/tracking/setup.py` — mlflow.autolog() call path
- `/workspace/pyproject.toml` — current state, no test config, no dev deps
- `/workspace/uv.lock` — pytest 9.0.2 and pytest-asyncio 1.3.0 already present; pytest-cov/env/mock/timeout/respx absent

### Secondary (MEDIUM confidence)
- pytest-asyncio 1.3.0 `asyncio_mode=auto` and `asyncio_default_fixture_loop_scope` setting names — consistent with pytest-asyncio docs pattern [ASSUMED current for 1.3.0]
- pytest-env `[tool.pytest.ini_options] env` table format — consistent with official README pattern [ASSUMED]

### Tertiary (LOW confidence — training knowledge)
- mlflow.autolog httpx patching behavior — widely documented in mlflow issue tracker [ASSUMED: not verified against mlflow 3.10.1 release notes]

---

## Metadata

**Confidence breakdown:**
- pyproject.toml changes: HIGH — current file verified, additions derived from locked requirements
- conftest.py content: HIGH — derived from verified source code analysis of env.py and query.py
- Package versions: MEDIUM — uv.lock confirms what's present; exact latest PyPI versions not verifiable (no network)
- mlflow/httpx interaction: LOW-MEDIUM — pattern is well-known but not verified against mlflow 3.10.1 specifically

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable ecosystem — pytest/coverage config rarely changes)
