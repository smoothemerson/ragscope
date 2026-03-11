# API Reference

A Q&A API built on Retrieval-Augmented Generation (RAG). Upload documents and ask questions about them — fully offline, no external API keys required.

## Base URL

```
http://localhost:8000
```

To use a different port, see [Configuration — Port Remapping](./configuration.md#port-remapping).

---

## POST /ingest

Upload a document to be processed and stored in the vector store.

### Request

- **Content-Type**: `multipart/form-data`
- **Field**: `file` — the document to upload

**Accepted file types**: `.pdf`, `.txt`

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@/path/to/document.pdf"
```

### Response — 200 OK

```json
{
  "status": "ok",
  "chunks_stored": 42,
  "filename": "document.pdf"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"ok"` on success |
| `chunks_stored` | integer | Number of text chunks stored in the vector store |
| `filename` | string | Name of the uploaded file |

### Errors

| Status | Condition |
|--------|-----------|
| `400 Bad Request` | File type is not `.pdf` or `.txt` |

```json
{
  "detail": "Unsupported file type '.docx'. Only .pdf and .txt are accepted."
}
```

---

## POST /query

Ask a question about the ingested documents.

### Request

- **Content-Type**: `application/json`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `question` | string | Yes | — | The question to answer (minimum 1 character) |
| `top_k` | integer | No | `4` | Number of document chunks to retrieve (minimum 1) |

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic of the document?", "top_k": 4}'
```

### Response — 200 OK

```json
{
  "answer": "O documento aborda...",
  "sources": [
    "chunk text 1",
    "chunk text 2"
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The generated answer |
| `sources` | array of strings | The document chunks used to generate the answer |

> **Note on response language**: The language model is configured to always respond in Brazilian Portuguese (pt-BR), regardless of the language used in the question.

### Errors

| Status | Condition |
|--------|-----------|
| `404 Not Found` | No documents have been ingested yet |
| `500 Internal Server Error` | Pipeline failure during query processing |

---

## GET /health

Check whether the API's dependencies are reachable.

```bash
curl http://localhost:8000/health
```

### Response — 200 OK

```json
{
  "status": "ok",
  "chromadb": "ok",
  "ollama": "ok"
}
```

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `status` | string | `"ok"` | Always `"ok"` — does not reflect dependency health |
| `chromadb` | string | `"ok"` / `"error"` | Whether ChromaDB is reachable |
| `ollama` | string | `"ok"` / `"error"` | Whether the Ollama service is reachable |

> **Note**: The top-level `status` field is always `"ok"`. Check the `chromadb` and `ollama` fields individually to determine dependency health.
