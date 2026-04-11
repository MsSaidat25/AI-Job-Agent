"""Tests for the privacy ledger and EU AI Act compliance export."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def session(fresh_db):
    """Fresh SQLite session with all ORM tables created."""
    from src.models import Base, get_engine
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _seed_user(session, user_id: str = "user-pl-1") -> str:
    from src.models import UserProfileORM
    if not session.query(UserProfileORM).filter_by(id=user_id).first():
        session.add(UserProfileORM(
            id=user_id, name_enc="n", email_enc="e@test", location="Earth",
            skills=[], experience_level="mid",
            education=[], work_history=[], desired_roles=[],
            desired_job_types=[], languages=[], certifications=[],
        ))
        session.commit()
    return user_id


class TestLogEvent:
    def test_happy_path(self, session):
        from src.privacy_ledger import log_event, get_ledger

        uid = _seed_user(session)
        row_id = log_event(
            session,
            user_id=uid,
            action="tool.generate_resume",
            tool_name="generate_resume",
            data_categories=["profile", "resume_content", "job_description"],
            purpose="document generation",
            llm_provider="anthropic",
            llm_model="claude-opus-4-6",
            retention_days=90,
            details={"tokens": 1234},
        )
        assert row_id is not None
        ledger = get_ledger(session, uid)
        assert len(ledger) == 1
        entry = ledger[0]
        assert entry["action"] == "tool.generate_resume"
        assert "profile" in entry["data_categories"]
        assert entry["llm_provider"] == "anthropic"
        assert entry["details"]["tokens"] == 1234

    def test_unknown_category_dropped(self, session):
        from src.privacy_ledger import log_event, get_ledger

        uid = _seed_user(session, "user-pl-unknown")
        log_event(
            session,
            user_id=uid,
            action="test",
            data_categories=["profile", "not-a-real-category"],
        )
        entry = get_ledger(session, uid)[0]
        assert entry["data_categories"] == ["profile"]

    def test_db_failure_returns_none(self, session, monkeypatch):
        """Ledger is advisory -- a DB failure must not raise."""
        from src.privacy_ledger import log_event

        uid = _seed_user(session, "user-pl-err")

        def _boom(*a, **kw):
            raise RuntimeError("db down")

        monkeypatch.setattr(session, "add", _boom)
        result = log_event(
            session, user_id=uid, action="x", data_categories=["profile"],
        )
        assert result is None


class TestGetLedger:
    def test_newest_first_ordering(self, session):
        from src.privacy_ledger import log_event, get_ledger

        uid = _seed_user(session, "user-pl-order")
        log_event(session, user_id=uid, action="a")
        log_event(session, user_id=uid, action="b")
        log_event(session, user_id=uid, action="c")
        actions = [e["action"] for e in get_ledger(session, uid)]
        assert actions == ["c", "b", "a"]

    def test_limit_applied(self, session):
        from src.privacy_ledger import log_event, get_ledger

        uid = _seed_user(session, "user-pl-limit")
        for i in range(5):
            log_event(session, user_id=uid, action=f"act-{i}")
        assert len(get_ledger(session, uid, limit=2)) == 2

    def test_since_filter(self, session):
        from src.models import PrivacyLedgerORM
        from src.privacy_ledger import get_ledger

        uid = _seed_user(session, "user-pl-since")
        old = datetime.now(timezone.utc) - timedelta(days=60)
        recent = datetime.now(timezone.utc)
        session.add(PrivacyLedgerORM(
            user_id=uid, action="old-event", data_categories=["profile"],
            created_at=old,
        ))
        session.add(PrivacyLedgerORM(
            user_id=uid, action="recent-event", data_categories=["profile"],
            created_at=recent,
        ))
        session.commit()

        recent_only = get_ledger(session, uid, since=datetime.now(timezone.utc) - timedelta(days=7))
        actions = [e["action"] for e in recent_only]
        assert "recent-event" in actions
        assert "old-event" not in actions


class TestExportForUser:
    def test_export_shape_and_fields(self, session):
        from src.privacy_ledger import export_for_user, log_event

        uid = _seed_user(session, "user-pl-export")
        log_event(
            session, user_id=uid,
            action="tool.search_jobs",
            tool_name="search_jobs",
            data_categories=["profile", "job_description"],
            purpose="match scoring",
            llm_provider="anthropic",
            llm_model="claude-opus-4-6",
            retention_days=30,
        )
        log_event(
            session, user_id=uid,
            action="tool.generate_resume",
            tool_name="generate_resume",
            data_categories=["profile", "resume_content"],
            purpose="document generation",
            retention_days=90,
        )
        bundle = export_for_user(session, uid)

        # Top-level fields required by the EU AI Act alignment.
        assert bundle["user_id"] == uid
        assert "generated_at" in bundle
        assert bundle["system"]["operator"] == "AVIEN SOLUTIONS INC"
        assert bundle["risk_classification"]["eu_ai_act_category"] == "limited_risk"
        assert "human_oversight" in bundle["risk_classification"]

        # Roll-ups over the entries.
        assert bundle["counts"]["total_events"] == 2
        assert bundle["counts"]["by_action"]["tool.search_jobs"] == 1
        assert bundle["counts"]["by_category"]["profile"] == 2
        assert "resume_content" in bundle["data_categories_processed"]
        assert bundle["retention_summary_days"]["resume_content"] == 90
        assert bundle["retention_summary_days"]["job_description"] == 30
        assert len(bundle["entries"]) == 2

    def test_export_windowing(self, session):
        from src.models import PrivacyLedgerORM
        from src.privacy_ledger import export_for_user

        uid = _seed_user(session, "user-pl-window")
        # Old event outside the window
        session.add(PrivacyLedgerORM(
            user_id=uid, action="stale", data_categories=["profile"],
            retention_days=30,
            created_at=datetime.now(timezone.utc) - timedelta(days=500),
        ))
        # Recent event inside the window
        session.add(PrivacyLedgerORM(
            user_id=uid, action="fresh", data_categories=["profile"],
            retention_days=30,
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()

        bundle = export_for_user(session, uid, window_days=90)
        assert bundle["counts"]["total_events"] == 1
        assert bundle["entries"][0]["action"] == "fresh"
