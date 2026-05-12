import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.health import check_health


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


@pytest.mark.unit
def test_health_all_ok():
    mock_httpx_cls = _make_httpx_cls(status_code=200)
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 5

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "ok"
    assert result.chromadb == "ok"


@pytest.mark.unit
def test_health_ollama_non_200_status_reports_error():
    mock_httpx_cls = _make_httpx_cls(status_code=503)
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "error"
    assert result.chromadb == "ok"


@pytest.mark.unit
def test_health_ollama_500_status_reports_error():
    mock_httpx_cls = _make_httpx_cls(status_code=500)
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "error"
    assert result.chromadb == "ok"


@pytest.mark.unit
def test_health_ollama_connection_error_reports_error():
    mock_httpx_cls = _make_httpx_cls(raise_exc=ConnectionError("Connection refused"))
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "error"
    assert result.chromadb == "ok"


@pytest.mark.unit
def test_health_ollama_timeout_reports_error():
    mock_httpx_cls = _make_httpx_cls(raise_exc=TimeoutError("timed out"))
    mock_vs = MagicMock()
    mock_vs._collection.count.return_value = 1

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "error"
    assert result.chromadb == "ok"


@pytest.mark.unit
def test_health_chromadb_init_exception_reports_error():
    mock_httpx_cls = _make_httpx_cls(status_code=200)

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", side_effect=Exception("Chroma unavailable")):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "ok"
    assert result.chromadb == "error"


@pytest.mark.unit
def test_health_chromadb_count_exception_reports_error():
    mock_httpx_cls = _make_httpx_cls(status_code=200)
    mock_vs = MagicMock()
    mock_vs._collection.count.side_effect = Exception("Count query failed")

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", return_value=mock_vs):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "ok"
    assert result.chromadb == "error"


@pytest.mark.unit
def test_health_both_fail_reports_both_errors():
    mock_httpx_cls = _make_httpx_cls(raise_exc=OSError("network failure"))

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", side_effect=Exception("Chroma down")):

        result = asyncio.run(check_health())

    assert result.status == "ok"
    assert result.ollama == "error"
    assert result.chromadb == "error"


@pytest.mark.unit
def test_health_status_always_ok_regardless_of_dependency_failures():
    mock_httpx_cls = _make_httpx_cls(raise_exc=RuntimeError("any error"))

    with patch("src.services.health.httpx.AsyncClient", mock_httpx_cls), \
         patch("src.services.health.OllamaEmbeddings"), \
         patch("src.services.health.Chroma", side_effect=Exception("any error")):

        result = asyncio.run(check_health())

    assert result.status == "ok"
