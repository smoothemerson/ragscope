import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.models import IngestResponse
from src.utils.env import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
)

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
ALLOWED_CONTENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain", "application/octet-stream"},
}


async def ingest_document(file: UploadFile) -> IngestResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Only .pdf and .txt are accepted.",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name

    total_bytes = 0

    with open(tmp_path, "wb") as tmp:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break

            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Uploaded file is too large. "
                        f"Maximum allowed size is {MAX_UPLOAD_SIZE_BYTES} bytes."
                    ),
                )

            tmp.write(chunk)

    if total_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES.get(suffix, set()):
        raise HTTPException(
            status_code=400,
            detail=(f"Unsupported content type '{content_type}' for '{suffix}' files."),
        )

    embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    vector_store = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    if suffix == ".pdf":
        loader = PyPDFLoader(tmp_path)
        pages = loader.load_and_split()
    else:
        loader = TextLoader(tmp_path)
        pages = loader.load()

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
