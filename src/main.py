import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, File, UploadFile

from src.health import check_health
from src.ingest import ingest_document
from src.models import HealthResponse, IngestResponse, QueryRequest, QueryResponse
from src.query import handle_query
from src.security import verify_api_key
from src.tracking.setup import mlflow_autolog
from src.utils.env import (
    API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_JUDGE_MODEL,
    OLLAMA_MODEL,
)
from src.utils.log_manager import logger

os.environ["GIT_PYTHON_REFRESH"] = "quiet"


async def pull_model(client: httpx.AsyncClient, model: str) -> None:
    logger.info(f"Pulling Ollama model: {model}")
    async with client.stream(
    try:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model},
            timeout=httpx.Timeout(connect=5.0, read=60.0, write=30.0, pool=5.0),
        ) as response:
            response.raise_for_status()
            async for _ in response.aiter_lines():
                pass
    except httpx.TimeoutException as exc:
        logger.warning(f"Timed out while pulling Ollama model {model}: {exc}")
        raise
    logger.info(f"Model ready: {model}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not API_KEY:
        raise RuntimeError("API_KEY is required and must not be empty.")

    logger.info("Configuring MLflow autolog...")
    mlflow_autolog()

    logger.info("Starting up — pulling required Ollama models...")
    try:
        async with httpx.AsyncClient() as client:
            for model in [OLLAMA_MODEL, OLLAMA_JUDGE_MODEL, OLLAMA_EMBED_MODEL]:
                await pull_model(client, model)
        logger.info("All models ready. API is now accepting requests.")
    except Exception as exc:
        logger.warning(
            "Could not pre-pull one or more Ollama models. "
            f"Continuing startup without warm-up: {exc}"
        )
    yield


app = FastAPI(
    title="RAG API",
    description="Retrieval-Augmented Generation API with MLflow evaluation dashboard",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest a PDF or text document into the vector store",
)
async def ingest(file: UploadFile = File(...), _: None = Depends(verify_api_key)):
    return await ingest_document(file)


@app.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the RAG pipeline with a question",
)
async def query(request: QueryRequest, _: None = Depends(verify_api_key)):
    return await handle_query(request)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check for API dependencies",
)
async def health():
    return await check_health()
