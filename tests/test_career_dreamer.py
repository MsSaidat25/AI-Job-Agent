"""Tests for career dreamer module (mocked LLM calls)."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from src.career_dreamer import CareerDreamer
from src.models import (
    DreamScenario,
    DreamTimeline,
    ExperienceLevel,
    GapReport,
    UserProfile,
)


def _profile(**kwargs: Any) -> UserProfile:
    defaults: dict[str, Any] = dict(
        name="Test User",
        email="test@example.com",
        location="Berlin, Germany",
        skills=["Python", "SQL", "Docker"],
        experience_level=ExperienceLevel.MID,
        years_of_experience=4,
        desired_roles=["Data Engineer"],
    )
    defaults.update(kwargs)
    return UserProfile(**defaults)


def _dream(**kwargs: Any) -> DreamScenario:
    defaults: dict[str, Any] = dict(
        dream_role="Machine Learning Engineer",
        dream_industry="AI/ML",
        dream_location="San Francisco, CA",
        timeline_months=12,
    )
    defaults.update(kwargs)
    return DreamScenario(**defaults)


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(type="text", text=response_text)]
    )
    return client


class TestBuildGapReport:
    def test_returns_gap_report(self):
        response = json.dumps({
            "overlapping_skills": ["Python", "SQL"],
            "missing_skills": [
                {"skill": "PyTorch", "learning_time_weeks": 8, "priority": "high"},
                {"skill": "MLOps", "learning_time_weeks": 4, "priority": "medium"},
            ],
            "salary_current": 85000,
            "salary_dream": 150000,
            "feasibility_score": 72,
            "feasibility_rationale": "Strong Python base, needs ML specialisation.",
            "recommendations": ["Take a PyTorch course", "Build ML portfolio projects"],
        })
        dreamer = CareerDreamer(client=_mock_client(response))
        report = dreamer.build_gap_report(_profile(), _dream())

        assert isinstance(report, GapReport)
        assert report.dream_role == "Machine Learning Engineer"
        assert "Python" in report.overlapping_skills
        assert len(report.missing_skills) == 2
        assert report.feasibility_score == 72
        assert report.salary_dream == 150000
        assert len(report.recommendations) >= 1

    def test_feasibility_clamped_to_100(self):
        response = json.dumps({
            "overlapping_skills": [],
            "missing_skills": [],
            "feasibility_score": 150,
            "feasibility_rationale": "Perfect fit.",
            "recommendations": [],
        })
        dreamer = CareerDreamer(client=_mock_client(response))
        report = dreamer.build_gap_report(_profile(), _dream())
        assert report.feasibility_score == 100.0

    def test_feasibility_clamped_to_0(self):
        response = json.dumps({
            "overlapping_skills": [],
            "missing_skills": [],
            "feasibility_score": -10,
            "feasibility_rationale": "Not feasible.",
            "recommendations": [],
        })
        dreamer = CareerDreamer(client=_mock_client(response))
        report = dreamer.build_gap_report(_profile(), _dream())
        assert report.feasibility_score == 0.0

    def test_handles_api_error(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("API down")
        dreamer = CareerDreamer(client=client)
        report = dreamer.build_gap_report(_profile(), _dream())
        assert report.feasibility_score == 0.0
        assert "Unable to analyse" in report.feasibility_rationale

    def test_handles_empty_skills(self):
        response = json.dumps({
            "overlapping_skills": [],
            "missing_skills": [{"skill": "Everything", "learning_time_weeks": 52, "priority": "high"}],
            "feasibility_score": 20,
            "feasibility_rationale": "Major career shift.",
            "recommendations": ["Start from basics"],
        })
        dreamer = CareerDreamer(client=_mock_client(response))
        report = dreamer.build_gap_report(_profile(skills=[]), _dream())
        assert report.feasibility_score == 20


class TestScoreFeasibility:
    def test_returns_existing_score(self):
        dreamer = CareerDreamer(client=_mock_client(""))
        report = GapReport(dream_role="ML Engineer", feasibility_score=75.0)
        assert dreamer.score_feasibility(report) == 75.0

    def test_recalculates_when_zero(self):
        response = json.dumps({"feasibility_score": 60, "rationale": "Moderate difficulty."})
        dreamer = CareerDreamer(client=_mock_client(response))
        report = GapReport(dream_role="ML Engineer", feasibility_score=0)
        score = dreamer.score_feasibility(report)
        assert score == 60.0

    def test_handles_api_error(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("fail")
        dreamer = CareerDreamer(client=client)
        report = GapReport(dream_role="ML Engineer", feasibility_score=0)
        assert dreamer.score_feasibility(report) == 0.0


class TestBuildTimeline:
    def test_returns_timeline(self):
        response = json.dumps({
            "milestones": [
                {"week": 1, "goal": "Learn basics", "actions": ["Enroll in course"], "deliverable": "Course enrolled"},
                {"week": 4, "goal": "Build project", "actions": ["Start portfolio"], "deliverable": "First project done"},
            ]
        })
        dreamer = CareerDreamer(client=_mock_client(response))
        report = GapReport(
            dream_role="ML Engineer",
            missing_skills=[{"skill": "PyTorch", "learning_time_weeks": 8, "priority": "high"}],
            recommendations=["Learn PyTorch"],
        )
        timeline = dreamer.build_timeline(report, months=6)
        assert isinstance(timeline, DreamTimeline)
        assert timeline.total_weeks == 24
        assert len(timeline.milestones) == 2

    def test_no_gaps_returns_immediate(self):
        dreamer = CareerDreamer(client=_mock_client(""))
        report = GapReport(dream_role="Data Engineer")
        timeline = dreamer.build_timeline(report)
        assert timeline.total_weeks == 0
        assert "already have" in timeline.milestones[0]["goal"].lower()

    def test_handles_api_error(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("fail")
        dreamer = CareerDreamer(client=client)
        report = GapReport(
            dream_role="ML Engineer",
            missing_skills=[{"skill": "TensorFlow", "learning_time_weeks": 6, "priority": "high"}],
        )
        timeline = dreamer.build_timeline(report, months=6)
        assert timeline.milestones == []
        assert timeline.total_weeks == 24
