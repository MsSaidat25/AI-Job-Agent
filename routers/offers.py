"""Offer management endpoints (Sprint 5)."""

import asyncio
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter

from routers.schemas import AgentResponse

router = APIRouter(prefix="/api/offers", tags=["offers"])


# ── Request / Response schemas ───────────────────────────────────────────────


class CreateOfferRequest(BaseModel):
    company: str = Field(..., max_length=300)
    role: str = Field(..., max_length=500)
    base_salary: int = Field(..., ge=0)
    bonus: Optional[int] = Field(default=None, ge=0)
    equity: Optional[str] = Field(default=None, max_length=200)
    benefits: str = Field(default="", max_length=5000)
    location: str = Field(default="", max_length=200)
    remote: bool = False
    job_id: Optional[str] = Field(default=None, max_length=200)
    deadline: Optional[str] = Field(default=None, max_length=20)


class OfferResponse(BaseModel):
    id: str
    company: str
    role: str
    base_salary: int
    bonus: Optional[int] = None
    equity: Optional[str] = None
    benefits: str = ""
    location: str = ""
    remote: bool = False
    status: str = "pending"
    deadline: Optional[str] = None
    created_at: Optional[str] = None


class OfferListResponse(BaseModel):
    offers: list[OfferResponse]
    total: int


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.post("/", status_code=status.HTTP_201_CREATED, response_model=OfferResponse)
    @limiter.limit("10/minute")
    async def add_offer(
        request: Request,
        body: CreateOfferRequest,
        session_id: str = session_dep,
    ):
        """Add a new job offer."""
        from src.models import OfferORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            offer_id = str(uuid.uuid4())
            offer = OfferORM(
                id=offer_id,
                user_id=profile.id,
                job_id=body.job_id,
                company=body.company,
                role=body.role,
                base_salary=body.base_salary,
                bonus=body.bonus,
                equity=body.equity,
                benefits=body.benefits,
                location=body.location,
                remote=body.remote,
            )
            if body.deadline:
                from datetime import date as _date

                try:
                    setattr(offer, "deadline", _date.fromisoformat(body.deadline))
                except ValueError:
                    pass
            db.add(offer)
            db.commit()
            o: Any = offer
            return OfferResponse(
                id=o.id,
                company=o.company,
                role=o.role,
                base_salary=o.base_salary,
                bonus=o.bonus,
                equity=o.equity,
                benefits=o.benefits,
                location=o.location,
                remote=o.remote,
                status=o.status,
                deadline=str(o.deadline) if o.deadline else None,
                created_at=str(o.created_at) if o.created_at else None,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.get("/", response_model=OfferListResponse)
    @limiter.limit("30/minute")
    async def list_offers(
        request: Request,
        session_id: str = session_dep,
    ):
        """List all offers for the current user."""
        from src.models import OfferORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            rows = (
                db.query(OfferORM)
                .filter_by(user_id=profile.id)
                .order_by(OfferORM.created_at.desc())
                .all()
            )
            offers = []
            for row in rows:
                o: Any = row
                offers.append(OfferResponse(
                    id=o.id,
                    company=o.company,
                    role=o.role,
                    base_salary=o.base_salary,
                    bonus=o.bonus,
                    equity=o.equity,
                    benefits=o.benefits,
                    location=o.location,
                    remote=o.remote,
                    status=o.status,
                    deadline=str(o.deadline) if o.deadline else None,
                    created_at=str(o.created_at) if o.created_at else None,
                ))
            return OfferListResponse(offers=offers, total=len(offers))
        finally:
            db.close()

    @router.get("/compare", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def compare_offers(
        request: Request,
        session_id: str = session_dep,
    ):
        """Side-by-side comparison of all offers."""
        from src.models import OfferORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            rows = (
                db.query(OfferORM)
                .filter_by(user_id=profile.id)
                .order_by(OfferORM.created_at.desc())
                .all()
            )
            if not rows:
                return AgentResponse(response="No offers to compare.")
            offer_summaries = []
            for row in rows:
                o: Any = row
                offer_summaries.append(
                    f"- {o.company}: {o.role}, ${o.base_salary:,} base"
                    + (f" + ${o.bonus:,} bonus" if o.bonus else "")
                    + (f", equity: {o.equity}" if o.equity else "")
                    + (f", {o.location}" if o.location else "")
                    + (" (remote)" if o.remote else "")
                )
        finally:
            db.close()

        agent = get_agent_fn(session_id)
        summary_text = "\n".join(offer_summaries)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Compare these job offers side-by-side and recommend the best choice:\n\n"
                f"{summary_text}\n\n"
                "Consider total compensation, growth potential, work-life balance, and location.",
            )
        return AgentResponse(response=response)
