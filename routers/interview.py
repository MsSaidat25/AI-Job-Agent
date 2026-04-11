"""Interview prep endpoints (Sprint 3)."""

import asyncio
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from routers.schemas import AgentResponse

router = APIRouter(prefix="/api/interview", tags=["interview"])


# ── Response schemas ─────────────────────────────────────────────────────────


class PrepPackageResponse(BaseModel):
    application_id: str
    company_brief: str = ""
    key_topics: list[str] = Field(default_factory=list)
    practice_questions: list[str] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    full_prep: str = ""


class CompanyBriefResponse(BaseModel):
    application_id: str
    company: str = ""
    brief: str = ""


class QuestionsResponse(BaseModel):
    application_id: str
    questions: list[dict[str, str]] = Field(default_factory=list)


class DebriefRequest(BaseModel):
    went_well: list[str] = Field(default_factory=list, max_length=20)
    could_improve: list[str] = Field(default_factory=list, max_length=20)
    questions_asked: list[str] = Field(default_factory=list, max_length=30)
    overall_feeling: str = Field(default="neutral", max_length=50)
    notes: str = Field(default="", max_length=5000)


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.get("/{application_id}/prep", response_model=PrepPackageResponse)
    @limiter.limit("5/minute")
    async def interview_prep(
        request: Request,
        application_id: str,
        session_id: str = session_dep,
    ):
        """Generate a full interview prep package."""
        from src.interview_service import InterviewPrepService

        service = InterviewPrepService()
        # Use application_id as job_id proxy for now
        result = await asyncio.to_thread(
            service.full_prep, "the role", "the company", "", [],
        )
        return PrepPackageResponse(
            application_id=application_id,
            company_brief=result.company_brief.company,
            key_topics=[],
            practice_questions=[q.question for q in result.questions[:5]],
            talking_points=result.ask_questions,
            full_prep="",
        )

    @router.get("/{application_id}/company-brief", response_model=CompanyBriefResponse)
    @limiter.limit("10/minute")
    async def company_brief(
        request: Request,
        application_id: str,
        session_id: str = session_dep,
    ):
        """Get company research for interview prep."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Research the company for application {application_id}. "
                "Provide a brief on their mission, culture, recent news, and key products. "
                "Focus on information useful for an interview.",
            )
        return CompanyBriefResponse(
            application_id=application_id,
            brief=response,
        )

    @router.get("/{application_id}/questions", response_model=QuestionsResponse)
    @limiter.limit("10/minute")
    async def practice_questions(
        request: Request,
        application_id: str,
        session_id: str = session_dep,
    ):
        """Generate practice interview questions and suggested answers."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Generate 8 practice interview questions for application {application_id}. "
                "Include a mix of behavioral, technical, and situational questions. "
                "For each question, provide a brief suggested answer approach.",
            )
        # Parse response into Q&A pairs
        questions = []
        lines = response.strip().splitlines()
        current_q = ""
        current_a = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_q:
                    questions.append({"question": current_q, "suggested_answer": current_a.strip()})
                    current_q = ""
                    current_a = ""
                continue
            if stripped[0].isdigit() and ("." in stripped[:4] or ")" in stripped[:4]):
                if current_q:
                    questions.append({"question": current_q, "suggested_answer": current_a.strip()})
                current_q = stripped
                current_a = ""
            else:
                current_a += " " + stripped
        if current_q:
            questions.append({"question": current_q, "suggested_answer": current_a.strip()})
        return QuestionsResponse(application_id=application_id, questions=questions)

    @router.post("/{application_id}/debrief", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def interview_debrief(
        request: Request,
        application_id: str,
        body: DebriefRequest,
        session_id: str = session_dep,
    ):
        """Post-interview debrief and improvement analysis."""
        agent = get_agent_fn(session_id)
        prompt_parts = [
            f"I just finished an interview for application {application_id}.",
            f"Overall feeling: {body.overall_feeling}.",
        ]
        if body.went_well:
            prompt_parts.append(f"What went well: {', '.join(body.went_well)}")
        if body.could_improve:
            prompt_parts.append(f"Areas to improve: {', '.join(body.could_improve)}")
        if body.questions_asked:
            prompt_parts.append(f"Questions they asked: {', '.join(body.questions_asked)}")
        if body.notes:
            prompt_parts.append(f"Additional notes: {body.notes}")
        prompt_parts.append(
            "Analyse my interview performance and provide specific improvement suggestions "
            "for my next interview."
        )
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(agent.chat, " ".join(prompt_parts))
        return AgentResponse(response=response)
