"""Intelligence and insights endpoints (Sprint 4)."""

import asyncio
from typing import Any, Optional

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


class ResumeVariantBucket(BaseModel):
    resume_tone: str
    sample_variant_id: str
    total_applications: int
    submitted: int
    responses: int
    interviews: int
    offers: int
    response_rate: float
    interview_rate: float
    offer_rate: float
    avg_ats_score: float = 0.0


class ResumeAbResponse(BaseModel):
    variants: list[ResumeVariantBucket] = Field(default_factory=list)
    winning_variant_id: Optional[str] = None
    total_variants: int = 0


class MarkWinningRequest(BaseModel):
    variant_id: str


class MarkWinningResponse(BaseModel):
    ok: bool
    variant_id: str


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

    @router.get("/resume-ab", response_model=ResumeAbResponse)
    @limiter.limit("10/minute")
    async def resume_ab(
        request: Request,
        session_id: str = session_dep,
    ):
        """Return per-tone resume A/B response-rate metrics.

        P3.2: surfaces the winning resume tone (professional vs. creative
        vs. technical) once the user has enough submissions to call it.
        """
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        agent = get_agent_fn(session_id)
        data = await asyncio.to_thread(
            agent._tracker.compute_variant_performance, profile.id
        )
        return ResumeAbResponse(
            variants=[ResumeVariantBucket(**v) for v in data["variants"]],
            winning_variant_id=data["winning_variant_id"],
            total_variants=data["total_variants"],
        )

    @router.post("/resume-ab/mark-winning", response_model=MarkWinningResponse)
    @limiter.limit("10/minute")
    async def mark_winning(
        request: Request,
        body: MarkWinningRequest,
        session_id: str = session_dep,
    ):
        """Persist a user's choice of winning variant (status='winning')."""
        agent = get_agent_fn(session_id)
        ok = await asyncio.to_thread(
            agent._tracker.mark_winning_variant, body.variant_id
        )
        return MarkWinningResponse(ok=ok, variant_id=body.variant_id)

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
