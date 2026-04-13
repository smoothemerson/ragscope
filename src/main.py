from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.api.router import router
from src.tracking.setup import mlflow_autolog
from src.utils.env import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_JUDGE_MODEL,
    OLLAMA_MODEL,
)
from src.utils.log_manager import logger


async def pull_model(client: httpx.AsyncClient, model: str) -> None:
    logger.info(f"Pulling Ollama model: {model}")
    try:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model},
            timeout=None,
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

app.include_router(router)
