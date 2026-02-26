import httpx

from app.config import CHROMA_HOST, CHROMA_PORT, OLLAMA_BASE_URL
from app.models import HealthResponse


async def check_health() -> HealthResponse:
    chroma_status = "ok"
    ollama_status = "ok"

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(
                f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v1/heartbeat"
            )
            if resp.status_code != 200:
                chroma_status = "error"
        except Exception:
            chroma_status = "error"

        try:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code != 200:
                ollama_status = "error"
        except Exception:
            ollama_status = "error"

    return HealthResponse(
        status="ok",
        chromadb=chroma_status,
        ollama=ollama_status,
    )
