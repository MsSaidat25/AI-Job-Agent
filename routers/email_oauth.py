"""Email OAuth and compose endpoints (Sprint 3)."""

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from routers.schemas import AgentResponse

router = APIRouter(prefix="/api/email", tags=["email"])


# ── Request / Response schemas ───────────────────────────────────────────────


class OAuthRedirectResponse(BaseModel):
    redirect_url: str


class OAuthCallbackResponse(BaseModel):
    status: str
    email: str = ""
    message: str = ""


class AuthStatusResponse(BaseModel):
    connected: bool = False
    provider: str = ""
    email: str = ""


class ComposeEmailRequest(BaseModel):
    to: str = Field(..., max_length=500)
    subject: str = Field(..., max_length=500)
    job_id: Optional[str] = Field(default=None, max_length=200)
    application_id: Optional[str] = Field(default=None, max_length=200)
    tone: str = Field(default="professional", max_length=50)


class ComposeEmailResponse(BaseModel):
    subject: str
    body: str
    to: str
    ready_to_send: bool = False


class InboxItem(BaseModel):
    message_id: str = ""
    subject: str = ""
    sender: str = ""
    date: str = ""
    snippet: str = ""
    is_reply: bool = False


class InboxResponse(BaseModel):
    messages: list[InboxItem] = Field(default_factory=list)
    total: int = 0


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.get("/auth/gmail", response_model=OAuthRedirectResponse)
    @limiter.limit("5/minute")
    async def gmail_auth_redirect(
        request: Request,
        session_id: str = session_dep,
    ):
        """Get Gmail OAuth redirect URL."""
        from src.email_oauth_service import EmailOAuthService

        service = EmailOAuthService()
        url, _state = await asyncio.to_thread(service.get_gmail_auth_url, session_id)
        return OAuthRedirectResponse(redirect_url=url)

    @router.get("/auth/gmail/callback", response_model=OAuthCallbackResponse)
    @limiter.limit("10/minute")
    async def gmail_auth_callback(
        request: Request,
        code: str = "",
        state: str = "",
        session_id: str = session_dep,
    ):
        """Handle Gmail OAuth callback."""
        from src.email_oauth_service import EmailOAuthService

        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code.")
        if not state:
            raise HTTPException(status_code=400, detail="Missing state parameter.")
        # Validate CSRF state token
        service = EmailOAuthService()
        mapped_user = service.validate_oauth_state(state)
        if not mapped_user:
            raise HTTPException(status_code=400, detail="Invalid or expired state token.")
        result = await service.handle_gmail_callback(code=code, user_id=mapped_user)

        # Persist tokens to DB
        if result.get("access_token"):
            from src.models import EmailOAuthTokenORM, init_db
            from src.privacy import encrypt
            from src.models_db import _get_encryption_key
            from config.settings import ENCRYPT_USER_DATA
            db = init_db()
            try:
                access_val = result["access_token"]
                refresh_val = result.get("refresh_token", "")
                if ENCRYPT_USER_DATA:
                    key = _get_encryption_key()
                    access_val = encrypt(access_val, key)
                    if refresh_val:
                        refresh_val = encrypt(refresh_val, key)
                token_orm = EmailOAuthTokenORM(
                    user_id=mapped_user,
                    provider="gmail",
                    access_token_enc=access_val,
                    refresh_token_enc=refresh_val,
                    scopes="gmail.send gmail.readonly",
                )
                db.merge(token_orm)
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

        return OAuthCallbackResponse(
            status="connected" if result.get("access_token") else "error",
            email="",
            message="Gmail connected" if result.get("access_token") else "Connection failed",
        )

    @router.get("/auth/status", response_model=AuthStatusResponse)
    @limiter.limit("30/minute")
    async def auth_status(
        request: Request,
        session_id: str = session_dep,
    ):
        """Check email connection status."""
        from src.models import EmailOAuthTokenORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            token = db.query(EmailOAuthTokenORM).filter_by(user_id=profile.id).first()
            if not token:
                return AuthStatusResponse(connected=False)
            t: Any = token
            return AuthStatusResponse(
                connected=True,
                provider=t.provider,
                email=t.email_address or "",
            )
        finally:
            db.close()

    @router.delete("/auth/gmail", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def disconnect_gmail(
        request: Request,
        session_id: str = session_dep,
    ):
        """Disconnect Gmail OAuth."""
        from src.models import EmailOAuthTokenORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            token = db.query(EmailOAuthTokenORM).filter_by(user_id=profile.id).first()
            if token:
                db.delete(token)
                db.commit()
            return AgentResponse(response="Gmail disconnected.")
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.post("/compose", response_model=ComposeEmailResponse)
    @limiter.limit("5/minute")
    async def compose_email(
        request: Request,
        body: ComposeEmailRequest,
        session_id: str = session_dep,
    ):
        """Compose an application email (user reviews before send)."""
        agent = get_agent_fn(session_id)
        context_parts = [
            f"Draft a {body.tone} application email to {body.to}.",
            f"Subject should relate to: {body.subject}",
        ]
        if body.job_id:
            context_parts.append(f"This is for job ID: {body.job_id}")
        if body.application_id:
            context_parts.append(f"Application ID: {body.application_id}")
        context_parts.append(
            "Write the full email body. Do not include a subject line in the body."
        )
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(agent.chat, " ".join(context_parts))
        return ComposeEmailResponse(
            subject=body.subject,
            body=response,
            to=body.to,
            ready_to_send=False,
        )

    @router.get("/inbox", response_model=InboxResponse)
    @limiter.limit("10/minute")
    async def check_inbox(
        request: Request,
        session_id: str = session_dep,
    ):
        """Check for replies in connected email inbox."""
        from src.email_oauth_service import EmailOAuthService
        from src.session_store import get_session_profile

        get_session_profile(session_id)
        EmailOAuthService()
        # Would need stored access token from EmailOAuthTokenORM
        return InboxResponse(messages=[], total=0)
