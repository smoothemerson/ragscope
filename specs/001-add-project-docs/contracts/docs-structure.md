# Documentation Contract: File Structure & Content Map

**Branch**: `001-add-project-docs` | **Date**: 2026-03-11
**Purpose**: Define the exact files to be created/modified, their headings, and the content each section must contain. This is the authoritative contract for implementation.

---

## Files to Create

### `docs/api.md` — API Reference

| Section | Required Content |
|---------|-----------------|
| `# API Reference` | One-line summary of the API purpose |
| `## Base URL` | `http://localhost:8000` with note about port remapping |
| `## POST /ingest` | Description, accepted file types (`.pdf`, `.txt`), multipart/form-data format, success response schema, error responses (400 unsupported type), curl example |
| `## POST /query` | Description, JSON request schema (`question`: string required; `top_k`: int default 4 min 1), response schema (`answer`: string; `sources`: array of strings), error responses (404 no docs, 500 pipeline error), curl example, note on response language (Brazilian Portuguese) |
| `## GET /health` | Description, response schema (`status`, `chromadb`, `ollama` — each `"ok"` or `"error"`), note that `status` is always `"ok"`, curl example |

---

### `docs/architecture.md` — System Architecture

| Section | Required Content |
|---------|-----------------|
| `# Architecture` | Brief system description (offline RAG + evaluation) |
| `## Components` | Table or list: FastAPI (port 8000), ChromaDB embedded, Ollama (port 11434), MLflow (port 5000) — with role of each |
| `## Startup Sequence` | Model pull behavior on startup: `ollama-pull-llama-*` init service pulls 3 models sequentially before API starts; first startup longer due to download |
| `## Ingestion Pipeline` | Step-by-step: upload → file type validation → extraction (PyPDF/TextLoader) → chunking (4000 chars, 20 overlap) → embedding (OLLAMA_EMBED_MODEL) → storage (ChromaDB `ragscope_collection`) |
| `## Query Pipeline` | Step-by-step: question → embedding → cosine similarity retrieval (top-k) → context assembly → LLM generation (OLLAMA_MODEL, temperature=0) → evaluation → response |
| `## Evaluation` | 3 scorers (AnswerRelevancy, Hallucination, Safety), judge model (OLLAMA_JUDGE_MODEL), non-fatal (answer returned even if evaluation fails), results in MLflow |
| `## Data Persistence` | ChromaDB persists to `chroma_data` volume; new ingests accumulate; how to reset (volume removal commands) |
| `## Project Structure` | Directory tree of `src/` with one-line description of each file |

---

### `docs/configuration.md` — Configuration Reference

| Section | Required Content |
|---------|-----------------|
| `# Configuration` | Brief intro: all config via environment variables and `.env` file |
| `## Environment Variables` | Full table: Variable, Default, Description for all 7 documented variables including `CHROMA_PERSIST_DIR` (`/chroma/data` in Docker Compose; `/tmp/chroma` for local runs) |
| `## Hardware Profiles (Docker)` | Table of COMPOSE_PROFILES values (cpu, gpu-nvidia, gpu-amd) with requirements; startup command; warning about invalid values |
| `## Switching Models` | How to change generation, judge, and embedding models via env vars; note that new models are auto-pulled on next startup |
| `## Port Remapping` | Default ports for each service; how to remap via docker-compose port override syntax; example |
| `## Data Management` | How ChromaDB data persists; how to reset ChromaDB only vs. reset everything (volume commands) |
| `## OS Requirements` | Linux and macOS supported natively; Windows users should use WSL2; link to WSL2 docs |

---

## Files to Modify

### `README.md` — Revision Only

**Permitted changes** (fix inaccuracies only, no new sections):

| Location | Current (incorrect) | Corrected value |
|----------|--------------------|--------------  |
| Env Vars table — `OLLAMA_MODEL` default | `qwen3.5:9b` | `llama3.2` |
| Env Vars table — `OLLAMA_JUDGE_MODEL` default | `llama3.2` | `mistral` |
| MLflow Dashboard — scorers list | 4 scorers including `retrieval_groundedness` | 3 scorers: answer relevancy, hallucination, safety |
| How It Works — MLflow Logging scorers | 4 scorers including `RetrievalGroundedness` | 3 scorers: `AnswerRelevancy`, `Hallucination`, `Safety` |

**Not permitted**: Adding new sections, rewriting existing sections, changing structure, adding new tables or examples.
