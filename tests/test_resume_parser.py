"""Tests for resume parser module (mocked LLM calls)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.models import ExperienceLevel, UserProfile
from src.resume_parser import ResumeParser, _get_extension


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(type="text", text=response_text)]
    )
    return client


_VALID_PARSE_RESPONSE = json.dumps({
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+1-555-0100",
    "location": "Austin, TX, USA",
    "skills": ["Python", "AWS", "FastAPI", "SQL"],
    "experience_level": "senior",
    "years_of_experience": 8,
    "education": [{"degree": "B.Sc. Computer Science", "school": "UT Austin", "graduation_year": "2018"}],
    "work_history": [
        {"title": "Senior Engineer", "company": "TechCo", "start": "2020-01", "end": "present", "highlights": ["Led team of 5"]},
    ],
    "desired_roles": ["Staff Engineer", "Backend Lead"],
    "languages": ["English", "Spanish"],
    "certifications": ["AWS Solutions Architect"],
    "portfolio_url": "https://janedoe.dev",
    "linkedin_url": "https://linkedin.com/in/janedoe",
    "confidence": {
        "name": 0.95,
        "email": 0.99,
        "skills": 0.85,
        "experience_level": 0.7,
        "years_of_experience": 0.6,
    },
})


class TestGetExtension:
    def test_pdf(self):
        assert _get_extension("resume.pdf") == ".pdf"

    def test_docx(self):
        assert _get_extension("my_resume.DOCX") == ".docx"

    def test_image(self):
        assert _get_extension("scan.PNG") == ".png"

    def test_no_extension(self):
        assert _get_extension("noext") == ""


class TestResumeParserParse:
    @patch("src.resume_parser._extract_text_from_pdf", return_value="Jane Doe\nSenior Engineer at TechCo")
    def test_parse_pdf(self, mock_extract):
        parser = ResumeParser(client=_mock_client(_VALID_PARSE_RESPONSE))
        result = parser.parse(b"fake-pdf-bytes", "resume.pdf")
        assert result["name"] == "Jane Doe"
        assert "Python" in result["skills"]
        assert result["confidence"]["name"] == 0.95

    @patch("src.resume_parser._extract_text_from_docx", return_value="Jane Doe\nSenior Engineer")
    def test_parse_docx(self, mock_extract):
        parser = ResumeParser(client=_mock_client(_VALID_PARSE_RESPONSE))
        result = parser.parse(b"fake-docx-bytes", "resume.docx")
        assert result["name"] == "Jane Doe"

    def test_parse_image(self):
        parser = ResumeParser(client=_mock_client(_VALID_PARSE_RESPONSE))
        result = parser.parse(b"fake-png-bytes", "resume.png")
        assert result["name"] == "Jane Doe"

    def test_unsupported_format(self):
        parser = ResumeParser(client=_mock_client(""))
        result = parser.parse(b"data", "resume.xyz")
        assert "error" in result

    @patch("src.resume_parser._extract_text_from_pdf", return_value="")
    def test_empty_pdf(self, mock_extract):
        parser = ResumeParser(client=_mock_client(""))
        result = parser.parse(b"empty", "empty.pdf")
        assert "error" in result

    @patch("src.resume_parser._extract_text_from_pdf", return_value="Some text")
    def test_handles_bad_json(self, mock_extract):
        parser = ResumeParser(client=_mock_client("not valid json at all"))
        result = parser.parse(b"data", "resume.pdf")
        assert "error" in result

    @patch("src.resume_parser._extract_text_from_pdf", return_value="Some text")
    def test_handles_api_error(self, mock_extract):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("API down")
        parser = ResumeParser(client=client)
        result = parser.parse(b"data", "resume.pdf")
        assert "error" in result


class TestParseToProfile:
    @patch("src.resume_parser._extract_text_from_pdf", return_value="Jane Doe resume")
    def test_returns_profile(self, mock_extract):
        parser = ResumeParser(client=_mock_client(_VALID_PARSE_RESPONSE))
        profile, confidence = parser.parse_to_profile(b"pdf-data", "resume.pdf")
        assert isinstance(profile, UserProfile)
        assert profile.name == "Jane Doe"
        assert profile.experience_level == ExperienceLevel.SENIOR
        assert "Python" in profile.skills
        assert confidence.get("name") == 0.95

    @patch("src.resume_parser._extract_text_from_pdf", return_value="some text")
    def test_returns_none_on_error(self, mock_extract):
        parser = ResumeParser(client=_mock_client("not json"))
        profile, confidence = parser.parse_to_profile(b"data", "resume.pdf")
        assert profile is None
        assert confidence == {}

    @patch("src.resume_parser._extract_text_from_pdf", return_value="resume text")
    def test_handles_invalid_experience_level(self, mock_extract):
        response = json.dumps({
            "name": "Bob",
            "email": "bob@test.com",
            "location": "NYC",
            "skills": ["Java"],
            "experience_level": "invalid_level",
            "years_of_experience": 3,
            "education": [],
            "work_history": [],
            "desired_roles": [],
            "languages": ["English"],
            "certifications": [],
            "portfolio_url": None,
            "linkedin_url": None,
            "confidence": {},
        })
        parser = ResumeParser(client=_mock_client(response))
        profile, _ = parser.parse_to_profile(b"data", "resume.pdf")
        assert profile is not None
        assert profile.experience_level == ExperienceLevel.MID  # fallback
