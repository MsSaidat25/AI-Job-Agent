"""Tests for JobAgent._dispatch_tool covering all 13 tool dispatches."""
# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.models import UserProfile


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_dispatch.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("src.models.DB_PATH", db_path)
    monkeypatch.setattr("src.models_bootstrap.DB_PATH", db_path)
    monkeypatch.setattr("config.settings.DATABASE_URL", "")
    monkeypatch.setattr("config.settings.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models.DATABASE_URL", "")
    monkeypatch.setattr("src.models.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL_FAILOVER", "")
    from src.models import reset_db_state
    reset_db_state()


def _make_agent():
    """Create a JobAgent with mocked subsystems."""
    from src.agent import JobAgent

    profile = UserProfile(
        name="Test User",
        email="test@example.com",
        location="Berlin",
        skills=["Python"],
        desired_roles=["Engineer"],
    )

    with patch("src.agent.get_llm_client", return_value=MagicMock()):
        agent = JobAgent(profile=profile)

    # Replace real subsystems with mocks
    agent._search_engine = MagicMock()
    agent._market_svc = MagicMock()
    agent._doc_gen = MagicMock()
    agent._tracker = MagicMock()
    agent._career_dreamer = MagicMock()
    return agent


class TestDispatchTool:
    def test_search_jobs(self):
        agent = _make_agent()
        agent._search_engine.search.return_value = []
        result = json.loads(agent._dispatch_tool("search_jobs", {}))
        assert isinstance(result, list)

    def test_get_market_insights(self):
        agent = _make_agent()
        from src.models import MarketInsight
        agent._market_svc.get_insights.return_value = MarketInsight(
            region="Berlin", industry="Tech",
        )
        result = json.loads(agent._dispatch_tool("get_market_insights", {
            "region": "Berlin", "industry": "Tech",
        }))
        assert result["region"] == "Berlin"

    def test_get_application_tips(self):
        agent = _make_agent()
        agent._market_svc.get_application_tips.return_value = "Tips for Japan"
        result = agent._dispatch_tool("get_application_tips", {"region": "Japan"})
        assert "Japan" in result

    def test_generate_resume_missing_job(self):
        agent = _make_agent()
        result = json.loads(agent._dispatch_tool("generate_resume", {"job_id": "nonexistent"}))
        assert "error" in result

    def test_generate_resume_with_cached_job(self):
        agent = _make_agent()
        from src.models import JobListing
        job = JobListing(title="Dev", company="Co", location="Berlin", description="Build stuff")
        agent._job_cache["j1"] = job
        agent._doc_gen.generate_resume.return_value = MagicMock(
            id="d1", doc_type="resume", content="# Resume", tailoring_notes="Tailored",
        )
        result = json.loads(agent._dispatch_tool("generate_resume", {"job_id": "j1"}))
        assert result["doc_type"] == "resume"

    def test_generate_cover_letter_missing_job(self):
        agent = _make_agent()
        result = json.loads(agent._dispatch_tool("generate_cover_letter", {"job_id": "nope"}))
        assert "error" in result

    def test_generate_cover_letter_with_cached_job(self):
        agent = _make_agent()
        from src.models import JobListing
        job = JobListing(title="Dev", company="Co", location="Berlin", description="Build stuff")
        agent._job_cache["j2"] = job
        agent._doc_gen.generate_cover_letter.return_value = MagicMock(
            id="d2", doc_type="cover_letter", content="Dear...", tailoring_notes="Notes",
        )
        result = json.loads(agent._dispatch_tool("generate_cover_letter", {"job_id": "j2"}))
        assert result["doc_type"] == "cover_letter"

    def test_track_application(self):
        agent = _make_agent()
        agent._tracker.add_application.return_value = None
        result = json.loads(agent._dispatch_tool("track_application", {"job_id": "j1"}))
        assert "application_id" in result
        assert result["status"] == "submitted"

    def test_update_application(self):
        agent = _make_agent()
        agent._tracker.update_status.return_value = True
        import uuid
        app_id = str(uuid.uuid4())
        result = json.loads(agent._dispatch_tool("update_application", {
            "application_id": app_id, "new_status": "interview_scheduled",
        }))
        assert result["new_status"] == "interview_scheduled"

    def test_update_application_invalid_id(self):
        agent = _make_agent()
        result = json.loads(agent._dispatch_tool("update_application", {
            "application_id": "not-a-uuid", "new_status": "submitted",
        }))
        assert "error" in result

    def test_list_applications_empty(self):
        agent = _make_agent()
        agent._tracker.get_applications.return_value = []
        result = json.loads(agent._dispatch_tool("list_applications", {}))
        assert result["total"] == 0

    def test_get_analytics(self):
        agent = _make_agent()
        agent._tracker.compute_metrics.return_value = {"total": 0}
        agent._tracker.generate_insights.return_value = "No data yet."
        result = json.loads(agent._dispatch_tool("get_analytics", {}))
        assert "metrics" in result
        assert "insights" in result

    def test_get_feedback_analysis(self):
        agent = _make_agent()
        agent._tracker.employer_feedback_analysis.return_value = '{"patterns": []}'
        result = agent._dispatch_tool("get_feedback_analysis", {})
        assert "patterns" in result

    def test_career_dreamer(self):
        agent = _make_agent()
        agent._career_dreamer.build_gap_report.return_value = MagicMock(
            feasibility_score=75.0,
            feasibility_rationale="Good fit",
            overlapping_skills=["Python"],
            missing_skills=[],
            salary_current=80000,
            salary_dream=120000,
            recommendations=["Learn ML"],
        )
        agent._career_dreamer.build_timeline.return_value = MagicMock(
            total_weeks=48, milestones=[],
        )
        result = json.loads(agent._dispatch_tool("career_dreamer", {"dream_role": "ML Engineer"}))
        assert result["feasibility_score"] == 75.0

    def test_analyze_skill_gaps(self):
        agent = _make_agent()
        agent._search_engine.analyze_skill_gaps.return_value = {"gaps": []}
        result = json.loads(agent._dispatch_tool("analyze_skill_gaps", {}))
        assert "gaps" in result

    def test_score_ats_match_missing_job(self):
        agent = _make_agent()
        result = json.loads(agent._dispatch_tool("score_ats_match", {"job_id": "nope"}))
        assert "error" in result

    def test_score_ats_match_no_resume(self):
        agent = _make_agent()
        from src.models import JobListing
        job = JobListing(title="Dev", company="Co", location="Berlin", description="Build stuff")
        agent._job_cache["j1"] = job
        result = json.loads(agent._dispatch_tool("score_ats_match", {"job_id": "j1"}))
        assert "error" in result

    def test_unknown_tool(self):
        agent = _make_agent()
        result = json.loads(agent._dispatch_tool("nonexistent_tool", {}))
        assert "error" in result
        assert "Unknown tool" in result["error"]

    def test_tool_exception_returns_error(self):
        agent = _make_agent()
        agent._search_engine.search.side_effect = RuntimeError("boom")
        result = json.loads(agent._dispatch_tool("search_jobs", {}))
        assert "error" in result
