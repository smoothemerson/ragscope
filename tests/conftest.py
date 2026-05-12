import os

os.environ["API_KEY"] = "test-api-key"

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

TEST_API_KEY = "test-api-key"
WRONG_API_KEY = "wrong-key"


@pytest.fixture(scope="session")
def client():
    from src.main import app

    with patch("src.main.mlflow_autolog"), patch(
        "src.main.pull_model", new=AsyncMock()
    ):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def auth_headers():
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def make_upload_file():
    def _factory(filename: str, content: bytes, content_type: str | None) -> MagicMock:
        mock = MagicMock()
        mock.filename = filename
        mock.content_type = content_type
        mock.read = AsyncMock(side_effect=[content, b""])
        return mock

    return _factory
