"""Tests for src/auth.py -- JWT verification and user identity extraction."""
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from src.auth import get_current_user_id, verify_id_token


# ── verify_id_token ──────────────────────────────────────────────────────────


def _make_token(payload: dict, kid: str = "key1", key: str = "secret") -> str:
    return jwt.encode(payload, key, algorithm="HS256", headers={"kid": kid})


@patch("src.auth._fetch_google_certs")
def test_verify_missing_kid(mock_certs):
    """Token without kid header should raise 401."""
    token = jwt.encode({"sub": "u1"}, "s", algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        verify_id_token(token)
    assert exc_info.value.status_code == 401
    assert "kid" in exc_info.value.detail


@patch("src.auth._fetch_google_certs")
def test_verify_unknown_kid(mock_certs):
    """Token signed with unknown kid should raise 401 after cert refresh."""
    mock_certs.return_value = {"other_key": "cert_pem"}
    token = _make_token({"sub": "u1"}, kid="unknown_kid")
    with pytest.raises(HTTPException) as exc_info:
        verify_id_token(token)
    assert exc_info.value.status_code == 401
    assert "unknown key" in exc_info.value.detail
    # Should have tried to force-refresh certs
    assert mock_certs.call_count == 2


@patch("src.auth._fetch_google_certs")
def test_verify_expired_token(mock_certs):
    """Expired token should raise 401 via ExpiredSignatureError."""
    import time

    mock_certs.return_value = {"key1": "cert_pem"}
    token = _make_token({"sub": "u1", "exp": int(time.time()) - 3600}, kid="key1")
    with patch("src.auth.jwt.decode", side_effect=jwt.ExpiredSignatureError("Token is expired")):
        with pytest.raises(HTTPException) as exc_info:
            verify_id_token(token)
    assert exc_info.value.status_code == 401


# ── get_current_user_id ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("src.auth.AUTH_ENABLED", False)
async def test_get_user_id_legacy_mode():
    """When AUTH_ENABLED=false, returns X-Session-ID."""
    result = await get_current_user_id(authorization=None, x_session_id="sess-123")
    assert result == "sess-123"


@pytest.mark.asyncio
@patch("src.auth.AUTH_ENABLED", False)
async def test_get_user_id_legacy_missing_header():
    """When AUTH_ENABLED=false and no X-Session-ID, raises 400."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(authorization=None, x_session_id=None)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@patch("src.auth.AUTH_ENABLED", True)
async def test_get_user_id_auth_missing_bearer():
    """When AUTH_ENABLED=true and no Authorization header, raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(authorization=None, x_session_id=None)
    assert exc_info.value.status_code == 401
    assert "Bearer" in exc_info.value.detail


@pytest.mark.asyncio
@patch("src.auth.AUTH_ENABLED", True)
@patch("src.auth.verify_id_token")
async def test_get_user_id_auth_valid_token(mock_verify):
    """When AUTH_ENABLED=true with valid Bearer token, returns sub."""
    mock_verify.return_value = {"sub": "user-abc"}
    result = await get_current_user_id(
        authorization="Bearer some-token", x_session_id=None
    )
    assert result == "user-abc"
    mock_verify.assert_called_once_with("some-token")


@pytest.mark.asyncio
@patch("src.auth.AUTH_ENABLED", True)
@patch("src.auth.verify_id_token")
async def test_get_user_id_auth_missing_sub(mock_verify):
    """When token payload has no sub, raises 401."""
    mock_verify.return_value = {"email": "user@example.com"}
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(
            authorization="Bearer some-token", x_session_id=None
        )
    assert exc_info.value.status_code == 401
    assert "sub" in exc_info.value.detail
