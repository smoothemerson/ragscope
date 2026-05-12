import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.integration
def test_query_missing_api_key_returns_401(client):
    resp = client.post("/query", json={"question": "test question"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized"


@pytest.mark.integration
def test_query_wrong_api_key_returns_401(client):
    resp = client.post(
        "/query",
        headers={"X-API-Key": "not-the-right-key"},
        json={"question": "test question"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized"


@pytest.mark.integration
def test_query_missing_body_returns_422(client, auth_headers):
    resp = client.post("/query", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.integration
def test_query_empty_question_returns_422(client, auth_headers):
    resp = client.post(
        "/query",
        headers=auth_headers,
        json={"question": ""},
    )
    assert resp.status_code == 422


@pytest.mark.integration
def test_query_question_too_long_returns_422(client, auth_headers):
    resp = client.post(
        "/query",
        headers=auth_headers,
        json={"question": "x" * 5001},
    )
    assert resp.status_code == 422


@pytest.mark.integration
def test_query_top_k_zero_returns_422(client, auth_headers):
    resp = client.post(
        "/query",
        headers=auth_headers,
        json={"question": "valid question", "top_k": 0},
    )
    assert resp.status_code == 422


@pytest.mark.integration
def test_query_top_k_negative_returns_422(client, auth_headers):
    resp = client.post(
        "/query",
        headers=auth_headers,
        json={"question": "valid question", "top_k": -1},
    )
    assert resp.status_code == 422


@pytest.mark.integration
def test_query_top_k_over_max_returns_422(client, auth_headers):
    resp = client.post(
        "/query",
        headers=auth_headers,
        json={"question": "valid question", "top_k": 21},
    )
    assert resp.status_code == 422


@pytest.mark.integration
def test_query_empty_collection_returns_404(client, auth_headers):
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 0

    with patch("src.services.query._get_vectorstore", return_value=mock_vs):
        resp = client.post(
            "/query",
            headers=auth_headers,
            json={"question": "What is in the store?"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "No documents found. Please ingest documents first."


@pytest.mark.integration
def test_query_success_returns_200_with_answer_and_sources(client, auth_headers):
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 10

    mock_doc = MagicMock()
    mock_doc.page_content = "Context passage"
    mock_vs.as_retriever.return_value.invoke.return_value = [mock_doc]

    mock_llm_response = MagicMock()
    mock_llm_response.content = "This is the answer."

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations"):

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_response

        resp = client.post(
            "/query",
            headers=auth_headers,
            json={"question": "What is the answer?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "This is the answer."
    assert data["sources"] == ["Context passage"]


@pytest.mark.integration
def test_query_default_top_k_accepted(client, auth_headers):
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 5

    mock_doc = MagicMock()
    mock_doc.page_content = "content"
    mock_vs.as_retriever.return_value.invoke.return_value = [mock_doc]

    mock_llm_response = MagicMock()
    mock_llm_response.content = "answer"

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations"):

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_response

        resp = client.post(
            "/query",
            headers=auth_headers,
            json={"question": "test without top_k"},
        )

    assert resp.status_code == 200


@pytest.mark.integration
def test_query_top_k_boundary_min_accepted(client, auth_headers):
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 2

    mock_doc = MagicMock()
    mock_doc.page_content = "c"
    mock_vs.as_retriever.return_value.invoke.return_value = [mock_doc]

    mock_llm_response = MagicMock()
    mock_llm_response.content = "a"

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations"):

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_response

        resp = client.post(
            "/query",
            headers=auth_headers,
            json={"question": "test", "top_k": 1},
        )

    assert resp.status_code == 200


@pytest.mark.integration
def test_query_top_k_boundary_max_accepted(client, auth_headers):
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 20

    mock_doc = MagicMock()
    mock_doc.page_content = "c"
    mock_vs.as_retriever.return_value.invoke.return_value = [mock_doc]

    mock_llm_response = MagicMock()
    mock_llm_response.content = "a"

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations"):

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_response

        resp = client.post(
            "/query",
            headers=auth_headers,
            json={"question": "test", "top_k": 20},
        )

    assert resp.status_code == 200


@pytest.mark.integration
def test_query_response_schema_has_required_fields(client, auth_headers):
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    mock_doc = MagicMock()
    mock_doc.page_content = "data"
    mock_vs.as_retriever.return_value.invoke.return_value = [mock_doc]

    mock_llm_response = MagicMock()
    mock_llm_response.content = "resp"

    with patch("src.services.query._get_vectorstore", return_value=mock_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations"):

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_response

        resp = client.post(
            "/query",
            headers=auth_headers,
            json={"question": "check schema"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
