"""Tests for data models."""
from typing import Any

from sqlalchemy import text

from src.models import (
    ApplicationRecord,
    ApplicationStatus,
    DreamScenario,
    DreamTimeline,
    ExperienceLevel,
    GapReport,
    GeneratedDocument,
    JobListing,
    JobType,
    MarketInsight,
    UserProfile,
)


def make_profile(**kwargs: Any) -> UserProfile:
    defaults: dict[str, Any] = dict(
        name="Jane Doe",
        email="jane@example.com",
        location="Berlin, Germany",
        skills=["Python", "SQL", "Docker"],
        experience_level=ExperienceLevel.MID,
        years_of_experience=4,
        desired_roles=["Data Engineer", "Backend Developer"],
        desired_job_types=[JobType.FULL_TIME, JobType.REMOTE],
    )
    defaults.update(kwargs)
    return UserProfile(**defaults)


def make_job(**kwargs: Any) -> JobListing:
    defaults: dict[str, Any] = dict(
        title="Data Engineer",
        company="DataCo",
        location="Berlin, Germany",
        description="Build ETL pipelines.",
        requirements=["Python", "SQL", "Spark"],
        industry="Technology",
        source_platform="LinkedIn",
    )
    defaults.update(kwargs)
    return JobListing(**defaults)


def test_user_profile_deduplication():
    p = make_profile(skills=["Python", "SQL", "Python"])
    assert p.skills.count("Python") == 1


def test_user_profile_defaults():
    p = make_profile()
    assert p.languages == ["English"]
    assert p.certifications == []


def test_job_listing_defaults():
    j = make_job()
    assert j.remote_allowed is False
    assert j.job_type == JobType.FULL_TIME
    assert j.match_score is None


def test_application_record_status_default():
    ar = ApplicationRecord(user_id="u1", job_id="j1")
    assert ar.status == ApplicationStatus.DRAFT


def test_market_insight_fields():
    mi = MarketInsight(
        region="Singapore",
        industry="Finance",
        top_skills_in_demand=["Python", "Risk Management"],
        avg_salary_usd=90_000,
        competition_level="high",
        trending_roles=["Quant Analyst"],
    )
    assert mi.region == "Singapore"
    assert mi.competition_level == "high"


def test_dream_scenario_defaults():
    ds = DreamScenario(dream_role="ML Engineer")
    assert ds.timeline_months == 12
    assert ds.dream_industry == ""


def test_gap_report_fields():
    gr = GapReport(
        dream_role="ML Engineer",
        overlapping_skills=["Python"],
        missing_skills=[{"skill": "PyTorch", "learning_time_weeks": 8, "priority": "high"}],
        feasibility_score=72.5,
    )
    assert gr.dream_role == "ML Engineer"
    assert gr.feasibility_score == 72.5
    assert len(gr.missing_skills) == 1


def test_dream_timeline_fields():
    dt = DreamTimeline(
        dream_role="ML Engineer",
        total_weeks=48,
        milestones=[{"week": 1, "goal": "Learn basics", "actions": [], "deliverable": "Course done"}],
    )
    assert dt.total_weeks == 48
    assert len(dt.milestones) == 1


def test_generated_document_ats_fields():
    doc = GeneratedDocument(
        user_id="u1", job_id="j1", doc_type="resume", content="Resume text",
        ats_score=85.0, missing_keywords=["Kubernetes"],
    )
    assert doc.ats_score == 85.0
    assert "Kubernetes" in doc.missing_keywords


def test_db_init_creates_tables(fresh_db):
    """init_db should create tables without error in a temp dir."""
    from src.models import Base, get_engine
    engine = get_engine()
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    table_names = {t[0] for t in tables}
    assert "user_profiles" in table_names
    assert "job_listings" in table_names
    assert "application_records" in table_names
    assert "career_dreams" in table_names
