"""Daily feed endpoints (Sprint 3)."""

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

router = APIRouter(prefix="/api/feed", tags=["feed"])


class FeedItemResponse(BaseModel):
    job_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    match_score: Optional[float] = None
    annotation: str = ""


class DailyFeedResponse(BaseModel):
    items: list[FeedItemResponse] = Field(default_factory=list)
    new_count: int = 0
    high_match_count: int = 0
    summary: str = ""


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.get("/daily", response_model=DailyFeedResponse)
    @limiter.limit("10/minute")
    async def daily_feed(
        request: Request,
        session_id: str = session_dep,
    ):
        """Return curated daily job feed for the user."""
        from src.feed_service import FeedService
        from src.session_store import get_session_profile

        agent = get_agent_fn(session_id)
        profile = get_session_profile(session_id)
        service = FeedService()
        result = await asyncio.to_thread(
            service.generate_daily_feed, profile.id, profile, agent._job_cache,
        )
        return DailyFeedResponse(
            items=[FeedItemResponse(**it.model_dump()) for it in result.items],
            new_count=result.new_count,
            high_match_count=result.high_match_count,
            summary=result.summary,
        )

    @router.post("/refresh", response_model=DailyFeedResponse)
    @limiter.limit("3/minute")
    async def refresh_feed(
        request: Request,
        session_id: str = session_dep,
    ):
        """Force regenerate the daily feed."""
        from src.feed_service import FeedService
        from src.session_store import get_session_profile

        agent = get_agent_fn(session_id)
        profile = get_session_profile(session_id)
        service = FeedService()
        result = await asyncio.to_thread(
            service.generate_daily_feed, profile.id, profile, agent._job_cache,
        )
        return DailyFeedResponse(
            items=[FeedItemResponse(**it.model_dump()) for it in result.items],
            new_count=result.new_count,
            high_match_count=result.high_match_count,
            summary=result.summary,
        )
