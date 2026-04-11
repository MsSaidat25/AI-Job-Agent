"""Salary calibration and negotiation endpoints (Sprint 2 + Sprint 4)."""

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from routers.schemas import AgentResponse

router = APIRouter(prefix="/api/salary", tags=["salary"])


# ── Request / Response schemas ───────────────────────────────────────────────


class SalaryCalibrateRequest(BaseModel):
    role: str = Field(..., max_length=500)
    locations: list[str] = Field(default_factory=lambda: ["United States"])
    skills: list[str] = Field(default_factory=list)


class SalaryCalibrateResponse(BaseModel):
    role: str
    locations: list[str]
    data_points: list[dict[str, Any]] = Field(default_factory=list)
    market_summary: str = ""
    arbitrage_analysis: str = ""


class NegotiateRequest(BaseModel):
    current_offer: int = Field(..., ge=0)
    role: str = Field(..., max_length=500)
    company: str = Field(default="", max_length=300)
    location: str = Field(default="", max_length=200)
    competing_offer: Optional[int] = Field(default=None, ge=0)
    leverage_points: list[str] = Field(default_factory=list)


class CompareOffersRequest(BaseModel):
    offers: list[dict[str, Any]] = Field(..., max_length=10)


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.post("/calibrate", response_model=SalaryCalibrateResponse)
    @limiter.limit("10/minute")
    async def salary_calibrate(
        request: Request,
        body: SalaryCalibrateRequest,
        session_id: str = session_dep,
    ):
        """Calibrate salary expectations across locations."""
        from src.salary_service import SalaryCalibrationService

        service = SalaryCalibrationService()
        result = await asyncio.to_thread(
            service.calibrate,
            role=body.role,
            locations=body.locations,
            skills=body.skills,
        )
        return SalaryCalibrateResponse(
            role=result.role,
            locations=result.locations,
            data_points=[dp.model_dump(mode="json") for dp in result.data_points],
            market_summary=result.market_summary,
            arbitrage_analysis=result.arbitrage_analysis,
        )

    @router.post("/negotiate", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def negotiate_salary(
        request: Request,
        body: NegotiateRequest,
        session_id: str = session_dep,
    ):
        """Generate a counter-offer strategy."""
        agent = get_agent_fn(session_id)
        prompt_parts = [
            f"Help me negotiate a salary counter-offer. Current offer: ${body.current_offer:,} "
            f"for {body.role} at {body.company or 'the company'}",
        ]
        if body.location:
            prompt_parts.append(f"Location: {body.location}")
        if body.competing_offer:
            prompt_parts.append(f"I have a competing offer of ${body.competing_offer:,}")
        if body.leverage_points:
            prompt_parts.append(f"My leverage points: {', '.join(body.leverage_points)}")
        prompt_parts.append(
            "Provide a specific counter-offer amount, email script, and talking points."
        )
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(agent.chat, ". ".join(prompt_parts))
        return AgentResponse(response=response)

    @router.post("/compare-offers", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def compare_offers(
        request: Request,
        body: CompareOffersRequest,
        session_id: str = session_dep,
    ):
        """Compare multiple job offers side-by-side."""
        agent = get_agent_fn(session_id)
        import json

        offers_text = json.dumps(body.offers, indent=2)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Compare these job offers and recommend the best choice:\n\n{offers_text}\n\n"
                "Consider total compensation, growth potential, work-life balance, and location.",
            )
        return AgentResponse(response=response)
