"""Tests for ApplicationTracker (no Anthropic API calls needed)."""
from __future__ import annotations

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


# ── P3.2 resume A/B response-rate loop ────────────────────────────────────

def _add_variant(
    session, user_id: str, application_id: str, job_id: str,
    tone: str = "professional", ats: float | None = None,
) -> str:
    from src.models import DocumentVariantORM
    vid = str(uuid.uuid4())
    session.add(DocumentVariantORM(
        id=vid,
        user_id=user_id,
        job_id=job_id,
        application_id=application_id,
        resume_content="resume body",
        resume_tone=tone,
        ats_score=ats,
    ))
    session.flush()
    return vid


class TestVariantPerformance:
    def test_empty_user(self, tracker):
        data = tracker.compute_variant_performance("nobody")
        assert data["variants"] == []
        assert data["winning_variant_id"] is None
        assert data["total_variants"] == 0

    def test_variants_without_applications_ignored(self, tracker):
        from src.models import DocumentVariantORM
        uid = "user-ab-0"
        # A bare variant with no application_id should not appear.
        _ensure_parent_rows(tracker._session, uid, "job-x")
        tracker._session.add(DocumentVariantORM(
            id=str(uuid.uuid4()), user_id=uid, job_id="job-x",
            application_id=None, resume_content="x", resume_tone="creative",
        ))
        tracker._session.flush()
        data = tracker.compute_variant_performance(uid)
        assert data["variants"] == []

    def test_per_tone_response_rates(self, tracker):
        uid = "user-ab-1"
        # Two "professional" variants, one got a response, one did not.
        rec_a = _make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session)
        tracker.add_application(rec_a)
        _add_variant(tracker._session, uid, rec_a.id, rec_a.job_id, tone="professional", ats=82)

        rec_b = _make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session)
        tracker.add_application(rec_b)
        tracker.update_status(rec_b.id, ApplicationStatus.INTERVIEW_SCHEDULED)
        _add_variant(tracker._session, uid, rec_b.id, rec_b.job_id, tone="professional", ats=90)

        # One "creative" variant, still awaiting response (SUBMITTED).
        rec_c = _make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session)
        tracker.add_application(rec_c)
        _add_variant(tracker._session, uid, rec_c.id, rec_c.job_id, tone="creative", ats=70)
        tracker._session.commit()

        data = tracker.compute_variant_performance(uid)
        assert data["total_variants"] == 2
        by_tone = {v["resume_tone"]: v for v in data["variants"]}
        assert by_tone["professional"]["submitted"] == 2
        assert by_tone["professional"]["responses"] == 1
        assert by_tone["professional"]["interviews"] == 1
        assert by_tone["professional"]["response_rate"] == 0.5
        assert by_tone["professional"]["avg_ats_score"] == 86.0
        assert by_tone["creative"]["response_rate"] == 0.0

    def test_winner_needs_margin_and_samples(self, tracker):
        uid = "user-ab-2"
        # Not enough samples to declare a winner.
        for _ in range(2):
            rec = _make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session)
            tracker.add_application(rec)
            tracker.update_status(rec.id, ApplicationStatus.INTERVIEW_SCHEDULED)
            _add_variant(tracker._session, uid, rec.id, rec.job_id, tone="technical")
        tracker._session.commit()
        data = tracker.compute_variant_performance(uid)
        assert data["winning_variant_id"] is None  # only 2 submissions

    def test_winner_declared_with_margin(self, tracker):
        uid = "user-ab-3"
        # technical: 3 submissions, 3 responses (100%)
        tech_vids: list[str] = []
        for _ in range(3):
            rec = _make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session)
            tracker.add_application(rec)
            tracker.update_status(rec.id, ApplicationStatus.INTERVIEW_SCHEDULED)
            tech_vids.append(_add_variant(
                tracker._session, uid, rec.id, rec.job_id, tone="technical"
            ))
        # professional: 3 submissions, 0 responses
        for _ in range(3):
            rec = _make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session)
            tracker.add_application(rec)
            _add_variant(tracker._session, uid, rec.id, rec.job_id, tone="professional")
        tracker._session.commit()

        data = tracker.compute_variant_performance(uid)
        # Winner must be one of the technical variants -- which specific
        # row is surfaced depends on query ordering, so we only assert
        # that the winning_variant_id is drawn from the technical tone.
        assert data["winning_variant_id"] in tech_vids
        by_tone = {v["resume_tone"]: v for v in data["variants"]}
        assert by_tone["technical"]["response_rate"] == 1.0
        assert by_tone["professional"]["response_rate"] == 0.0

    def test_mark_winning_variant_persists(self, tracker):
        uid = "user-ab-4"
        rec = _make_record(uid, ApplicationStatus.SUBMITTED, session=tracker._session)
        tracker.add_application(rec)
        vid = _add_variant(tracker._session, uid, rec.id, rec.job_id, tone="creative")
        tracker._session.commit()

        assert tracker.mark_winning_variant(vid) is True

        from src.models import DocumentVariantORM
        row = tracker._session.query(DocumentVariantORM).filter_by(id=vid).first()
        assert row is not None and row.status == "winning"

    def test_mark_winning_variant_missing(self, tracker):
        assert tracker.mark_winning_variant("no-such-variant") is False
