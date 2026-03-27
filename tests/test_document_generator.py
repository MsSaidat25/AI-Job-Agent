"""Tests for document generator (mocked LLM calls)."""
from __future__ import annotations

import json

from unittest.mock import MagicMock

from src.document_generator import DocumentGenerator
from src.models import ExperienceLevel, JobListing, UserProfile


def _profile() -> UserProfile:
    return UserProfile(
        name="Jane Doe",
        email="jane@example.com",
        location="Austin, TX",
        skills=["Python", "AWS", "FastAPI"],
        experience_level=ExperienceLevel.SENIOR,
        years_of_experience=8,
        desired_roles=["Backend Engineer"],
        education=[{"degree": "B.Sc. CS", "school": "UT Austin", "graduation_year": "2018"}],
        work_history=[{"title": "Senior Engineer", "company": "TechCo", "start": "2020-01", "end": "present"}],
    )


def _job() -> JobListing:
    return JobListing(
        title="Staff Backend Engineer",
        company="MegaCorp",
        location="Austin, TX",
        description="Build scalable APIs with Python and AWS.",
        requirements=["Python", "AWS", "System Design"],
        industry="Technology",
    )


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(type="text", text=response_text)]
    )
    return client


def _mock_client_multi(*responses: str) -> MagicMock:
    """Mock client that returns different responses for sequential calls."""
    client = MagicMock()
    client.messages.create.side_effect = [
        MagicMock(content=[MagicMock(type="text", text=r)]) for r in responses
    ]
    return client


class TestDocumentGenerator:
    def test_generate_resume_with_ats(self):
        resume_text = '## Jane Doe\nSenior Engineer\n```json\n{"tailoring_notes":"Emphasized AWS"}\n```'
        ats_response = json.dumps({
            "ats_score": 82,
            "missing_keywords": ["System Design"],
            "matched_keywords": ["Python", "AWS"],
            "suggestions": ["Add system design examples"],
        })
        gen = DocumentGenerator(client=_mock_client_multi(resume_text, ats_response))
        doc = gen.generate_resume(_profile(), _job(), tone="professional")
        assert doc.doc_type == "resume"
        assert doc.content
        assert "AWS" in doc.tailoring_notes
        assert doc.ats_score == 82
        assert "System Design" in doc.missing_keywords

    def test_generate_resume_no_ats(self):
        resume_text = '## Jane Doe\nSenior Engineer\n```json\n{"tailoring_notes":"Emphasized AWS"}\n```'
        gen = DocumentGenerator(client=_mock_client(resume_text))
        doc = gen.generate_resume(_profile(), _job(), tone="professional", auto_ats=False)
        assert doc.doc_type == "resume"
        assert doc.ats_score is None
        assert doc.missing_keywords == []

    def test_generate_cover_letter(self):
        cl_text = 'Dear Hiring Manager,\nI am excited...\n```json\n{"tailoring_notes":"Focused on Python"}\n```'
        gen = DocumentGenerator(client=_mock_client(cl_text))
        doc = gen.generate_cover_letter(_profile(), _job())
        assert doc.doc_type == "cover_letter"
        assert doc.content

    def test_resume_no_tailoring_notes(self):
        ats_response = json.dumps({"ats_score": 50, "missing_keywords": [], "matched_keywords": [], "suggestions": []})
        gen = DocumentGenerator(client=_mock_client_multi("Just a resume, no JSON block.", ats_response))
        doc = gen.generate_resume(_profile(), _job())
        assert doc.content == "Just a resume, no JSON block."
        assert doc.tailoring_notes == ""

    def test_suggest_improvements(self):
        gen = DocumentGenerator(client=_mock_client("1. Add metrics\n2. Improve keywords"))
        from src.models import GeneratedDocument

        doc = GeneratedDocument(
            user_id="u1", job_id="j1", doc_type="resume",
            content="My resume content here.",
        )
        suggestions = gen.suggest_improvements(doc, _job())
        assert "metrics" in suggestions.lower()

    def test_split_notes_handles_bad_json(self):
        ats_response = json.dumps({"ats_score": 0, "missing_keywords": [], "matched_keywords": [], "suggestions": []})
        gen = DocumentGenerator(client=_mock_client_multi("Body\n```json\nnot valid json\n```", ats_response))
        doc = gen.generate_resume(_profile(), _job())
        assert doc.content == "Body"
        assert doc.tailoring_notes == "not valid json"


class TestATSScoring:
    def test_score_ats_match(self):
        ats_response = json.dumps({
            "ats_score": 85,
            "missing_keywords": ["Kubernetes"],
            "matched_keywords": ["Python", "AWS"],
            "suggestions": ["Add K8s experience"],
        })
        gen = DocumentGenerator(client=_mock_client(ats_response))
        result = gen.score_ats_match("My resume with Python and AWS", "Job needs Python, AWS, Kubernetes")
        assert result["ats_score"] == 85
        assert "Kubernetes" in result["missing_keywords"]
        assert len(result["suggestions"]) >= 1

    def test_score_clamped_to_range(self):
        ats_response = json.dumps({
            "ats_score": 150,
            "missing_keywords": [],
            "matched_keywords": [],
            "suggestions": [],
        })
        gen = DocumentGenerator(client=_mock_client(ats_response))
        result = gen.score_ats_match("resume", "job desc")
        assert result["ats_score"] == 100

    def test_score_handles_bad_json(self):
        gen = DocumentGenerator(client=_mock_client("not json"))
        result = gen.score_ats_match("resume", "job desc")
        assert result["ats_score"] == 0
        assert "Unable to compute" in result["suggestions"][0]

    def test_score_handles_api_error(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("API down")
        gen = DocumentGenerator(client=client)
        result = gen.score_ats_match("resume", "job desc")
        assert result["ats_score"] == 0

    def test_score_strips_markdown_fences(self):
        ats_response = '```json\n{"ats_score": 75, "missing_keywords": [], "matched_keywords": ["Python"], "suggestions": []}\n```'
        gen = DocumentGenerator(client=_mock_client(ats_response))
        result = gen.score_ats_match("Python resume", "Python job")
        assert result["ats_score"] == 75
