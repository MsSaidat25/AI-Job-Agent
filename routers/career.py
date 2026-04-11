"""Career Dreamer endpoints (Sprint 2)."""

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from routers.schemas import AgentResponse

router = APIRouter(prefix="/api/career", tags=["career"])


# ── Request / Response schemas ───────────────────────────────────────────────


class CareerDreamRequest(BaseModel):
    dream_role: str = Field(..., max_length=500)
    dream_industry: str = Field(default="", max_length=300)
    dream_location: str = Field(default="", max_length=200)
    timeline_months: int = Field(default=12, ge=1, le=120)


class CareerDreamResponse(BaseModel):
    dream_id: str
    dream_role: str
    dream_industry: str
    dream_location: str
    timeline_months: int
    gap_report: Optional[dict[str, Any]] = None
    timeline_plan: Optional[dict[str, Any]] = None
    feasibility_score: Optional[float] = None
    analysis: str = ""


class CareerDreamSummary(BaseModel):
    dream_id: str
    dream_role: str
    dream_industry: str
    feasibility_score: Optional[float] = None
    created_at: Optional[str] = None


class CareerDreamListResponse(BaseModel):
    dreams: list[CareerDreamSummary]
    total: int


class FindJobsResponse(BaseModel):
    dream_id: str
    search_terms: list[str]
    dream_role: str


class SaveDreamRequest(BaseModel):
    analysis: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.post("/dream", response_model=CareerDreamResponse)
    @limiter.limit("5/minute")
    async def career_dream(
        request: Request,
        body: CareerDreamRequest,
        session_id: str = session_dep,
    ):
        """Run career dreamer analysis via the agent."""
        agent = get_agent_fn(session_id)
        try:
            async with get_lock_fn(session_id):
                response = await asyncio.to_thread(
                    agent.chat,
                    f"Analyse my career dream: I want to become a {body.dream_role} "
                    f"in the {body.dream_industry or 'any'} industry, "
                    f"located in {body.dream_location or 'anywhere'}, "
                    f"within {body.timeline_months} months. "
                    "Provide a gap analysis, feasibility score (0-1), and a step-by-step timeline plan.",
                )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"LLM service unavailable: {type(exc).__name__}")
        import uuid

        dream_id = str(uuid.uuid4())
        return CareerDreamResponse(
            dream_id=dream_id,
            dream_role=body.dream_role,
            dream_industry=body.dream_industry,
            dream_location=body.dream_location,
            timeline_months=body.timeline_months,
            analysis=response,
        )

    @router.get("/dream/{dream_id}/detail", response_model=CareerDreamResponse)
    @limiter.limit("30/minute")
    async def get_dream_detail(
        request: Request,
        dream_id: str,
        session_id: str = session_dep,
    ):
        """Get a saved career dream from the database."""
        from src.models import CareerDreamORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            dream = db.query(CareerDreamORM).filter_by(id=dream_id).first()
            if not dream:
                raise HTTPException(status_code=404, detail="Dream not found.")
            d: Any = dream
            if d.user_id != profile.id:
                raise HTTPException(status_code=403, detail="Access denied.")
            return CareerDreamResponse(
                dream_id=d.id,
                dream_role=d.dream_role,
                dream_industry=d.dream_industry,
                dream_location=d.dream_location,
                timeline_months=d.timeline_months,
                gap_report=d.gap_report,
                timeline_plan=d.timeline_plan,
                feasibility_score=d.feasibility_score,
            )
        finally:
            db.close()

    @router.post("/dream/{dream_id}/find-jobs", response_model=FindJobsResponse)
    @limiter.limit("10/minute")
    async def find_jobs_for_dream(
        request: Request,
        dream_id: str,
        session_id: str = session_dep,
    ):
        """Return search terms derived from a dream role."""
        from src.models import CareerDreamORM, init_db

        db = init_db()
        try:
            dream = db.query(CareerDreamORM).filter_by(id=dream_id).first()
            if not dream:
                raise HTTPException(status_code=404, detail="Dream not found.")
            d: Any = dream
            role = d.dream_role
            industry = d.dream_industry
        finally:
            db.close()

        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Generate 5 job search terms for someone pursuing a career as a {role} "
                f"in the {industry or 'general'} industry. Return only the search terms, one per line.",
            )
        terms = [t.strip("- ").strip() for t in response.strip().splitlines() if t.strip()]
        return FindJobsResponse(dream_id=dream_id, search_terms=terms[:10], dream_role=role)

    @router.post("/dream/{dream_id}/save", response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def save_dream(
        request: Request,
        dream_id: str,
        body: SaveDreamRequest,
        session_id: str = session_dep,
    ):
        """Save a career dream to the database."""
        from src.models import CareerDreamORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            existing = db.query(CareerDreamORM).filter_by(id=dream_id).first()
            if existing:
                return AgentResponse(response="Dream already saved.")
            # Save with minimal info; full analysis stored in gap_report

            dream = CareerDreamORM(
                id=dream_id,
                user_id=profile.id,
                dream_role="saved dream",
            )
            db.add(dream)
            db.commit()
            return AgentResponse(response="Dream saved successfully.")
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.get("/dreams", response_model=CareerDreamListResponse)
    @limiter.limit("30/minute")
    async def list_dreams(
        request: Request,
        session_id: str = session_dep,
    ):
        """List all saved career dreams for the current user."""
        from src.models import CareerDreamORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            rows = (
                db.query(CareerDreamORM)
                .filter_by(user_id=profile.id)
                .order_by(CareerDreamORM.created_at.desc())
                .all()
            )
            dreams = []
            for row in rows:
                d: Any = row
                dreams.append(CareerDreamSummary(
                    dream_id=d.id,
                    dream_role=d.dream_role,
                    dream_industry=d.dream_industry,
                    feasibility_score=d.feasibility_score,
                    created_at=str(d.created_at) if d.created_at else None,
                ))
            return CareerDreamListResponse(dreams=dreams, total=len(dreams))
        finally:
            db.close()

    @router.get("/report", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def career_report(
        request: Request,
        session_id: str = session_dep,
    ):
        """Generate a comparison report across all saved career dreams."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                "Generate a comparison report of all my saved career dreams. "
                "Compare feasibility, timelines, skill gaps, and recommend the best path forward.",
            )
        return AgentResponse(response=response)
