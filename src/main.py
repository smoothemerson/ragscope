import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile

from src.health import check_health
from src.ingest import ingest_document
from src.models import HealthResponse, IngestResponse, QueryRequest, QueryResponse
from src.query import handle_query
from src.tracking.setup import mlflow_autolog
from src.utils.log_manager import logger

os.environ["GIT_PYTHON_REFRESH"] = "quiet"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Configuring MLflow autolog...")
    mlflow_autolog()
    yield


app = FastAPI(
    title="RAG API",
    description="Retrieval-Augmented Generation API with MLflow evaluation dashboard",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest a PDF or text document into the vector store",
)
async def ingest(file: UploadFile = File(...)):
    return await ingest_document(file)


@app.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the RAG pipeline with a question",
)
async def query(request: QueryRequest):
    return await handle_query(request)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check for API dependencies",
)
async def health():
    return await check_health()
