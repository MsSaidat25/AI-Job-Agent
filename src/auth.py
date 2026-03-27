# Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com). All Rights Reserved.
# avien@aviensolutions.com
"""
Authentication -- Cloud Identity Platform JWT verification.

When AUTH_ENABLED=true, incoming requests must carry a valid
`Authorization: Bearer <id_token>` header.  The token is verified
against Google's public signing keys.

When AUTH_ENABLED=false (local dev, default), the legacy X-Session-ID
header flow is used instead.

Usage in FastAPI:
    from src.auth import get_current_user_id

    @app.get("/api/protected")
    async def protected(user_id: str = Depends(get_current_user_id)):
        ...
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import jwt
from fastapi import Header, HTTPException, status

from config.settings import AUTH_ENABLED, GCP_PROJECT_ID

logger = logging.getLogger(__name__)

# Google's public JWK endpoint for Identity Platform / Firebase Auth tokens
_GOOGLE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
_cached_certs: dict[str, str] | None = None
_certs_fetched_at: float = 0.0
_CERTS_TTL_SECONDS: float = 3600.0  # 1 hour
_certs_lock = threading.Lock()


def _fetch_google_certs(force: bool = False) -> dict[str, str]:
    """Fetch and cache Google's public signing certificates (TTL: 1 hour)."""
    global _cached_certs, _certs_fetched_at

    if not force and _cached_certs is not None:
        if time.monotonic() - _certs_fetched_at < _CERTS_TTL_SECONDS:
            return _cached_certs

    with _certs_lock:
        # Double-check after acquiring lock
        if not force and _cached_certs is not None:
            if time.monotonic() - _certs_fetched_at < _CERTS_TTL_SECONDS:
                return _cached_certs

        import httpx
        try:
            resp = httpx.get(_GOOGLE_CERTS_URL, timeout=10.0)
            resp.raise_for_status()
            certs: dict[str, str] = resp.json()
            _cached_certs = certs
            _certs_fetched_at = time.monotonic()
            return certs
        except httpx.HTTPStatusError as e:
            logger.error("Failed to fetch Google certs: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to verify token: authentication service unavailable",
            )
        except httpx.RequestError as e:
            logger.error("Network error fetching Google certs: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to verify token: authentication service unavailable",
            )


def verify_id_token(token: str) -> dict:
    """Verify a Cloud Identity Platform / Firebase Auth ID token.

    Returns the decoded token payload containing user_id (sub), email, etc.
    Raises HTTPException on invalid/expired tokens.
    """
    try:
        # Decode header to get the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID (kid)",
            )

        # Fetch Google's public certs
        certs = _fetch_google_certs()
        cert_pem = certs.get(kid)
        if not cert_pem:
            # Force refresh and retry once (keys rotate)
            certs = _fetch_google_certs(force=True)
            cert_pem = certs.get(kid)
            if not cert_pem:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token signed with unknown key",
                )

        # Verify and decode
        payload = jwt.decode(
            token,
            cert_pem,
            algorithms=["RS256"],
            audience=GCP_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{GCP_PROJECT_ID}",
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        logger.exception("Invalid ID token received")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def get_current_user_id(
    authorization: Optional[str] = Header(default=None),
    x_session_id: Optional[str] = Header(default=None),
) -> str:
    """FastAPI dependency: extract user identity from the request.

    When AUTH_ENABLED=true:  verifies Bearer token, returns user_id (sub).
    When AUTH_ENABLED=false: returns the X-Session-ID header (legacy flow).
    """
    if AUTH_ENABLED:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required (Bearer <token>)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization.removeprefix("Bearer ").strip()
        payload = verify_id_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject (sub)",
            )
        return user_id

    # Legacy: X-Session-ID header for local dev / Render without auth
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Session-ID header is required.",
        )
    return x_session_id
