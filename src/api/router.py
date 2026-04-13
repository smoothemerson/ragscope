from fastapi import APIRouter, Depends, File, UploadFile

from src.models import HealthResponse, IngestResponse, QueryRequest, QueryResponse
from src.security import verify_api_key
from src.services.health import check_health
from src.services.ingest import ingest_document
from src.services.query import handle_query

router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest a PDF or text document into the vector store",
)
async def ingest(file: UploadFile = File(...), _: None = Depends(verify_api_key)):
    return await ingest_document(file)


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the RAG pipeline with a question",
)
async def query(request: QueryRequest, _: None = Depends(verify_api_key)):
    return await handle_query(request)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check for API dependencies",
)
async def health():
    return await check_health()
