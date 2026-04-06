# Tasks: Project Documentation

**Input**: Design documents from `/specs/001-add-project-docs/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, contracts/docs-structure.md ✓

**Organization**: Tasks grouped by user story to enable independent delivery of each documentation section.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to
- All content decisions are pre-resolved in `research.md` and `contracts/docs-structure.md`

---

## Phase 1: Setup

**Purpose**: Create the `docs/` directory structure before any content is written.

- [x] T001 Create `docs/` directory at repository root

---

## Phase 2: User Story 1 — Quick Start Guide (Priority: P1) 🎯 MVP

**Goal**: Revise `README.md` for accuracy and link it to the new `./docs/` files.

**Independent Test**: Follow the README from a clean environment — services start, ingest works, query returns an answer. No broken links.

### Implementation

- [x] T002 [US1] Fix inaccuracy in `README.md` — correct `OLLAMA_MODEL` default from `qwen3.5:9b` to `llama3.2` in the Environment Variables table
- [x] T003 [US1] Fix inaccuracy in `README.md` — correct `OLLAMA_JUDGE_MODEL` default from `llama3.2` to `mistral` in the Environment Variables table
- [x] T004 [US1] Fix inaccuracy in `README.md` — remove `retrieval_groundedness` from the MLflow Dashboard scorers list (3 scorers only: answer relevancy, hallucination, safety)
- [x] T005 [US1] Fix inaccuracy in `README.md` — correct scorer list in the How It Works → MLflow Logging section to match `evaluate.py` (3 scorers: `AnswerRelevancy`, `Hallucination`, `Safety`; no `RetrievalGroundedness`)
- [x] T006 [US1] Fix inaccuracy in `README.md` — document `CHROMA_PERSIST_DIR` correctly for Docker Compose (`/chroma/data`) and local runs (`/tmp/chroma`)
- [x] T007 [US1] ~~Add `## Documentation` section to `README.md`~~ — skipped per FR-012 (no new content in README)

**Checkpoint**: README is accurate and User Story 1 is independently verifiable.

---

## Phase 3: User Story 2 — API Endpoint Documentation (Priority: P2)

**Goal**: Create `docs/api.md` with the full contract for all three endpoints.

**Independent Test**: An API consumer reads `docs/api.md` and successfully calls all three endpoints using only the curl examples provided, with correct request format and expected response structure.

### Implementation

- [x] T008 [US2] Create `docs/api.md` with document header and `## Base URL` section (`http://localhost:8000`; note about port remapping linking to `docs/configuration.md`)
- [x] T009 [US2] Add `## POST /ingest` section to `docs/api.md` — description, accepted file types (`.pdf`, `.txt` only), multipart/form-data request format, success response schema (`status`, `chunks_stored`, `filename`), HTTP 400 error for unsupported types, curl example
- [x] T010 [US2] Add `## POST /query` section to `docs/api.md` — description, JSON request schema (`question`: string required min 1 char; `top_k`: int default 4 min 1), response schema (`answer`: string; `sources`: array of strings), HTTP 404 error when no documents ingested, HTTP 500 on pipeline error, note that the LLM always responds in Brazilian Portuguese (pt-br) regardless of input language, curl example
- [x] T011 [US2] Add `## GET /health` section to `docs/api.md` — description, response schema (`status`, `chromadb`, `ollama` — each `"ok"` or `"error"`), note that `status` is always `"ok"` regardless of dependency health, curl example

**Checkpoint**: `docs/api.md` complete. An API consumer can integrate without reading any source code.

---

## Phase 4: User Story 3 — Architecture Documentation (Priority: P3)

**Goal**: Create `docs/architecture.md` covering components, both pipelines, evaluation, and persistence.

**Independent Test**: A contributor reads `docs/architecture.md` and can identify where to change the LLM model and where to change the chunk size without opening source code.

### Implementation

- [x] T012 [US3] Create `docs/architecture.md` with document header and `## Components` section — table listing FastAPI (port 8000, embedded ChromaDB), Ollama (port 11434), MLflow (port 5000), with the role of each
- [x] T013 [US3] Add `## Startup Sequence` section to `docs/architecture.md` — `ollama-pull-llama-*` init service pulls the 3 Ollama models (`OLLAMA_MODEL`, `OLLAMA_JUDGE_MODEL`, `OLLAMA_EMBED_MODEL`) before API start; first startup takes longer due to model download; subsequent startups reuse cached models in `ollama_data` volume
- [x] T014 [US3] Add `## Ingestion Pipeline` section to `docs/architecture.md` — step-by-step: file upload (multipart) → file type validation (.pdf/.txt, HTTP 400 otherwise) → text extraction (PyPDFLoader for PDF, TextLoader for TXT) → chunking (RecursiveCharacterTextSplitter, chunk_size=4000, chunk_overlap=20) → embedding (OLLAMA_EMBED_MODEL) → storage in ChromaDB collection `ragscope_collection`
- [x] T015 [US3] Add `## Query Pipeline` section to `docs/architecture.md` — step-by-step: question → embedding (OLLAMA_EMBED_MODEL) → cosine similarity search in ChromaDB (top-k chunks, default k=4) → context assembly → LLM generation (OLLAMA_MODEL, temperature=0) → LLM-as-judge evaluation → response returned with answer and source chunks
- [x] T016 [US3] Add `## Evaluation` section to `docs/architecture.md` — 3 scorers: `AnswerRelevancy`, `Hallucination`, `Safety`; judge model is `OLLAMA_JUDGE_MODEL`; evaluation runs only if sources were found; evaluation failure is non-fatal (answer is still returned, warning is logged); results appear in MLflow UI under experiment `ragscope`, GenAI section
- [x] T017 [US3] Add `## Data Persistence` section to `docs/architecture.md` — ChromaDB data persists to `chroma_data` Docker named volume; new ingests accumulate (data is not replaced); to reset ChromaDB only: `docker volume rm <project>_chroma_data`; to reset everything: `docker compose down -v`
- [x] T018 [US3] Add `## Project Structure` section to `docs/architecture.md` — directory tree of `src/` with a one-line description for each file: `main.py`, `ingest.py`, `query.py`, `evaluate.py`, `health.py`, `models.py`, `tracking/setup.py`, `utils/env.py`, `utils/log_manager.py`

**Checkpoint**: `docs/architecture.md` complete. A maintainer can navigate the codebase using only this document.

---

## Phase 5: User Story 4 — Configuration and Models Documentation (Priority: P3)

**Goal**: Create `docs/configuration.md` covering all environment variables, models, Docker profiles, ports, and data management.

**Independent Test**: An operator reads `docs/configuration.md` and successfully switches the generation model and activates GPU profile without consulting any other file.

### Implementation

- [x] T019 [P] [US4] Create `docs/configuration.md` with document header and `## Environment Variables` section — full table with Variable, Default, and Description for all 7 variables: `COMPOSE_PROFILES` (`cpu`), `OLLAMA_MODEL` (`llama3.2`), `OLLAMA_JUDGE_MODEL` (`mistral`), `OLLAMA_EMBED_MODEL` (`nomic-embed-text`), `MLFLOW_TRACKING_URI` (`http://mlflow:5000`), `OLLAMA_BASE_URL` (`http://ollama:11434`), `CHROMA_PERSIST_DIR` (`/chroma/data` in Docker Compose, `/tmp/chroma` for local runs)
- [x] T020 [US4] Add `## Hardware Profiles` section to `docs/configuration.md` — table of `COMPOSE_PROFILES` values (`cpu`, `gpu-nvidia`, `gpu-amd`) with system requirements for each; how to set in `.env`; startup command (`docker compose up`); warning that any other value (including blank) results in no Ollama service starting
- [x] T021 [US4] Add `## Switching Models` section to `docs/configuration.md` — how to change generation, judge, and embedding models via `.env` variables; note that changed models are auto-pulled on next startup; recommend compatible model sizes for available VRAM/RAM
- [x] T022 [US4] Add `## Port Remapping` section to `docs/configuration.md` — default ports (API: 8000, MLflow: 5000, Ollama: 11434); how to remap via Docker Compose `ports:` override syntax; example showing remapping API to port 9000
- [x] T023 [US4] Add `## Data Management` section to `docs/configuration.md` — explain that ChromaDB data accumulates across ingests and restarts; command to reset ChromaDB volume only; command to reset all volumes (ChromaDB + Ollama model cache); warning that full reset requires re-downloading all models on next startup
- [x] T024 [US4] Add `## OS Requirements` section to `docs/configuration.md` — Linux and macOS supported natively via Docker Desktop or Docker Engine; Windows users must use WSL2; brief note with link to Microsoft WSL2 installation documentation

**Checkpoint**: `docs/configuration.md` complete. All 4 user stories independently verifiable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final accuracy check and consistency review across all files.

- [x] T025 [P] Cross-verify all values in `docs/api.md` against `src/models.py` and `src/ingest.py` — confirm field names, types, defaults, and error codes are exact
- [x] T026 [P] Cross-verify all values in `docs/configuration.md` against `.env.example` and `src/utils/env.py` — confirm all defaults match source of truth
- [x] T027 [P] Verify all links in `README.md` `## Documentation` section resolve to the correct `docs/` files — skipped (T007 not added per FR-012)
- [x] T028 Review all three `docs/` files for American English (en-US) spelling and consistent terminology (e.g., "vector store" not "vectorstore", "evaluation" not "scoring")

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US1)**: Depends on Phase 1 (docs/ directory must exist for links to be valid)
- **Phase 3 (US2)**: Depends on Phase 1 only — can start after T001
- **Phase 4 (US3)**: Depends on Phase 1 only — can start after T001
- **Phase 5 (US4)**: Depends on Phase 1 only — can start after T001
- **Phase 6 (Polish)**: Depends on all phases 2–5 being complete

### User Story Dependencies

- **US1 (P1)**: Start after Phase 1 — no dependency on other stories
- **US2 (P2)**: Start after Phase 1 — no dependency on other stories
- **US3 (P3)**: Start after Phase 1 — no dependency on other stories
- **US4 (P3)**: Start after Phase 1 — no dependency on other stories
- **US2, US3, US4 can all be worked in parallel** once T001 is done

### Within Each User Story

- Tasks within a story are sequential (each section builds the file incrementally)
- T019 is marked [P] because `docs/configuration.md` file creation has no dependency on US3 tasks

### Parallel Opportunities

- After T001: US2 (T008–T011), US3 (T012–T018), US4 (T019–T024) all start in parallel
- Polish tasks T025, T026, T027 are all parallelizable

---

## Parallel Example: After Phase 1

```bash
# All three docs files can be written simultaneously:
Task: "Create docs/api.md ..." (T008)
Task: "Create docs/architecture.md ..." (T012)
Task: "Create docs/configuration.md ..." (T019)

# While also:
Task: "Fix README.md inaccuracies ..." (T002–T006)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: US1 — README revision (T002–T007)
3. **STOP and VALIDATE**: README is accurate and links resolve
4. README already provides enough for a user to start the project

### Incremental Delivery

1. T001 → docs/ directory ready
2. T002–T007 → README revised, links added (US1 ✓)
3. T008–T011 → API reference complete (US2 ✓)
4. T012–T018 → Architecture documented (US3 ✓)
5. T019–T024 → Configuration documented (US4 ✓)
6. T025–T028 → Polish complete

### Parallel Strategy (single developer)

1. T001 first (30 seconds)
2. T002–T007: README fixes (can batch all corrections in one edit session)
3. T008–T011, T012–T018, T019–T024: Write all three docs files (can interleave by section)
4. T025–T028: Final cross-check pass

---

## Notes

- No code changes — all tasks produce Markdown files only
- Content for each task is fully specified in `contracts/docs-structure.md` and `research.md`
- Source of truth for all values: `src/` code files and `.env.example` (not existing README.md)
- Key accuracy note: LLM responds in Brazilian Portuguese — must appear in `docs/api.md` POST /query section
- Key accuracy note: 3 scorers only (not 4) — `AnswerRelevancy`, `Hallucination`, `Safety`
