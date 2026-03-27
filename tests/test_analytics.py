"""Tests for ApplicationTracker (no Anthropic API calls needed)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.analytics import ApplicationTracker
from src.models import ApplicationRecord, ApplicationStatus


@pytest.fixture
def tracker(fresh_db):
    from src.models import Base, get_engine
    from sqlalchemy.orm import sessionmaker
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Mock AI insight.")]
    )
    yield ApplicationTracker(session=session, client=mock_client)
    session.close()


def _ensure_parent_rows(session, user_id: str, job_id: str):
    """Insert parent UserProfile and JobListing rows if they don't exist."""
    from src.models import UserProfileORM, JobListingORM
    if not session.query(UserProfileORM).filter_by(id=user_id).first():
        session.add(UserProfileORM(
            id=user_id, name_enc="test", email_enc="test@test.com",
            location="Test", skills=[], experience_level="mid",
            education=[], work_history=[], desired_roles=[],
            desired_job_types=[], languages=[], certifications=[],
        ))
    if not session.query(JobListingORM).filter_by(id=job_id).first():
        session.add(JobListingORM(
            id=job_id, title="Test Job", company="Test Co",
            location="Test", description="Test description",
            requirements=[], nice_to_have=[], keywords=[],
        ))
    session.flush()


def _make_record(
    user_id: str,
    status: ApplicationStatus = ApplicationStatus.SUBMITTED,
    session=None,
) -> ApplicationRecord:
    job_id = str(uuid.uuid4())
    if session is not None:
        _ensure_parent_rows(session, user_id, job_id)
    return ApplicationRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        job_id=job_id,
        status=status,
        submitted_at=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
    )


def test_add_and_retrieve_application(tracker):
    uid = "user-1"
    rec = _make_record(uid, session=tracker._session)
    tracker.add_application(rec)
    apps = tracker.get_applications(uid)
    assert len(apps) == 1
    assert apps[0].id == rec.id


def test_update_status(tracker):
    uid = "user-2"
    rec = _make_record(uid, session=tracker._session)
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
    tracker.add_application(_make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session))
    rec2 = _make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session)
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
    tracker.add_application(_make_record(uid, session=tracker._session))
    insights = tracker.generate_insights(uid)
    assert isinstance(insights, str)
    assert len(insights) > 0
