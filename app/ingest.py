import tempfile
from pathlib import Path

import chromadb
from fastapi import HTTPException, UploadFile
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaEmbeddings

from app.config import (
    CHROMA_COLLECTION,
    CHROMA_HOST,
    CHROMA_PORT,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
)
from app.models import IngestResponse

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


def get_chroma_client() -> chromadb.HttpClient:
    try:
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"ChromaDB unreachable: {exc}"
        ) from exc


async def ingest_document(file: UploadFile) -> IngestResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Only .pdf and .txt are accepted.",
        )

    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if suffix == ".pdf":
            loader = PyPDFLoader(tmp_path)
        else:
            loader = TextLoader(tmp_path)

        docs = loader.load()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(CHROMA_COLLECTION)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"ChromaDB unreachable: {exc}"
        ) from exc

    texts = [chunk.page_content for chunk in chunks]
    ids = [f"{file.filename}_{i}" for i in range(len(texts))]
    embedded = embeddings.embed_documents(texts)
    collection.add(documents=texts, embeddings=embedded, ids=ids)

    return IngestResponse(
        status="ok",
        chunks_stored=len(chunks),
        filename=file.filename or "",
    )
