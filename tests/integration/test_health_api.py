import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_httpx_cls(status_code: int = 200, raise_exc: Exception | None = None):
    mock_response = MagicMock()
    mock_response.status_code = status_code

    mock_http_client = AsyncMock()
    if raise_exc is not None:
        mock_http_client.get.side_effect = raise_exc
    else:
        mock_http_client.get.return_value = mock_response

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_cls


@pytest.mark.integration
def test_health_requires_no_authentication(client):
    mock_httpx_cls = _make_httpx_cls(status_code=200)
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):
        resp = client.get("/health")

    assert resp.status_code == 200


@pytest.mark.integration
def test_health_all_ok(client):
    mock_httpx_cls = _make_httpx_cls(status_code=200)
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 3

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):
        resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["ollama"] == "ok"
    assert data["chromadb"] == "ok"


@pytest.mark.integration
def test_health_ollama_connection_error_returns_error_field(client):
    mock_httpx_cls = _make_httpx_cls(raise_exc=ConnectionError("refused"))
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):
        resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["ollama"] == "error"
    assert data["chromadb"] == "ok"


@pytest.mark.integration
def test_health_ollama_non_200_returns_error_field(client):
    mock_httpx_cls = _make_httpx_cls(status_code=503)
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):
        resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["ollama"] == "error"
    assert data["chromadb"] == "ok"


@pytest.mark.integration
def test_health_chromadb_init_failure_returns_error_field(client):
    mock_httpx_cls = _make_httpx_cls(status_code=200)

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", side_effect=Exception("Chroma offline")):
        resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["ollama"] == "ok"
    assert data["chromadb"] == "error"


@pytest.mark.integration
def test_health_chromadb_count_failure_returns_error_field(client):
    mock_httpx_cls = _make_httpx_cls(status_code=200)
    mock_vs = MagicMock()
    mock_vs._collection.count.side_effect = Exception("count failed")

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):
        resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["ollama"] == "ok"
    assert data["chromadb"] == "error"


@pytest.mark.integration
def test_health_both_dependencies_fail(client):
    mock_httpx_cls = _make_httpx_cls(raise_exc=OSError("network down"))

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", side_effect=Exception("Chroma gone")):
        resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["ollama"] == "error"
    assert data["chromadb"] == "error"


@pytest.mark.integration
def test_health_response_schema_has_required_fields(client):
    mock_httpx_cls = _make_httpx_cls(status_code=200)
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):
        resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "ollama" in data
    assert "chromadb" in data
