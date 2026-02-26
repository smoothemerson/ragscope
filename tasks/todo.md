# TODO Checklist — RAG API with MLflow Evaluation Dashboard

Derived from unchecked acceptance criteria in `prd-rag-api.md`, plus CI/CD and MLflow improvements.

---

## Runtime Verification (US-001)

- [ ] `docker compose up` starts all services without errors
- [ ] MLflow UI is accessible at `http://localhost:5000`
- [ ] FastAPI docs are accessible at `http://localhost:8000/docs`

## Linting

- [ ] US-002: Linting passes (`ruff check`) for ingestion endpoint code
- [ ] US-003: Linting passes (`ruff check`) for query endpoint code
- [ ] US-004: Linting passes (`ruff check`) for MLflow logging code
- [ ] US-005: Linting passes (`ruff check`) for LLM-as-judge evaluation code
- [ ] US-006: Linting passes (`ruff check`) for health check endpoint code

## CI — GitHub Actions

- [ ] Add `.github/workflows/lint.yml` with `ruff check` on push and PR
- [ ] CI workflow runs on Python 3.11+ and installs dependencies from `requirements.txt`
- [ ] CI pipeline passes on `main` branch

## Dependabot

- [ ] Add `.github/dependabot.yml` for `pip` ecosystem (weekly schedule)
- [ ] Add `.github/dependabot.yml` entry for `github-actions` ecosystem (weekly schedule)
- [ ] Add `.github/dependabot.yml` entry for `docker` ecosystem (weekly schedule)

## MLflow Experiment Migration

- [ ] Move MLflow experiment `rag-evaluation` from **ML Runs** section to **GenAI** section in the MLflow UI
- [ ] Update experiment tracking code to use MLflow GenAI-compatible logging (e.g., `mlflow.log_trace` or GenAI experiment type)
- [ ] Verify experiment appears under GenAI section in MLflow UI after migration
