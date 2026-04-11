"""Intelligence and insights endpoints (Sprint 4)."""

import asyncio
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from routers.schemas import AgentResponse

router = APIRouter(prefix="/api/insights", tags=["insights"])


# ── Response schemas ─────────────────────────────────────────────────────────


class OutcomeLearningResponse(BaseModel):
    correlations: list[dict[str, Any]] = Field(default_factory=list)
    winning_patterns: list[str] = Field(default_factory=list)
    analysis: str = ""


class RejectionPatternsResponse(BaseModel):
    patterns: list[dict[str, Any]] = Field(default_factory=list)
    common_reasons: list[str] = Field(default_factory=list)
    analysis: str = ""


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.get("/outcome-learning", response_model=OutcomeLearningResponse)
    @limiter.limit("5/minute")
    async def outcome_learning(
        request: Request,
        session_id: str = session_dep,
    ):
        """Get variant correlation data -- which resume/cover letter variants perform best."""
        from src.outcome_service import OutcomeLearningService
        from src.session_store import get_session_profile

        get_session_profile(session_id)
        service = OutcomeLearningService()
        insights = await asyncio.to_thread(service.generate_insights, [], [])
        return OutcomeLearningResponse(
            correlations=[],
            winning_patterns=[],
            analysis=insights,
        )

    @router.get("/rejection-patterns", response_model=RejectionPatternsResponse)
    @limiter.limit("5/minute")
    async def rejection_patterns(
        request: Request,
        session_id: str = session_dep,
    ):
        """Analyse rejection patterns across applications."""
        from src.restrategizer import RejectionRestrategizer
        from src.session_store import get_session_profile

        get_session_profile(session_id)
        service = RejectionRestrategizer()
        patterns = await asyncio.to_thread(service.detect_patterns, [])
        return RejectionPatternsResponse(
            patterns=[p.model_dump() for p in patterns],
            common_reasons=[],
            analysis="",
        )

    @router.get("/restrategize", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def restrategize(
        request: Request,
        session_id: str = session_dep,
    ):
        """Get actionable advice based on application history."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                "Based on my application history, rejection patterns, and feedback, "
                "provide actionable advice to improve my success rate. "
                "Include specific changes to my resume, cover letters, and application strategy.",
            )
        return AgentResponse(response=response)

    @router.get("/weekly-report", response_model=AgentResponse)
    @limiter.limit("3/minute")
    async def weekly_report(
        request: Request,
        session_id: str = session_dep,
    ):
        """Generate a weekly advisor report."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                "Generate my weekly career advisor report. Include: "
                "1) Applications submitted this week and their status "
                "2) Response rate trends "
                "3) Interview performance "
                "4) Market conditions for my target roles "
                "5) Recommended actions for next week",
            )
        return AgentResponse(response=response)
