from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    status: str
    chunks_stored: int
    filename: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(default=4, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


class HealthResponse(BaseModel):
    status: str
    chromadb: str
    ollama: str
