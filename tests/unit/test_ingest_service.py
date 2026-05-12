import asyncio

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

from src.services.ingest import ingest_document


@pytest.mark.unit
def test_ingest_unsupported_extension_raises_400(make_upload_file):
    mock_file = make_upload_file("virus.exe", b"bytes", "application/octet-stream")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ingest_document(mock_file))
    assert exc_info.value.status_code == 400
    assert ".exe" in exc_info.value.detail


@pytest.mark.unit
def test_ingest_no_extension_raises_400(make_upload_file):
    mock_file = make_upload_file("noextension", b"bytes", "text/plain")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ingest_document(mock_file))
    assert exc_info.value.status_code == 400
    assert "Unsupported file type" in exc_info.value.detail


@pytest.mark.unit
def test_ingest_empty_file_raises_400(make_upload_file):
    mock_file = make_upload_file("empty.txt", b"", "text/plain")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ingest_document(mock_file))
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Uploaded file is empty."


@pytest.mark.unit
def test_ingest_oversized_file_raises_413(make_upload_file):
    with patch("src.services.ingest.MAX_UPLOAD_SIZE_BYTES", 5):
        mock_file = make_upload_file("big.txt", b"Hello world!", "text/plain")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(ingest_document(mock_file))
    assert exc_info.value.status_code == 413
    assert "too large" in exc_info.value.detail.lower()


@pytest.mark.unit
def test_ingest_wrong_content_type_raises_400(make_upload_file):
    mock_file = make_upload_file("doc.txt", b"Hello world", "application/pdf")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ingest_document(mock_file))
    assert exc_info.value.status_code == 400
    assert "application/pdf" in exc_info.value.detail
    assert ".txt" in exc_info.value.detail


@pytest.mark.unit
def test_ingest_txt_wrong_content_type_pdf_raises_400(make_upload_file):
    mock_file = make_upload_file("report.txt", b"some text", "application/pdf")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ingest_document(mock_file))
    assert exc_info.value.status_code == 400
    assert "Unsupported content type" in exc_info.value.detail


@pytest.mark.unit
def test_ingest_txt_success(make_upload_file):
    mock_file = make_upload_file("doc.txt", b"Hello world", "text/plain")
    mock_pages = [MagicMock()]
    mock_chunks = [MagicMock(), MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma") as mock_chroma, \
         patch("src.services.ingest.TextLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks
        mock_chroma.return_value.add_documents = MagicMock()

        result = asyncio.run(ingest_document(mock_file))

    assert result.status == "ok"
    assert result.chunks_stored == 2
    assert result.filename == "doc.txt"


@pytest.mark.unit
def test_ingest_txt_octet_stream_content_type_succeeds(make_upload_file):
    mock_file = make_upload_file("data.txt", b"Some data", "application/octet-stream")
    mock_pages = [MagicMock()]
    mock_chunks = [MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma") as mock_chroma, \
         patch("src.services.ingest.TextLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks
        mock_chroma.return_value.add_documents = MagicMock()

        result = asyncio.run(ingest_document(mock_file))

    assert result.status == "ok"
    assert result.filename == "data.txt"


@pytest.mark.unit
def test_ingest_pdf_success(make_upload_file):
    mock_file = make_upload_file("report.pdf", b"%PDF-1.4 content", "application/pdf")
    mock_pages = [MagicMock(), MagicMock()]
    mock_chunks = [MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma") as mock_chroma, \
         patch("src.services.ingest.PyPDFLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load_and_split.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks
        mock_chroma.return_value.add_documents = MagicMock()

        result = asyncio.run(ingest_document(mock_file))

    assert result.status == "ok"
    assert result.chunks_stored == 1
    assert result.filename == "report.pdf"


@pytest.mark.unit
def test_ingest_none_content_type_skips_check(make_upload_file):
    mock_file = make_upload_file("doc.txt", b"Hello", None)
    mock_pages = [MagicMock()]
    mock_chunks = [MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma"), \
         patch("src.services.ingest.TextLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks

        result = asyncio.run(ingest_document(mock_file))

    assert result.status == "ok"
    assert result.filename == "doc.txt"


@pytest.mark.unit
def test_ingest_chunks_stored_reflects_splitter_output(make_upload_file):
    mock_file = make_upload_file("multi.txt", b"Long content here", "text/plain")
    mock_pages = [MagicMock()]
    mock_chunks = [MagicMock() for _ in range(7)]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma") as mock_chroma, \
         patch("src.services.ingest.TextLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks
        mock_chroma.return_value.add_documents = MagicMock()

        result = asyncio.run(ingest_document(mock_file))

    assert result.chunks_stored == 7
