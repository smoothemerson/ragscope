import httpx
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from src.models import HealthResponse
from src.utils.env import CHROMA_PERSIST_DIR, OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL


async def check_health() -> HealthResponse:
    ollama_status = "ok"
    chromadb_status = "ok"

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code != 200:
                ollama_status = "error"
        except Exception:
            ollama_status = "error"

    try:
        embeddings = OllamaEmbeddings(
            model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL
        )
        vectorstore = Chroma(
            collection_name="ragscope_collection",
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )
        vectorstore._collection.count()
    except Exception:
        chromadb_status = "error"

    return HealthResponse(
        status="ok",
        chromadb=chromadb_status,
        ollama=ollama_status,
    )
