from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    status: str
    chunks_stored: int
    filename: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=4, ge=1)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    query_id: str


class HealthResponse(BaseModel):
    status: str
    chromadb: str
    ollama: str
