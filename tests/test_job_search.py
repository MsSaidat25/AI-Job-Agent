"""Tests for job search module (no external API calls)."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from src.job_search import (
    JobSearchEngine,
    MarketInsightLLM,
    MarketIntelligenceService,
    _build_query,
    _dedup_fingerprint,
    _score_job,
    _to_listing,
)
from src.models import ExperienceLevel, JobType, UserProfile


def _profile(**kwargs: Any) -> UserProfile:
    defaults: dict[str, Any] = dict(
        name="Test User",
        email="test@example.com",
        location="Berlin, Germany",
        skills=["Python", "SQL"],
        experience_level=ExperienceLevel.MID,
        desired_roles=["Data Engineer"],
        desired_job_types=[JobType.FULL_TIME, JobType.REMOTE],
    )
    defaults.update(kwargs)
    return UserProfile(**defaults)


def _raw_job(**overrides) -> dict:
    base = {
        "job_id": "test-123",
        "job_title": "Data Engineer",
        "employer_name": "TestCo",
        "job_description": "Build data pipelines with Python and SQL.",
        "job_city": "Berlin",
        "job_state": "",
        "job_country": "DE",
        "job_is_remote": False,
        "job_employment_type": "full_time",
        "job_min_salary": 60000,
        "job_max_salary": 90000,
        "job_publisher": "LinkedIn",
        "job_apply_link": "https://example.com/apply",
        "job_posted_at_datetime_utc": "2026-01-15T00:00:00Z",
    }
    base.update(overrides)
    return base


class TestBuildQuery:
    def test_default(self):
        p = _profile()
        q = _build_query(p)
        assert "Data Engineer" in q
        assert "Berlin" in q

    def test_location_override(self):
        p = _profile()
        q = _build_query(p, location_filter="London")
        assert "London" in q

    def test_no_desired_roles(self):
        p = _profile(desired_roles=[])
        q = _build_query(p)
        assert "software engineer" in q


class TestScoreJob:
    def test_skill_match_boosts_score(self):
        p = _profile(skills=["Python", "SQL"])
        job = _raw_job(job_description="We need Python and SQL experts.")
        score, rationale = _score_job(job, p)
        assert score > 50
        assert "Python" in rationale

    def test_title_match_boosts_score(self):
        p = _profile(desired_roles=["Data Engineer"])
        job = _raw_job(job_title="Senior Data Engineer")
        score, _ = _score_job(job, p)
        assert score > 50

    def test_remote_match_with_enum_types(self):
        """Item #4: Ensures enum .value comparison works."""
        p = _profile(desired_job_types=[JobType.REMOTE])
        job = _raw_job(job_is_remote=True)
        score, rationale = _score_job(job, p)
        assert "Remote" in rationale

    def test_score_clamped_to_100(self):
        p = _profile(
            skills=["Python", "SQL", "Spark", "Kafka", "AWS", "Docker", "K8s"],
            desired_roles=["Data Engineer"],
        )
        job = _raw_job(
            job_description="Python SQL Spark Kafka AWS Docker K8s",
            job_title="Data Engineer",
            job_is_remote=True,
        )
        score, _ = _score_job(job, p)
        assert score <= 100


class TestToListing:
    def test_creates_job_listing(self):
        p = _profile()
        listing = _to_listing(_raw_job(), p)
        assert listing.title == "Data Engineer"
        assert listing.company == "TestCo"
        assert listing.location == "Berlin, DE"
        assert listing.salary_min == 60000

    def test_handles_missing_fields(self):
        p = _profile()
        listing = _to_listing({"job_id": "x"}, p)
        assert listing.title == "Untitled Role"
        assert listing.company == "Unknown Company"


class TestJobSearchEngine:
    @patch("src.job_search._jsearch_sync")
    def test_search_returns_sorted_listings(self, mock_sync):
        mock_sync.return_value = [
            _raw_job(job_id="a", job_title="Junior Role"),
            _raw_job(job_id="b", job_title="Data Engineer"),
        ]
        engine = JobSearchEngine(client=MagicMock())
        results = engine.search(_profile(), max_results=5)
        assert len(results) == 2
        assert results[0].match_score >= results[1].match_score  # type: ignore[operator]

    def test_filter_by_location(self):
        engine = JobSearchEngine(client=MagicMock())
        from src.models import JobListing

        listings = [
            JobListing(title="A", company="C", location="Berlin, DE", description="x"),
            JobListing(title="B", company="C", location="London, UK", description="x"),
            JobListing(title="C", company="C", location="Remote", description="x", remote_allowed=True),
        ]
        filtered = engine.filter_by_location(listings, "Berlin", include_remote=True)
        assert any("Berlin" in j.location for j in filtered)


class TestSkillGapAnalysis:
    @patch("src.job_search._jsearch_sync")
    def test_analyze_skill_gaps(self, mock_sync):
        mock_sync.return_value = [
            _raw_job(job_id="a", job_description="We need Python, SQL, Spark, Kafka."),
            _raw_job(job_id="b", job_description="Python, SQL, AWS, Docker required."),
        ]
        gap_response = json.dumps({
            "must_have_gaps": [{"skill": "Spark", "frequency_pct": 80}],
            "nice_to_have_gaps": [{"skill": "Kafka", "frequency_pct": 50}],
            "hidden_strengths": ["SQL"],
            "upskill_roi": [{"skill": "Spark", "estimated_salary_bump_pct": 15, "learning_effort": "medium"}],
        })
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(type="text", text=gap_response)]
        )
        engine = JobSearchEngine(client=mock_client)
        result = engine.analyze_skill_gaps(_profile())
        assert len(result["must_have_gaps"]) >= 1
        assert len(result["upskill_roi"]) >= 1

    @patch("src.job_search._jsearch_sync")
    def test_analyze_skill_gaps_no_jobs(self, mock_sync):
        mock_sync.return_value = []
        engine = JobSearchEngine(client=MagicMock())
        result = engine.analyze_skill_gaps(_profile())
        assert "analysis_note" in result

    @patch("src.job_search._jsearch_sync")
    def test_analyze_skill_gaps_api_error(self, mock_sync):
        mock_sync.return_value = [_raw_job()]
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API down")
        engine = JobSearchEngine(client=mock_client)
        result = engine.analyze_skill_gaps(_profile())
        assert "error" in result


class TestMarketIntelligenceService:
    def test_get_insights_returns_model(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(type="text", text='{"summary":"Good market","top_skills":["Python"],"hiring_trend":"up"}')]
        )
        svc = MarketIntelligenceService(client=mock_client)
        result = svc.get_insights("Berlin", "Tech")
        assert isinstance(result, MarketInsightLLM)
        assert result.region == "Berlin"
        assert "Python" in result.top_skills

    def test_get_insights_handles_error(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API down")
        svc = MarketIntelligenceService(client=mock_client)
        result = svc.get_insights("Berlin", "Tech")
        assert "unavailable" in result.summary

    def test_get_application_tips(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(type="text", text="Tip: Be concise.")]
        )
        svc = MarketIntelligenceService(client=mock_client)
        tips = svc.get_application_tips("Germany")
        assert "concise" in tips.lower()


class TestDedupFingerprint:
    """P2: search_jobs_live must dedupe across providers that assign
    different ``job_id`` values to the same underlying posting."""

    def test_same_posting_different_job_ids(self):
        jsearch_variant = {
            "job_id": "jsearch-abc",
            "job_title": "Senior Backend Engineer",
            "employer_name": "Acme",
            "job_apply_link": "https://acme.example/apply/42?utm_source=jsearch",
        }
        adzuna_variant = {
            "job_id": "adzuna-xyz",
            "title": "  senior BACKEND engineer  ",
            "company": "acme",
            "redirect_url": "https://acme.example/apply/42?utm_source=adzuna",
        }
        fp_a = _dedup_fingerprint(jsearch_variant)
        fp_b = _dedup_fingerprint(adzuna_variant)
        assert fp_a == fp_b, (fp_a, fp_b)

    def test_different_postings_distinct(self):
        a = {
            "job_title": "Backend Engineer",
            "employer_name": "Acme",
            "job_apply_link": "https://acme.example/apply/1",
        }
        b = {
            "job_title": "Backend Engineer",
            "employer_name": "Beta",
            "job_apply_link": "https://beta.example/apply/1",
        }
        assert _dedup_fingerprint(a) != _dedup_fingerprint(b)


class TestJobSerializer:
    """P2: cached_to_job_detail must accept dict, Pydantic, and ORM inputs."""

    def test_dict_input(self):
        from routers._job_serializer import cached_to_job_detail
        cached = {
            "job_title": "Staff SWE",
            "employer_name": "Acme",
            "job_city": "Berlin",
            "job_state": "Berlin",
            "job_country": "DE",
            "job_is_remote": True,
            "job_employment_type": "full_time",
            "job_description": "desc",
            "job_apply_link": "https://acme.example/apply/1",
            "_source": "JSearch",
            "_match_score": 87,
            "_match_rationale": "strong Python overlap",
        }
        resp = cached_to_job_detail("j1", cached)
        assert resp.id == "j1"
        assert resp.title == "Staff SWE"
        assert resp.company == "Acme"
        assert resp.location == "Berlin, Berlin, DE"
        assert resp.remote_allowed is True
        assert resp.source_url == "https://acme.example/apply/1"
        assert resp.source_platform == "JSearch"
        assert resp.match_score == 87

    def test_pydantic_input_with_job_type_enum(self):
        from routers._job_serializer import cached_to_job_detail
        from src.models import JobListing, JobType
        listing = JobListing(
            id="j2",
            title="Data Engineer",
            company="Beta",
            location="Remote",
            remote_allowed=True,
            job_type=JobType.FULL_TIME,
            description="desc",
            source_url="https://beta.example/apply",
        )
        resp = cached_to_job_detail("j2", listing)
        assert resp.title == "Data Engineer"
        assert resp.job_type == "full_time"
        assert resp.source_url == "https://beta.example/apply"

    def test_is_saved_kwarg_propagates(self):
        from routers._job_serializer import cached_to_job_detail
        resp = cached_to_job_detail("j3", {"job_title": "T", "employer_name": "C"}, is_saved=True)
        assert resp.is_saved is True
