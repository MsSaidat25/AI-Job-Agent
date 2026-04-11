"""Authentication endpoints: signup, login, Google OAuth, refresh, sign-out."""

import logging
import urllib.parse
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter

from routers.schemas import (
    AuthResponse,
    GoogleAuthRequest,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _setup_routes(limiter: Limiter, session_dep: Any) -> None:
    from config.settings import GCP_IDENTITY_PLATFORM_API_KEY
    from src.session_store import create_session, delete_session

    _IDP_BASE = "https://identitytoolkit.googleapis.com/v1"
    _TOKEN_BASE = "https://securetoken.googleapis.com/v1"

    def _idp_url(endpoint: str) -> str:
        return f"{_IDP_BASE}/{endpoint}?key={GCP_IDENTITY_PLATFORM_API_KEY}"

    def _token_url() -> str:
        return f"{_TOKEN_BASE}/token?key={GCP_IDENTITY_PLATFORM_API_KEY}"

    @router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
    @limiter.limit("10/hour")
    async def signup(request: Request, body: SignupRequest):
        """Create a new user via GCP Identity Platform."""
        if not GCP_IDENTITY_PLATFORM_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not configured.",
            )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _idp_url("accounts:signUp"),
                json={
                    "email": body.email,
                    "password": body.password,
                    "displayName": body.name,
                    "returnSecureToken": True,
                },
            )
        data = resp.json()
        if resp.status_code != 200:
            detail = data.get("error", {}).get("message", "Signup failed")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        user_id = data["localId"]
        create_session(user_id=user_id)
        return AuthResponse(
            id_token=data["idToken"],
            refresh_token=data["refreshToken"],
            user_id=user_id,
            expires_in=int(data.get("expiresIn", 3600)),
        )

    @router.post("/login", response_model=AuthResponse)
    @limiter.limit("20/hour")
    async def login(request: Request, body: LoginRequest):
        """Sign in with email and password."""
        if not GCP_IDENTITY_PLATFORM_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not configured.",
            )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _idp_url("accounts:signInWithPassword"),
                json={
                    "email": body.email,
                    "password": body.password,
                    "returnSecureToken": True,
                },
            )
        data = resp.json()
        if resp.status_code != 200:
            detail = data.get("error", {}).get("message", "Login failed")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        user_id = data["localId"]
        create_session(user_id=user_id)
        return AuthResponse(
            id_token=data["idToken"],
            refresh_token=data["refreshToken"],
            user_id=user_id,
            expires_in=int(data.get("expiresIn", 3600)),
        )

    @router.post("/google", response_model=AuthResponse)
    @limiter.limit("20/hour")
    async def google_auth(request: Request, body: GoogleAuthRequest):
        """Exchange a Google ID token for Identity Platform credentials."""
        if not GCP_IDENTITY_PLATFORM_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not configured.",
            )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _idp_url("accounts:signInWithIdp"),
                json={
                    "postBody": f"id_token={urllib.parse.quote(body.id_token, safe='')}&providerId=google.com",
                    "requestUri": request.base_url._url.rstrip("/"),
                    "returnIdpCredential": True,
                    "returnSecureToken": True,
                },
            )
        data = resp.json()
        if resp.status_code != 200:
            detail = data.get("error", {}).get("message", "Google auth failed")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        user_id = data["localId"]
        create_session(user_id=user_id)
        return AuthResponse(
            id_token=data["idToken"],
            refresh_token=data["refreshToken"],
            user_id=user_id,
            expires_in=int(data.get("expiresIn", 3600)),
        )

    @router.post("/refresh", response_model=AuthResponse)
    @limiter.limit("30/hour")
    async def refresh_token(request: Request, body: RefreshRequest):
        """Exchange a refresh token for a new ID token."""
        if not GCP_IDENTITY_PLATFORM_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not configured.",
            )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _token_url(),
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": body.refresh_token,
                },
            )
        data = resp.json()
        if resp.status_code != 200:
            detail = data.get("error", {}).get("message", "Token refresh failed")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        return AuthResponse(
            id_token=data["id_token"],
            refresh_token=data["refresh_token"],
            user_id=data["user_id"],
            expires_in=int(data.get("expires_in", 3600)),
        )

    @router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
    @limiter.limit("30/hour")
    async def sign_out(request: Request, session_id: str = session_dep):
        """Sign out and clear the server-side session."""
        delete_session(session_id)
