import pytest
from pydantic import ValidationError

from src.models import HealthResponse, IngestResponse, QueryRequest, QueryResponse


@pytest.mark.unit
def test_query_request_defaults():
    req = QueryRequest(question="test question")
    assert req.question == "test question"
    assert req.top_k == 4


@pytest.mark.unit
def test_query_request_custom_top_k():
    req = QueryRequest(question="test", top_k=10)
    assert req.top_k == 10


@pytest.mark.unit
def test_query_request_single_char_question():
    req = QueryRequest(question="x")
    assert req.question == "x"


@pytest.mark.unit
def test_query_request_max_length_question():
    req = QueryRequest(question="a" * 5000)
    assert len(req.question) == 5000


@pytest.mark.unit
def test_query_request_empty_question_fails():
    with pytest.raises(ValidationError):
        QueryRequest(question="")


@pytest.mark.unit
def test_query_request_over_max_length_fails():
    with pytest.raises(ValidationError):
        QueryRequest(question="a" * 5001)


@pytest.mark.unit
def test_query_request_top_k_min_boundary():
    req = QueryRequest(question="test", top_k=1)
    assert req.top_k == 1


@pytest.mark.unit
def test_query_request_top_k_max_boundary():
    req = QueryRequest(question="test", top_k=20)
    assert req.top_k == 20


@pytest.mark.unit
def test_query_request_top_k_zero_fails():
    with pytest.raises(ValidationError):
        QueryRequest(question="test", top_k=0)


@pytest.mark.unit
def test_query_request_top_k_over_max_fails():
    with pytest.raises(ValidationError):
        QueryRequest(question="test", top_k=21)


@pytest.mark.unit
def test_query_request_top_k_negative_fails():
    with pytest.raises(ValidationError):
        QueryRequest(question="test", top_k=-1)


@pytest.mark.unit
def test_ingest_response_fields():
    resp = IngestResponse(status="ok", chunks_stored=5, filename="doc.txt")
    assert resp.status == "ok"
    assert resp.chunks_stored == 5
    assert resp.filename == "doc.txt"


@pytest.mark.unit
def test_ingest_response_zero_chunks():
    resp = IngestResponse(status="ok", chunks_stored=0, filename="empty.txt")
    assert resp.chunks_stored == 0


@pytest.mark.unit
def test_query_response_fields():
    resp = QueryResponse(answer="The answer", sources=["chunk1", "chunk2"])
    assert resp.answer == "The answer"
    assert resp.sources == ["chunk1", "chunk2"]


@pytest.mark.unit
def test_query_response_empty_sources():
    resp = QueryResponse(answer="some answer", sources=[])
    assert resp.sources == []


@pytest.mark.unit
def test_query_response_empty_answer():
    resp = QueryResponse(answer="", sources=[])
    assert resp.answer == ""


@pytest.mark.unit
def test_health_response_all_ok():
    resp = HealthResponse(status="ok", chromadb="ok", ollama="ok")
    assert resp.status == "ok"
    assert resp.chromadb == "ok"
    assert resp.ollama == "ok"


@pytest.mark.unit
def test_health_response_with_errors():
    resp = HealthResponse(status="ok", chromadb="error", ollama="error")
    assert resp.status == "ok"
    assert resp.chromadb == "error"
    assert resp.ollama == "error"


@pytest.mark.unit
def test_health_response_partial_error():
    resp = HealthResponse(status="ok", chromadb="ok", ollama="error")
    assert resp.ollama == "error"
    assert resp.chromadb == "ok"
