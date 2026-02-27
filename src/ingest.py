import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import (
    CHROMA_PERSIST_DIR,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
)
from src.models import IngestResponse

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


async def ingest_document(file: UploadFile) -> IngestResponse:
    embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    vector_store = Chroma(
        embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR
    )

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
            pages = loader.load_and_split()
        else:
            loader = TextLoader(tmp_path)
            pages = loader.load()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=20,
        length_function=len,
        add_start_index=True,
    )
    chunks = splitter.split_documents(pages)

    vector_store.add_documents(documents=chunks)

    return IngestResponse(
        status="ok",
        chunks_stored=len(chunks),
        filename=file.filename or "",
    )
