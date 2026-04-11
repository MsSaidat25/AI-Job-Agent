"""Email OAuth Service -- Gmail integration for sending applications and monitoring replies."""
from __future__ import annotations

import logging
from typing import Any, Optional, cast

from anthropic.types import TextBlock
from pydantic import BaseModel, Field

from config.settings import AGENT_MODEL, get_secret
from src.llm_client import create_message_with_failover, get_llm_client

logger = logging.getLogger(__name__)

GMAIL_CLIENT_ID = get_secret("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = get_secret("GMAIL_CLIENT_SECRET")
GMAIL_REDIRECT_URI = get_secret("GMAIL_REDIRECT_URI", "http://localhost:8000/api/email/auth/gmail/callback")

_GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
_SCOPES = "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly"


class EmailMessage(BaseModel):
    message_id: str = ""
    thread_id: str = ""
    from_email: str = ""
    to_email: str = ""
    subject: str = ""
    body_preview: str = ""
    date: str = ""
    labels: list[str] = Field(default_factory=list)


class EmailClassification(BaseModel):
    message_id: str
    category: str = ""  # response, rejection, interview_invite, offer, follow_up, unrelated
    confidence: float = 0.0
    suggested_status: Optional[str] = None  # ApplicationStatus value
    summary: str = ""


class EmailConnectionStatus(BaseModel):
    connected: bool = False
    email: str = ""
    provider: str = ""
    scopes: list[str] = Field(default_factory=list)


_oauth_state_store: dict[str, str] = {}  # state_token -> user_id


class EmailOAuthService:
    """Gmail OAuth integration for sending and receiving emails."""

    def __init__(self, client: Any = None) -> None:
        self._client = client or get_llm_client()

    def get_gmail_auth_url(self, user_id: str) -> tuple[str, str]:
        """Generate the Gmail OAuth2 authorization URL with CSRF state token.

        Returns (auth_url, state_token).
        """
        import secrets
        if not GMAIL_CLIENT_ID:
            return "", ""
        state_token = secrets.token_urlsafe(32)
        _oauth_state_store[state_token] = user_id
        params = (
            f"client_id={GMAIL_CLIENT_ID}"
            f"&redirect_uri={GMAIL_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={_SCOPES}"
            f"&access_type=offline"
            f"&prompt=consent"
            f"&state={state_token}"
        )
        return f"{_GMAIL_AUTH_URL}?{params}", state_token

    @staticmethod
    def validate_oauth_state(state: str) -> str | None:
        """Validate and consume an OAuth state token. Returns user_id or None."""
        return _oauth_state_store.pop(state, None)

    async def handle_gmail_callback(
        self, code: str, user_id: str,
    ) -> dict[str, str]:
        """Exchange authorization code for tokens."""
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _GMAIL_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GMAIL_CLIENT_ID,
                    "client_secret": GMAIL_CLIENT_SECRET,
                    "redirect_uri": GMAIL_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
        data = resp.json()
        if resp.status_code != 200:
            logger.error("Gmail token exchange failed: %s", data)
            return {}
        return {
            "access_token": data.get("access_token", ""),
            "refresh_token": data.get("refresh_token", ""),
            "expires_in": str(data.get("expires_in", 3600)),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, str]:
        """Refresh an expired access token."""
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _GMAIL_TOKEN_URL,
                data={
                    "client_id": GMAIL_CLIENT_ID,
                    "client_secret": GMAIL_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        data = resp.json()
        if resp.status_code != 200:
            return {}
        return {
            "access_token": data.get("access_token", ""),
            "expires_in": str(data.get("expires_in", 3600)),
        }

    async def send_email(
        self, access_token: str, to: str, subject: str, body: str,
        from_email: str = "",
    ) -> bool:
        """Send an email via Gmail API using safe MIME construction."""
        import base64
        from email.message import EmailMessage as PyEmailMessage
        import httpx

        msg = PyEmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        if from_email:
            msg["From"] = from_email
        msg.set_content(body, subtype="html")
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{_GMAIL_API_BASE}/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw},
            )
        if resp.status_code == 200:
            logger.info("Email sent via Gmail to %s", to)
            return True
        logger.error("Gmail send failed: %s", resp.text[:200])
        return False

    async def check_inbox(
        self, access_token: str, since_date: str = "", max_results: int = 20,
    ) -> list[EmailMessage]:
        """Read recent inbox messages."""
        import httpx

        query = "in:inbox"
        if since_date:
            query += f" after:{since_date}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{_GMAIL_API_BASE}/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"q": query, "maxResults": max_results},
            )
        if resp.status_code != 200:
            logger.error("Gmail inbox check failed: %s", resp.text[:200])
            return []

        messages = []
        data = resp.json()
        for msg_ref in data.get("messages", [])[:max_results]:
            messages.append(EmailMessage(
                message_id=msg_ref.get("id", ""),
                thread_id=msg_ref.get("threadId", ""),
            ))

        return messages

    def classify_reply(self, subject: str, body_preview: str) -> EmailClassification:
        """Use LLM to classify an email reply as response/rejection/interview/offer."""
        try:
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=256,
                system=(
                    "Classify this email as one of: response, rejection, interview_invite, offer, follow_up, unrelated. "
                    "Return JSON with: category, confidence (0-1), suggested_status (ApplicationStatus value or null), summary."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Subject: {subject}\nPreview: {body_preview[:500]}",
                }],
            )
            from src.utils import parse_json_response
            text = cast(TextBlock, response.content[0]).text
            result = parse_json_response(text)
            if isinstance(result, dict):
                return EmailClassification(**result)
        except Exception:
            logger.warning("Email classification failed", exc_info=True)
        return EmailClassification(message_id="", category="unrelated")
