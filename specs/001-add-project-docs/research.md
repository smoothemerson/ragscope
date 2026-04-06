# Research: Project Documentation

**Branch**: `001-add-project-docs` | **Date**: 2026-03-11
**Purpose**: Inventory current project behavior and identify inaccuracies in existing README before writing docs.

---

## Findings

### 1. Existing Documentation State

**Decision**: README.md already contains substantial content — architecture diagram, quickstart, example usage, env vars, and "How It Works" — but has inaccuracies that must be corrected during the revision pass.

**What exists in README.md:**
- Architecture ASCII diagram (accurate)
- Prerequisites section (accurate)
- Quickstart steps (accurate, includes Docker profile warning)
- Example usage with `curl` for all three endpoints (accurate)
- MLflow Dashboard section (partially inaccurate — see inaccuracies below)
- Environment Variables table (inaccurate defaults)
- How It Works section (partially inaccurate)

---

### 2. README Inaccuracies Found (must be corrected, not added)

| Location | README says | Source of truth (code) | Action |
|----------|------------|------------------------|--------|
| Env Vars table — `OLLAMA_MODEL` default | `qwen3.5:9b` | `.env.example`: `llama3.2` | Correct to `llama3.2` |
| Env Vars table — `OLLAMA_JUDGE_MODEL` default | `llama3.2` | `.env.example`: `mistral` | Correct to `mistral` |
| MLflow Dashboard — scorers list | `retrieval_groundedness`, `answer_relevancy`, `hallucination`, `safety` (4 scorers) | `evaluate.py`: `AnswerRelevancy`, `Hallucination`, `Safety` (3 scorers only) | Remove `retrieval_groundedness` |
| How It Works — MLflow Logging | "MLflow GenAI `evaluate()` runs scorers (`RetrievalGroundedness`, `AnswerRelevancy`, `Hallucination`, `Safety`)" | `evaluate.py`: 3 scorers only (no `RetrievalGroundedness`) | Correct to 3 scorers |
| `CHROMA_PERSIST_DIR` | Listed in env vars table with default `/chroma/data` | `src/utils/env.py` default is `/tmp/chroma`; Docker Compose pins it to `/chroma/data` for container runs | Correct docs to show compose value and local default |

---

### 3. Behavior Facts for Documentation

**Startup / Model Pull (`docker-compose.yml`)**
- During `docker compose up`, an `ollama-pull-llama-*` init service runs `ollama pull` for `OLLAMA_MODEL`, `OLLAMA_JUDGE_MODEL`, and `OLLAMA_EMBED_MODEL`
- `api` depends on the init service and starts after pull completion
- First startup takes longer due to model downloads
- Subsequent startups reuse cached models in the `ollama_data` volume

**Ingestion Pipeline (`ingest.py`)**
- Accepted file types: `.pdf` and `.txt` only (enforced with HTTP 400 for others)
- PDF: loaded with `PyPDFLoader.load_and_split()`
- TXT: loaded with `TextLoader`
- Chunking: `RecursiveCharacterTextSplitter`, chunk_size=4000, chunk_overlap=20
- Stored in ChromaDB collection `ragscope_collection` (embedded, persisted to `chroma_data` volume)
- Response: `{"status": "ok", "chunks_stored": <int>, "filename": "<str>"}`
- Error response (unsupported type): HTTP 400

**Query Pipeline (`query.py`)**
- Request fields: `question` (string, required, min 1 char), `top_k` (int, default 4, min 1)
- Embeds question with `OLLAMA_EMBED_MODEL`, retrieves top-k chunks by cosine similarity
- Builds context from retrieved chunks, runs through `PromptTemplate | ChatOllama` sequence
- **LLM response language**: The prompt instructs the model to always respond in Brazilian Portuguese (pt-br), regardless of the question language
- LLM temperature: 0 (deterministic output)
- Evaluation only runs if sources are found (skipped on empty retrieval)
- Error: HTTP 404 if no documents ingested; HTTP 500 on pipeline failure
- Response: `{"answer": "<str>", "sources": ["<chunk_text>", ...]}`

**Evaluation (`evaluate.py`)**
- Runs 3 MLflow GenAI scorers (via DeepEval): `AnswerRelevancy`, `Hallucination`, `Safety`
- Judge model: `OLLAMA_JUDGE_MODEL` (default: `mistral`)
- Evaluation failures are non-fatal — the answer is still returned; a warning is logged
- Results visible in MLflow UI under experiment `ragscope`, GenAI section

**Health Check (`health.py`)**
- Checks Ollama: GET `{OLLAMA_BASE_URL}/api/tags`, timeout 5s
- Checks ChromaDB: instantiates a `Chroma` instance and calls `._collection.count()`
- Response: `{"status": "ok", "chromadb": "ok"|"error", "ollama": "ok"|"error"}`
- Note: `status` field is always `"ok"` regardless of dependency health

**Data Persistence**
- ChromaDB persists to `chroma_data` Docker named volume
- New ingests accumulate in the existing collection — data is not replaced
- To reset: `docker compose down -v` removes all volumes (ChromaDB + Ollama models)
- To reset only ChromaDB: `docker volume rm <project>_chroma_data`

**Ports**
- API (FastAPI): `8000`
- MLflow UI: `5000`
- Ollama: `11434`
- Port remapping: override via Docker Compose port configuration (no env var for port remapping)

**Environment Variables** (source of truth: `.env.example` + `src/utils/env.py`)

| Variable | Default | User-overridable | Description |
|----------|---------|-----------------|-------------|
| `COMPOSE_PROFILES` | `cpu` | Yes (.env) | Docker hardware profile: `cpu`, `gpu-nvidia`, `gpu-amd` |
| `OLLAMA_MODEL` | `llama3.2` | Yes (.env) | Model for answer generation |
| `OLLAMA_JUDGE_MODEL` | `mistral` | Yes (.env) | Model for LLM-as-judge evaluation |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Yes (.env) | Model for text embeddings |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | Yes (.env) | MLflow tracking server URI |
| `CHROMA_PERSIST_DIR` | `/chroma/data` in Docker Compose (`/tmp/chroma` for local runs) | Partially | ChromaDB storage path for embedded Chroma data |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Not in .env.example | Ollama service URL — set via Docker networking |

---

### 4. Documentation Structure Decision

**Decision**: Three files under `./docs/`, each covering a distinct audience concern.

**Rationale**: Separating by concern (API, architecture, configuration) allows readers to go directly to what they need without scrolling through a monolithic file. README.md links to each.

| File | Primary audience | Content |
|------|-----------------|---------|
| `docs/api.md` | API consumers, integrators | Endpoint contracts, request/response schemas, error codes, curl examples |
| `docs/architecture.md` | Contributors, maintainers | Component overview, ingestion pipeline, query pipeline, data flow, startup sequence |
| `docs/configuration.md` | Operators | Env vars table, model switching, Docker profiles, port remapping, data persistence & reset |

**Alternatives considered**: Single `docs/reference.md` — rejected because it would be too long and mix distinct audiences.

---

### 5. README Revision Scope

**Decision**: Revise for accuracy only — fix identified inaccuracies without adding new README sections.

**Rationale**: The README is already well-structured and concise. The revision should keep structure stable and focus on correcting factual inaccuracies.
