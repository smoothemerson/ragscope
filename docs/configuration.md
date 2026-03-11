# Configuration

All runtime behavior is controlled via environment variables. Copy `.env.example` to `.env` and set values before starting the stack.

```bash
cp .env.example .env
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPOSE_PROFILES` | `cpu` | Docker hardware profile — must be exactly `cpu`, `gpu-nvidia`, or `gpu-amd` |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model used for answer generation |
| `OLLAMA_JUDGE_MODEL` | `mistral` | Ollama model used for LLM-as-judge evaluation |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama model used for text embeddings |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow tracking server URI |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL — set automatically via Docker networking |
| `CHROMA_PERSIST_DIR` | `/tmp/chroma` | Path inside the container where ChromaDB persists its data (mounted to the `chroma_data` Docker volume) |

---

## Hardware Profiles

Set `COMPOSE_PROFILES` in your `.env` file to match your hardware before running `docker compose up`.

| Value | Hardware | Requirements |
|-------|----------|--------------|
| `cpu` | CPU only | Any x86-64 machine with Docker |
| `gpu-nvidia` | NVIDIA GPU | NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) |
| `gpu-amd` | AMD GPU (ROCm) | AMD GPU with ROCm support + Docker ROCm runtime |

```bash
# .env
COMPOSE_PROFILES=cpu        # or gpu-nvidia or gpu-amd
```

Then start the stack:

```bash
docker compose up
```

> **Warning**: `COMPOSE_PROFILES` must be exactly one of the three values above. Any other value — including leaving it blank — will cause no Ollama service to start, and the API will fail to connect on startup.

---

## Switching Models

Change the model for any role by updating the corresponding variable in `.env`. All changed models are pulled automatically on the next startup.

```bash
# .env
OLLAMA_MODEL=llama3.1          # change the generation model
OLLAMA_JUDGE_MODEL=llama3.2    # change the evaluation judge
OLLAMA_EMBED_MODEL=nomic-embed-text  # change the embedding model
```

**Model size guidance**:
- Generation and judge models should fit in your available VRAM (GPU) or RAM (CPU). Models in the 7B–13B range typically require 8–16 GB.
- The embedding model (`nomic-embed-text`) is lightweight (~300 MB) and rarely needs to change.
- Any model available via `ollama pull` can be used. Browse available models at [ollama.com/library](https://ollama.com/library).

After changing a model, restart the stack:

```bash
docker compose down
docker compose up
```

The new model will be pulled automatically before the API begins accepting requests.

---

## Port Remapping

Default ports used by each service:

| Service | Default Port |
|---------|-------------|
| FastAPI (API) | `8000` |
| MLflow UI | `5000` |
| Ollama | `11434` |

To remap a port, create a `docker-compose.override.yml` file at the repository root. Docker Compose merges it with `docker-compose.yml` automatically.

**Example — remap the API to port 9000**:

```yaml
# docker-compose.override.yml
services:
  api:
    ports:
      - "9000:8000"
```

Then access the API at `http://localhost:9000` instead of `http://localhost:8000`.

---

## Data Management

ChromaDB data accumulates across ingests and container restarts. Each new `POST /ingest` call adds to the existing collection — previously ingested documents are not removed.

**Reset ChromaDB only** (Ollama model cache is preserved — no re-download required):

```bash
docker compose down
docker volume rm <project>_chroma_data
docker compose up
```

Replace `<project>` with your Compose project name (typically the name of the repository directory). To find it:

```bash
docker compose config --volumes
```

**Reset everything** (ChromaDB + Ollama model cache):

```bash
docker compose down -v
```

> **Warning**: A full reset removes the Ollama model cache. All three models (`OLLAMA_MODEL`, `OLLAMA_JUDGE_MODEL`, `OLLAMA_EMBED_MODEL`) will be re-downloaded on the next startup.

---

## OS Requirements

**Linux** and **macOS** are supported natively via [Docker Engine](https://docs.docker.com/engine/install/) or [Docker Desktop](https://www.docker.com/products/docker-desktop/).

**Windows** users must use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) (Windows Subsystem for Linux 2). Run all commands from within a WSL2 terminal. Native Windows (PowerShell or CMD) is not supported.
