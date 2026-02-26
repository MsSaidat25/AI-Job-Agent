"""Tests for ApplicationTracker (no Anthropic API calls needed)."""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.analytics import ApplicationTracker
from src.models import ApplicationRecord, ApplicationStatus, init_db


@pytest.fixture
def tracker(tmp_path, monkeypatch):
    monkeypatch.setattr("config.settings.DB_PATH", tmp_path / "test_analytics.db")
    from src.models import Base, get_engine
    from sqlalchemy.orm import sessionmaker
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Mock AI insight.")]
    )
    return ApplicationTracker(session=session, client=mock_client)


def _make_record(user_id: str, status: ApplicationStatus = ApplicationStatus.SUBMITTED) -> ApplicationRecord:
    return ApplicationRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        job_id=str(uuid.uuid4()),
        status=status,
        submitted_at=datetime.utcnow(),
        last_updated=datetime.utcnow(),
    )


def test_add_and_retrieve_application(tracker):
    uid = "user-1"
    rec = _make_record(uid)
    tracker.add_application(rec)
    apps = tracker.get_applications(uid)
    assert len(apps) == 1
    assert apps[0].id == rec.id


def test_update_status(tracker):
    uid = "user-2"
    rec = _make_record(uid)
    tracker.add_application(rec)
    updated = tracker.update_status(rec.id, ApplicationStatus.INTERVIEW_SCHEDULED)
    assert updated is not None
    assert updated.status == ApplicationStatus.INTERVIEW_SCHEDULED


def test_metrics_empty(tracker):
    metrics = tracker.compute_metrics("no-such-user")
    assert metrics["total"] == 0


def test_metrics_with_applications(tracker):
    uid = "user-3"
    # Add submitted + offer received
    tracker.add_application(_make_record(uid, ApplicationStatus.SUBMITTED))
    rec2 = _make_record(uid, ApplicationStatus.SUBMITTED)
    tracker.add_application(rec2)
    tracker.update_status(rec2.id, ApplicationStatus.OFFER_RECEIVED)

    metrics = tracker.compute_metrics(uid)
    assert metrics["total"] == 2
    assert metrics["submitted"] >= 1


def test_update_nonexistent_application(tracker):
    result = tracker.update_status("nonexistent-id", ApplicationStatus.REJECTED)
    assert result is None


def test_generate_insights_calls_llm(tracker):
    uid = "user-4"
    tracker.add_application(_make_record(uid))
    insights = tracker.generate_insights(uid)
    assert isinstance(insights, str)
    assert len(insights) > 0
