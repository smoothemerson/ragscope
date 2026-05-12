import pytest
from fastapi import HTTPException

from src.security import verify_api_key


@pytest.mark.unit
def test_verify_api_key_correct_returns_none():
    result = verify_api_key("test-api-key")
    assert result is None


@pytest.mark.unit
def test_verify_api_key_wrong_key_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key("completely-wrong-key")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


@pytest.mark.unit
def test_verify_api_key_none_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


@pytest.mark.unit
def test_verify_api_key_empty_string_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key("")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


@pytest.mark.unit
def test_verify_api_key_similar_but_not_equal_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key("test-api-key-extra")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"
