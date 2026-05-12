import asyncio

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

from src.models import QueryRequest
from src.services.query import handle_query


@pytest.mark.unit
def test_query_empty_collection_raises_404():
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 0

    request = QueryRequest(question="What is this?")

    with patch("src.services.query._get_vectorstore", return_value=mock_vs):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(handle_query(request))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No documents found. Please ingest documents first."


@pytest.mark.unit
def test_query_collection_count_exception_treated_as_empty_raises_404():
    mock_vs = MagicMock()
    mock_vs._collection.count.side_effect = Exception("Chroma unreachable")

    request = QueryRequest(question="What?")

    with patch("src.services.query._get_vectorstore", return_value=mock_vs):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(handle_query(request))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No documents found. Please ingest documents first."


@pytest.mark.unit
def test_query_success_returns_answer_and_sources():
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 5

    mock_doc = MagicMock()
    mock_doc.page_content = "Relevant content here"
    mock_vs.as_retriever.return_value.invoke.return_value = [mock_doc]

    mock_llm_response = MagicMock()
    mock_llm_response.content = "The answer is 42."

    request = QueryRequest(question="What is the answer?")

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations") as mock_eval:

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_response

        result = asyncio.run(handle_query(request))

    assert result.answer == "The answer is 42."
    assert result.sources == ["Relevant content here"]
    mock_eval.assert_called_once_with(
        question="What is the answer?",
        answer="The answer is 42.",
        context_chunks=["Relevant content here"],
    )


@pytest.mark.unit
def test_query_multiple_sources_joined_as_context():
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 3

    doc1 = MagicMock()
    doc1.page_content = "First chunk"
    doc2 = MagicMock()
    doc2.page_content = "Second chunk"
    mock_vs.as_retriever.return_value.invoke.return_value = [doc1, doc2]

    mock_llm_response = MagicMock()
    mock_llm_response.content = "Combined answer"

    request = QueryRequest(question="Tell me everything", top_k=2)

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations") as mock_eval:

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_response

        result = asyncio.run(handle_query(request))

    assert result.sources == ["First chunk", "Second chunk"]
    assert result.answer == "Combined answer"
    mock_eval.assert_called_once()


@pytest.mark.unit
def test_query_no_sources_skips_judge_evaluation():
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 5
    mock_vs.as_retriever.return_value.invoke.return_value = []

    mock_llm_response = MagicMock()
    mock_llm_response.content = "No context answer."

    request = QueryRequest(question="Anything?")

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations") as mock_eval:

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_response

        result = asyncio.run(handle_query(request))

    assert result.answer == "No context answer."
    assert result.sources == []
    mock_eval.assert_not_called()


@pytest.mark.unit
def test_query_vectorstore_init_exception_raises_500():
    request = QueryRequest(question="What?")

    with patch(
        "src.services.query._get_vectorstore",
        side_effect=RuntimeError("DB connection failed"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(handle_query(request))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal query pipeline error."


@pytest.mark.unit
def test_query_retriever_exception_raises_500():
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 3
    mock_vs.as_retriever.side_effect = RuntimeError("Retriever broken")

    request = QueryRequest(question="What?")

    with patch("src.services.query._get_vectorstore", return_value=mock_vs):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(handle_query(request))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal query pipeline error."


@pytest.mark.unit
def test_query_llm_sequence_exception_raises_500():
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 2

    mock_doc = MagicMock()
    mock_doc.page_content = "Some context"
    mock_vs.as_retriever.return_value.invoke.return_value = [mock_doc]

    request = QueryRequest(question="What?")

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq:

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.side_effect = RuntimeError("LLM timeout")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(handle_query(request))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal query pipeline error."
