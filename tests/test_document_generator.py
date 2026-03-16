"""Tests for document generator (mocked LLM calls)."""
from __future__ import annotations

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


class TestDocumentGenerator:
    def test_generate_resume(self):
        resume_text = '## Jane Doe\nSenior Engineer\n```json\n{"tailoring_notes":"Emphasized AWS"}\n```'
        gen = DocumentGenerator(client=_mock_client(resume_text))
        doc = gen.generate_resume(_profile(), _job(), tone="professional")
        assert doc.doc_type == "resume"
        assert doc.content  # body is non-empty
        assert "AWS" in doc.tailoring_notes

    def test_generate_cover_letter(self):
        cl_text = 'Dear Hiring Manager,\nI am excited...\n```json\n{"tailoring_notes":"Focused on Python"}\n```'
        gen = DocumentGenerator(client=_mock_client(cl_text))
        doc = gen.generate_cover_letter(_profile(), _job())
        assert doc.doc_type == "cover_letter"
        assert doc.content

    def test_resume_no_tailoring_notes(self):
        gen = DocumentGenerator(client=_mock_client("Just a resume, no JSON block."))
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
        gen = DocumentGenerator(client=_mock_client("Body\n```json\nnot valid json\n```"))
        doc = gen.generate_resume(_profile(), _job())
        assert doc.content == "Body"
        assert doc.tailoring_notes == "not valid json"
