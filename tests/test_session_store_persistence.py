"""Tests for the SQLite-backed session store (P3.4)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_session_persistence.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("src.models.DB_PATH", db_path)
    monkeypatch.setattr("src.models_bootstrap.DB_PATH", db_path)
    monkeypatch.setattr("config.settings.DATABASE_URL", "")
    monkeypatch.setattr("src.models.DATABASE_URL", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL", "")
    monkeypatch.setattr("config.settings.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("src.auth.AUTH_ENABLED", False)
    # Disable PII encryption so _seed_user_profile can round-trip plain text.
    monkeypatch.setattr("src.models_db.ENCRYPT_USER_DATA", False)
    from src.models import init_db, reset_db_state
    reset_db_state()
    s = init_db()
    s.close()
    # Clear session store so leftover state from other tests doesn't bleed in.
    import src.session_store as ss
    ss._sessions.clear()
    ss._user_to_session.clear()


def _seed_user_profile(user_id: str, firebase_uid: str = "") -> None:
    """Insert a UserProfileORM row we can rehydrate against."""
    from src.models import UserProfileORM, init_db

    db = init_db()
    try:
        db.add(UserProfileORM(
            id=user_id,
            firebase_uid=firebase_uid or None,
            name_enc="Test User",
            email_enc="test@test.com",
            location="Earth",
            skills=["Python"],
            experience_level="mid",
            education=[],
            work_history=[],
            desired_roles=[],
            desired_job_types=[],
            languages=["English"],
            certifications=[],
        ))
        db.commit()
    finally:
        db.close()


class TestPersistSession:
    def test_create_session_writes_row(self):
        import src.session_store as ss
        from src.models import SessionORM, init_db

        sid = ss.create_session(user_id="firebase-uid-1")
        db = init_db()
        try:
            row = db.query(SessionORM).filter_by(id=sid).first()
            assert row is not None
            assert str(row.user_id) == "firebase-uid-1"
        finally:
            db.close()

    def test_delete_session_removes_row(self):
        import src.session_store as ss
        from src.models import SessionORM, init_db

        sid = ss.create_session(user_id="firebase-uid-2")
        ss.delete_session(sid)
        db = init_db()
        try:
            row = db.query(SessionORM).filter_by(id=sid).first()
            assert row is None
        finally:
            db.close()

    def test_anonymous_session_persists_with_null_user(self):
        import src.session_store as ss
        from src.models import SessionORM, init_db

        sid = ss.create_session(user_id=None)
        db = init_db()
        try:
            row = db.query(SessionORM).filter_by(id=sid).first()
            assert row is not None
            assert row.user_id is None
        finally:
            db.close()


class TestRehydration:
    def test_rehydrate_after_memory_clear(self):
        """Simulate an API restart: clear _sessions, call rehydrate_session_from_db,
        and expect the persisted session to come back."""
        import src.session_store as ss

        # Seed profile + create persisted session.
        _seed_user_profile("user-123", firebase_uid="user-123")
        with patch("src.agent.JobAgent.__init__", return_value=None):
            sid = ss.create_session(user_id="user-123")
            # Populate the agent field so we have something to rehydrate against.
            ss.set_session_agent(sid, MagicMock(), MagicMock())

        # Simulate restart by clearing the in-memory cache.
        ss._sessions.clear()
        ss._user_to_session.clear()

        with patch("src.agent.JobAgent.__init__", return_value=None):
            rehydrated = ss.rehydrate_session_from_db("user-123")

        assert rehydrated == sid
        # Session is back in the in-memory cache.
        assert rehydrated in ss._sessions
        assert ss._user_to_session.get("user-123") == rehydrated

    def test_rehydrate_without_profile_returns_none(self):
        import src.session_store as ss
        # No profile seeded, no persisted session → None.
        assert ss.rehydrate_session_from_db("ghost-user") is None

    def test_rehydrate_without_persisted_row_returns_none(self):
        """Profile exists but no SessionORM row → None."""
        import src.session_store as ss
        _seed_user_profile("no-session-user", firebase_uid="no-session-user")
        assert ss.rehydrate_session_from_db("no-session-user") is None
