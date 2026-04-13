# TODO Checklist — RAG API with MLflow Evaluation Dashboard

Derived from unchecked acceptance criteria in `prd-rag-api.md`, plus CI/CD and MLflow improvements.

---

## Runtime Verification (US-001)

- [ ] `docker compose up` starts all services without errors
- [ ] MLflow UI is accessible at `http://localhost:5000`
- [ ] FastAPI docs are accessible at `http://localhost:8000/docs`

## Linting

- [x] US-002: Linting passes (`ruff check`) for ingestion endpoint code
- [x] US-003: Linting passes (`ruff check`) for query endpoint code
- [x] US-004: Linting passes (`ruff check`) for MLflow logging code
- [x] US-005: Linting passes (`ruff check`) for LLM-as-judge evaluation code
- [x] US-006: Linting passes (`ruff check`) for health check endpoint code

## CI — GitHub Actions

- [x] Add `.github/workflows/lint.yml` with `ruff check` on push and PR
- [x] CI workflow runs on Python 3.11+ and installs dependencies from `requirements.txt`
- [x] CI pipeline passes on `main` branch

## Dependabot

- [x] Add `.github/dependabot.yml` for `pip` ecosystem (weekly schedule)
- [x] Add `.github/dependabot.yml` entry for `github-actions` ecosystem (weekly schedule)
- [x] Add `.github/dependabot.yml` entry for `docker` ecosystem (weekly schedule)

## MLflow Verification

- [ ] Verify MLflow experiment `ragscope` is created on startup and visible in the UI
- [ ] Run a `/query` request and confirm GenAI evaluation outputs (`AnswerRelevancy`, `Hallucination`, `Safety`) are recorded
- [ ] Confirm query tracking works with current `mlflow.autolog()` setup
