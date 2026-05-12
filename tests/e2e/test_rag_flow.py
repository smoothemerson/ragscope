import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.e2e
def test_full_rag_user_journey(client, auth_headers):
    mock_pages = [MagicMock()]
    mock_chunks = [MagicMock(), MagicMock(), MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma") as mock_ingest_chroma, \
         patch("src.services.ingest.TextLoader") as mock_txt_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_txt_loader.return_value.load.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks
        mock_ingest_chroma.return_value.add_documents = MagicMock()

        ingest_resp = client.post(
            "/ingest",
            headers=auth_headers,
            files={
                "file": (
                    "user_guide.txt",
                    b"This document explains how to use the system.",
                    "text/plain",
                )
            },
        )

    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["status"] == "ok"
    assert ingest_data["chunks_stored"] == 3
    assert ingest_data["filename"] == "user_guide.txt"

    mock_query_vs = MagicMock()
    mock_query_vs._collection.count.return_value = 3

    mock_source_doc = MagicMock()
    mock_source_doc.page_content = "This document explains how to use the system."
    mock_query_vs.as_retriever.return_value.invoke.return_value = [mock_source_doc]

    mock_llm_resp = MagicMock()
    mock_llm_resp.content = "O documento explica como usar o sistema."

    with patch("src.services.query._get_vectorstore", return_value=mock_query_vs), \
         patch("src.services.query.get_llm") as mock_get_llm, \
         patch("src.services.query.PromptTemplate"), \
         patch("src.services.query.RunnableSequence") as mock_seq, \
         patch("src.services.query.run_judge_evaluations") as mock_eval:

        mock_get_llm.return_value = MagicMock()
        mock_seq.return_value.invoke.return_value = mock_llm_resp

        query_resp = client.post(
            "/query",
            headers=auth_headers,
            json={"question": "What does this document explain?", "top_k": 4},
        )

    assert query_resp.status_code == 200
    query_data = query_resp.json()
    assert query_data["answer"] == "O documento explica como usar o sistema."
    assert "This document explains how to use the system." in query_data["sources"]
    mock_eval.assert_called_once_with(
        question="What does this document explain?",
        answer="O documento explica como usar o sistema.",
        context_chunks=["This document explains how to use the system."],
    )

    mock_health_http_resp = MagicMock()
    mock_health_http_resp.status_code = 200

    mock_health_http_client = AsyncMock()
    mock_health_http_client.get.return_value = mock_health_http_resp

    mock_httpx_cls = MagicMock()
    mock_httpx_cls.return_value.__aenter__ = AsyncMock(
        return_value=mock_health_http_client
    )
    mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_health_vs = MagicMock()
    mock_health_vs._collection.count.return_value = 3

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_health_vs):
        health_resp = client.get("/health")

    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "ok"
    assert health_data["ollama"] == "ok"
    assert health_data["chromadb"] == "ok"


@pytest.mark.e2e
def test_query_before_ingest_returns_404(client, auth_headers):
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 0

    with patch("src.services.query._get_vectorstore", return_value=mock_vs):
        resp = client.post(
            "/query",
            headers=auth_headers,
            json={"question": "Is there anything stored?"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "No documents found. Please ingest documents first."


@pytest.mark.e2e
def test_unauthorized_user_cannot_ingest_or_query(client):
    ingest_resp = client.post(
        "/ingest",
        files={"file": ("doc.txt", b"content", "text/plain")},
    )
    assert ingest_resp.status_code == 401
    assert ingest_resp.json()["detail"] == "Unauthorized"

    query_resp = client.post(
        "/query",
        json={"question": "What is stored?"},
    )
    assert query_resp.status_code == 401
    assert query_resp.json()["detail"] == "Unauthorized"

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
