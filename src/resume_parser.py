# Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com). All Rights Reserved.
# avien@aviensolutions.com
"""
Resume Parser -- Extract structured profile data from uploaded resumes.

Supports PDF (via pdfplumber), DOCX (via python-docx), and image files
(via Claude Vision). Returns a structured UserProfile with per-field
confidence scores.
"""
from __future__ import annotations

import base64
import json
import logging
import mimetypes
from typing import Any, cast

import anthropic
from anthropic.types import TextBlock

from config.settings import AGENT_MODEL, MAX_TOKENS
from src.models import ExperienceLevel, UserProfile

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".webp", ".gif"}

_PARSE_SYSTEM = """You are an expert resume parser. Extract structured data from the
resume text provided. Respond ONLY with valid JSON -- no markdown fences, no commentary.

The JSON must have these keys:
- "name": string (full name)
- "email": string or null
- "phone": string or null
- "location": string (city, state/province, country)
- "skills": list of strings
- "experience_level": one of "entry", "mid", "senior", "lead", "executive"
- "years_of_experience": integer estimate
- "education": list of {"degree": str, "school": str, "graduation_year": str}
- "work_history": list of {"title": str, "company": str, "start": str, "end": str, "highlights": list[str]}
- "desired_roles": list of strings (inferred from experience)
- "languages": list of strings
- "certifications": list of strings
- "portfolio_url": string or null
- "linkedin_url": string or null
- "confidence": object mapping each top-level key to a float 0.0-1.0 confidence score
"""


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using pdfplumber."""
    import pdfplumber
    import io

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages[:20]:  # cap at 20 pages
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def _extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX using python-docx."""
    import docx
    import io

    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


class ResumeParser:
    """Parse resumes in PDF, DOCX, or image format into structured UserProfile data."""

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic()

    def parse(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> dict[str, Any]:
        """Parse a resume file and return structured profile data with confidence scores.

        Returns a dict with all UserProfile fields plus a "confidence" dict.
        """
        ext = _get_extension(filename)
        if ext not in _SUPPORTED_EXTENSIONS:
            return {"error": f"Unsupported file type: {ext}. Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"}

        if ext == ".pdf":
            return self._parse_text_resume(_extract_text_from_pdf(file_bytes))
        elif ext in {".docx", ".doc"}:
            return self._parse_text_resume(_extract_text_from_docx(file_bytes))
        else:
            return self._parse_image_resume(file_bytes, filename)

    def parse_to_profile(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> tuple[UserProfile | None, dict[str, float]]:
        """Parse a resume and return a UserProfile object plus confidence scores.

        Returns (None, {}) if parsing fails.
        """
        data = self.parse(file_bytes, filename)
        if "error" in data:
            return None, {}

        confidence = data.pop("confidence", {})

        try:
            exp_level = data.get("experience_level", "mid")
            try:
                exp_level = ExperienceLevel(exp_level)
            except ValueError:
                exp_level = ExperienceLevel.MID

            profile = UserProfile(
                name=data.get("name", "Unknown"),
                email=data.get("email", "unknown@example.com"),
                phone=data.get("phone"),
                location=data.get("location", ""),
                skills=data.get("skills", []),
                experience_level=exp_level,
                years_of_experience=int(data.get("years_of_experience", 0)),
                education=data.get("education", []),
                work_history=data.get("work_history", []),
                desired_roles=data.get("desired_roles", []),
                languages=data.get("languages", ["English"]),
                certifications=data.get("certifications", []),
                portfolio_url=data.get("portfolio_url"),
                linkedin_url=data.get("linkedin_url"),
            )
            return profile, confidence
        except Exception:
            logger.exception("Failed to construct UserProfile from parsed data")
            return None, {}

    def _parse_text_resume(self, text: str) -> dict[str, Any]:
        """Send extracted text to Claude for structured parsing."""
        if not text.strip():
            return {"error": "No text could be extracted from the file."}

        truncated = text[:6000]
        try:
            response = self._client.messages.create(
                model=AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                system=_PARSE_SYSTEM,
                messages=[{"role": "user", "content": f"Parse this resume:\n\n{truncated}"}],
            )
            raw = cast(TextBlock, response.content[0]).text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(raw)
        except (json.JSONDecodeError, IndexError):
            logger.exception("Failed to parse LLM response as JSON")
            return {"error": "Failed to parse resume content. The format may not be supported."}
        except Exception:
            logger.exception("Resume parsing failed")
            return {"error": "Resume parsing service temporarily unavailable."}

    def _parse_image_resume(self, file_bytes: bytes, filename: str) -> dict[str, Any]:
        """Use Claude Vision to parse an image-based resume."""
        mime_type = mimetypes.guess_type(filename)[0] or "image/png"
        b64_data = base64.b64encode(file_bytes).decode()

        try:
            messages = cast(Any, [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": b64_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Parse this resume image and extract all structured data.",
                    },
                ],
            }])
            response = self._client.messages.create(
                model=AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                system=_PARSE_SYSTEM,
                messages=messages,
            )
            raw = cast(TextBlock, response.content[0]).text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(raw)
        except (json.JSONDecodeError, IndexError):
            logger.exception("Failed to parse Vision response as JSON")
            return {"error": "Failed to parse resume image. Try a clearer scan or PDF."}
        except Exception:
            logger.exception("Image resume parsing failed")
            return {"error": "Resume parsing service temporarily unavailable."}


def _get_extension(filename: str) -> str:
    """Get lowercase file extension."""
    import os
    return os.path.splitext(filename)[1].lower()
