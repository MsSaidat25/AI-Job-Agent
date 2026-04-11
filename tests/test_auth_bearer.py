"""End-to-end integration tests for the Bearer-JWT auth flow.

These complement ``tests/test_api.py`` (which exercises the legacy
``X-Session-ID`` header flow) and ``tests/test_auth.py`` (which unit-tests
the JWT primitives). Together they give dual coverage of both identity
paths, per the P0.7 remediation plan.

The tests patch ``src.auth.verify_id_token`` at the call site so no real
JWKS fetch or signature verification happens — the contract we care about
here is: *given a verified token payload, does a protected endpoint flow
correctly through require_session and auto-create a session for the
authenticated user?*

Scope note: POST /api/session currently creates an anonymous session
regardless of Bearer presence — it's intended to be called by legacy
flows only. In the Bearer flow, ``require_session`` auto-creates a
session on first hit to any protected endpoint, so no explicit session
creation step is needed. These tests verify that behaviour.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_db_auth_on(tmp_path, monkeypatch):
    """Force AUTH_ENABLED=true and isolate the DB for every test in this file."""
    db_path = tmp_path / "test_auth_bearer.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("src.models.DB_PATH", db_path)
    monkeypatch.setattr("src.models_bootstrap.DB_PATH", db_path)
    monkeypatch.setattr("config.settings.DATABASE_URL", "")
    monkeypatch.setattr("config.settings.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models.DATABASE_URL", "")
    monkeypatch.setattr("src.models.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL_FAILOVER", "")
    # Force Bearer-auth path — this file tests the non-legacy flow.
    monkeypatch.setattr("config.settings.AUTH_ENABLED", True)
    monkeypatch.setattr("src.auth.AUTH_ENABLED", True)

    from src.models import reset_db_state, init_db
    reset_db_state()
    s = init_db()
    s.close()

    # Wipe the in-memory session store so each test starts fresh.
    import src.session_store as ss
    with ss._sessions_lock:
        ss._sessions.clear()
        ss._user_to_session.clear()

    import api as api_mod
    monkeypatch.setattr(api_mod.limiter, "enabled", False)


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


def _auth_headers(token: str = "fake-valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Happy path: protected endpoints auto-create sessions ────────────────────


class TestBearerAutoCreatesSession:
    """When AUTH_ENABLED=true, ``require_session`` must auto-create a session
    for the authenticated user on first hit to any protected endpoint. These
    tests exercise GET /api/profile (which runs ``require_session`` and then
    tries to read the session's profile) because it hits the auto-create path
    without needing the full POST /api/profile agent-init handshake.
    """

    def test_get_profile_auto_creates_session(self, client):
        """GET /api/profile with a valid Bearer and no prior session should
        auto-create a session keyed to the Bearer ``sub``, then return 404
        because no profile is stored yet. The 404 is the contract — we're
        asserting session auto-creation, not profile presence.
        """
        with patch("src.auth.verify_id_token", return_value={"sub": "fb-user-abc"}):
            r = client.get("/api/profile", headers=_auth_headers())

        assert r.status_code == 404  # No profile stored — but session exists.

        import src.session_store as ss
        with ss._sessions_lock:
            assert "fb-user-abc" in ss._user_to_session
            mapped_sid = ss._user_to_session["fb-user-abc"]
            assert mapped_sid in ss._sessions

    def test_same_bearer_reuses_session(self, client):
        """Two Bearer requests with the same ``sub`` must map to one session."""
        import src.session_store as ss

        with patch("src.auth.verify_id_token", return_value={"sub": "fb-user-xyz"}):
            r1 = client.get("/api/profile", headers=_auth_headers())
            assert r1.status_code == 404  # Auto-created session, no profile yet.

            r2 = client.get("/api/profile", headers=_auth_headers())
            assert r2.status_code == 404  # Same — session reused.

        with ss._sessions_lock:
            user_sessions = [
                sid for sid, _ in ss._sessions.items()
                if ss._user_to_session.get("fb-user-xyz") == sid
            ]
            assert len(user_sessions) == 1


# ── Failure modes ───────────────────────────────────────────────────────────


class TestBearerFailures:
    def test_missing_bearer_header_returns_401(self, client):
        """No Authorization header when AUTH_ENABLED=true → 401."""
        r = client.get("/api/profile")
        assert r.status_code == 401
        assert "Bearer" in r.json()["detail"]

    def test_malformed_authorization_header_returns_401(self, client):
        """Authorization header without 'Bearer ' prefix → 401."""
        r = client.get(
            "/api/profile",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert r.status_code == 401

    def test_expired_token_returns_401(self, client):
        """``verify_id_token`` raising HTTPException(401) propagates."""
        with patch(
            "src.auth.verify_id_token",
            side_effect=HTTPException(status_code=401, detail="Token expired"),
        ):
            r = client.get("/api/profile", headers=_auth_headers("expired-token"))
        assert r.status_code == 401
        assert "expired" in r.json()["detail"].lower()

    def test_token_without_sub_returns_401(self, client):
        """A verified token with no ``sub`` claim → 401."""
        with patch("src.auth.verify_id_token", return_value={"email": "no-sub@example.com"}):
            r = client.get("/api/profile", headers=_auth_headers())
        assert r.status_code == 401
        assert "sub" in r.json()["detail"]
