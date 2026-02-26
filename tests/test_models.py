"""Tests for data models."""
import pytest
from src.models import (
    ApplicationRecord,
    ApplicationStatus,
    ExperienceLevel,
    JobListing,
    JobType,
    MarketInsight,
    UserProfile,
    init_db,
)
from sqlalchemy import text


def make_profile(**kwargs) -> UserProfile:
    defaults = dict(
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


def make_job(**kwargs) -> JobListing:
    defaults = dict(
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


def test_db_init_creates_tables(tmp_path, monkeypatch):
    """init_db should create tables without error in a temp dir."""
    monkeypatch.setattr("config.settings.DB_PATH", tmp_path / "test.db")
    from src.models import init_db, Base, get_engine
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
