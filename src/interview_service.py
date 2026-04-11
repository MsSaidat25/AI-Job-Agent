"""Interview Preparation Service -- company research, Q&A generation, debrief analysis."""

import logging
from typing import Any, Optional, cast

from anthropic.types import TextBlock
from pydantic import BaseModel, Field

from config.settings import AGENT_MODEL
from src.llm_client import create_message_with_failover, get_llm_client
from src.utils import parse_json_response

logger = logging.getLogger(__name__)


class CompanyBrief(BaseModel):
    company: str
    industry: str = ""
    size: str = ""
    founded: str = ""
    mission: str = ""
    culture: str = ""
    recent_news: list[str] = Field(default_factory=list)
    interview_tips: list[str] = Field(default_factory=list)
    glassdoor_rating: Optional[float] = None


class InterviewQuestion(BaseModel):
    question: str
    category: str = ""  # behavioral, technical, situational, culture
    suggested_answer: str = ""
    tips: str = ""


class InterviewPrepPackage(BaseModel):
    company_brief: CompanyBrief
    questions: list[InterviewQuestion] = Field(default_factory=list)
    ask_questions: list[str] = Field(default_factory=list)
    format_hints: list[str] = Field(default_factory=list)


class DebriefReport(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    areas_to_improve: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    overall_assessment: str = ""


class InterviewPrepService:
    """AI-powered interview preparation."""

    def __init__(self, client: Any = None) -> None:
        self._client = client or get_llm_client()

    def research_company(self, company_name: str) -> CompanyBrief:
        """Generate a company research brief."""
        try:
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=1500,
                system=(
                    "You are a career research expert. Provide a company brief for interview preparation. "
                    "Return JSON with: company, industry, size, founded, mission, culture, "
                    "recent_news (array of 3-5 items), interview_tips (array of 3-5 tips), "
                    "glassdoor_rating (float or null)."
                ),
                messages=[{"role": "user", "content": f"Research brief for: {company_name}"}],
            )
            text = cast(TextBlock, response.content[0]).text
            result = parse_json_response(text)
            if isinstance(result, dict):
                return CompanyBrief(**result)
        except Exception:
            logger.warning("Company research failed for %s", company_name, exc_info=True)
        return CompanyBrief(company=company_name)

    def generate_questions(
        self, job_title: str, job_description: str, profile_skills: list[str],
    ) -> list[InterviewQuestion]:
        """Generate role-specific interview Q&A."""
        try:
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=2000,
                system=(
                    "You are an interview prep coach. Generate 10 interview questions tailored to "
                    "the job description and candidate's skills. Mix behavioral, technical, and situational. "
                    "Return JSON array of objects with: question, category, suggested_answer, tips."
                ),
                messages=[{
                    "role": "user",
                    "content": (
                        f"Job Title: {job_title}\n"
                        f"Description: {job_description[:2000]}\n"
                        f"Candidate Skills: {', '.join(profile_skills[:15])}"
                    ),
                }],
            )
            text = cast(TextBlock, response.content[0]).text
            result = parse_json_response(text)
            if isinstance(result, list):
                return [InterviewQuestion(**q) for q in result[:15]]
        except Exception:
            logger.warning("Question generation failed", exc_info=True)
        return []

    def generate_ask_questions(self, job_title: str, company: str) -> list[str]:
        """Generate questions the candidate should ask the interviewer."""
        try:
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=512,
                system=(
                    "Generate 5-7 thoughtful questions a candidate should ask in an interview. "
                    "Return a JSON array of strings. Questions should show genuine interest and insight."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Role: {job_title}\nCompany: {company}",
                }],
            )
            text = cast(TextBlock, response.content[0]).text
            result = parse_json_response(text)
            if isinstance(result, list):
                return [str(q) for q in result[:10]]
        except Exception:
            logger.warning("Ask-questions generation failed", exc_info=True)
        return []

    def debrief(
        self, job_title: str, company: str, responses: dict[str, str],
    ) -> DebriefReport:
        """Analyze post-interview debrief responses."""
        try:
            responses_text = "\n".join(f"Q: {q}\nA: {a}" for q, a in responses.items())
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=1000,
                system=(
                    "You are an interview coach. Analyze the candidate's interview debrief. "
                    "Return JSON with: strengths (array), areas_to_improve (array), "
                    "next_steps (array), overall_assessment (string)."
                ),
                messages=[{
                    "role": "user",
                    "content": (
                        f"Role: {job_title} at {company}\n\n"
                        f"Interview Debrief:\n{responses_text}"
                    ),
                }],
            )
            text = cast(TextBlock, response.content[0]).text
            result = parse_json_response(text)
            if isinstance(result, dict):
                return DebriefReport(**result)
        except Exception:
            logger.warning("Debrief analysis failed", exc_info=True)
        return DebriefReport()

    def full_prep(
        self, job_title: str, company: str, job_description: str,
        profile_skills: list[str],
    ) -> InterviewPrepPackage:
        """Generate a complete interview prep package."""
        brief = self.research_company(company)
        questions = self.generate_questions(job_title, job_description, profile_skills)
        ask_qs = self.generate_ask_questions(job_title, company)

        return InterviewPrepPackage(
            company_brief=brief,
            questions=questions,
            ask_questions=ask_qs,
            format_hints=[
                "Research the company's recent news before the interview",
                "Prepare 2-3 stories using the STAR method",
                "Dress one level above the company's dress code",
                "Arrive 10-15 minutes early",
                "Bring copies of your resume and a notebook",
            ],
        )
