import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.integration
def test_ingest_missing_api_key_returns_401(client):
    resp = client.post(
        "/ingest",
        files={"file": ("test.txt", b"Hello", "text/plain")},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized"


@pytest.mark.integration
def test_ingest_wrong_api_key_returns_401(client):
    resp = client.post(
        "/ingest",
        headers={"X-API-Key": "wrong-key"},
        files={"file": ("test.txt", b"Hello", "text/plain")},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized"


@pytest.mark.integration
def test_ingest_unsupported_extension_returns_400(client, auth_headers):
    resp = client.post(
        "/ingest",
        headers=auth_headers,
        files={"file": ("malware.exe", b"binary", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert ".exe" in resp.json()["detail"]
    assert "Unsupported file type" in resp.json()["detail"]


@pytest.mark.integration
def test_ingest_docx_extension_returns_400(client, auth_headers):
    resp = client.post(
        "/ingest",
        headers=auth_headers,
        files={"file": ("doc.docx", b"word content", "application/vnd.openxmlformats")},
    )
    assert resp.status_code == 400
    assert ".docx" in resp.json()["detail"]


@pytest.mark.integration
def test_ingest_empty_file_returns_400(client, auth_headers):
    resp = client.post(
        "/ingest",
        headers=auth_headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Uploaded file is empty."


@pytest.mark.integration
def test_ingest_oversized_file_returns_413(client, auth_headers):
    with patch("src.services.ingest.MAX_UPLOAD_SIZE_BYTES", 5):
        resp = client.post(
            "/ingest",
            headers=auth_headers,
            files={"file": ("big.txt", b"Too large content", "text/plain")},
        )
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"].lower()
    assert "Maximum allowed size" in resp.json()["detail"]


@pytest.mark.integration
def test_ingest_wrong_content_type_for_txt_returns_400(client, auth_headers):
    resp = client.post(
        "/ingest",
        headers=auth_headers,
        files={"file": ("doc.txt", b"Hello world", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "application/pdf" in resp.json()["detail"]
    assert ".txt" in resp.json()["detail"]


@pytest.mark.integration
def test_ingest_wrong_content_type_for_pdf_returns_400(client, auth_headers):
    resp = client.post(
        "/ingest",
        headers=auth_headers,
        files={"file": ("report.pdf", b"PDF content", "text/plain")},
    )
    assert resp.status_code == 400
    assert "text/plain" in resp.json()["detail"]
    assert ".pdf" in resp.json()["detail"]


@pytest.mark.integration
def test_ingest_txt_success_returns_200_with_fields(client, auth_headers):
    mock_pages = [MagicMock()]
    mock_chunks = [MagicMock(), MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma") as mock_chroma, \
         patch("src.services.ingest.TextLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks
        mock_chroma.return_value.add_documents = MagicMock()

        resp = client.post(
            "/ingest",
            headers=auth_headers,
            files={"file": ("sample.txt", b"Sample document content", "text/plain")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["chunks_stored"] == 2
    assert data["filename"] == "sample.txt"


@pytest.mark.integration
def test_ingest_pdf_success_returns_200_with_fields(client, auth_headers):
    mock_pages = [MagicMock(), MagicMock(), MagicMock()]
    mock_chunks = [MagicMock(), MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma") as mock_chroma, \
         patch("src.services.ingest.PyPDFLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load_and_split.return_value = mock_pages
        mock_splitter.return_value.split_documents.return_value = mock_chunks
        mock_chroma.return_value.add_documents = MagicMock()

        resp = client.post(
            "/ingest",
            headers=auth_headers,
            files={"file": ("paper.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["chunks_stored"] == 2
    assert data["filename"] == "paper.pdf"


@pytest.mark.integration
def test_ingest_response_schema_has_required_fields(client, auth_headers):
    mock_chunks = [MagicMock()]

    with patch("src.services.ingest.OllamaEmbeddings"), \
         patch("src.services.ingest.Chroma"), \
         patch("src.services.ingest.TextLoader") as mock_loader, \
         patch("src.services.ingest.RecursiveCharacterTextSplitter") as mock_splitter:

        mock_loader.return_value.load.return_value = [MagicMock()]
        mock_splitter.return_value.split_documents.return_value = mock_chunks

        resp = client.post(
            "/ingest",
            headers=auth_headers,
            files={"file": ("check.txt", b"content", "text/plain")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "chunks_stored" in data
    assert "filename" in data
