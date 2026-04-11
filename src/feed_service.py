"""Daily Curated Feed Service -- automated job discovery and pre-preparation."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, cast

from anthropic.types import TextBlock
from pydantic import BaseModel, Field

from config.settings import AGENT_MODEL
from src.llm_client import create_message_with_failover, get_llm_client

logger = logging.getLogger(__name__)


class FeedItem(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    match_score: Optional[float] = None
    annotation: str = ""
    is_pre_prepared: bool = False


class DailyFeed(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    items: list[FeedItem] = Field(default_factory=list)
    new_count: int = 0
    high_match_count: int = 0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str = ""


class FeedService:
    """Generates daily curated job feeds based on user preferences."""

    def __init__(self, client: Any = None) -> None:
        self._client = client or get_llm_client()

    def generate_daily_feed(
        self, user_id: str, profile: Any, job_cache: dict[str, Any],
    ) -> DailyFeed:
        """Generate a curated feed from cached/searched jobs."""
        items: list[FeedItem] = []
        for job_id, job in list(job_cache.items())[:50]:
            if isinstance(job, dict):
                title = job.get("job_title", job.get("title", ""))
                company = job.get("employer_name", job.get("company", ""))
                location = job.get("job_city", job.get("location", ""))
                score = job.get("_match_score")
            else:
                title = getattr(job, "title", "")
                company = getattr(job, "company", "")
                location = getattr(job, "location", "")
                score = getattr(job, "match_score", None)

            items.append(FeedItem(
                job_id=job_id,
                title=title,
                company=company,
                location=location,
                match_score=score,
            ))

        items.sort(key=lambda x: x.match_score or 0, reverse=True)
        high_match = sum(1 for i in items if i.match_score and i.match_score >= 90)

        # Generate AI annotations for top matches
        if items[:5]:
            try:
                jobs_ctx = "\n".join(
                    f"- {it.title} at {it.company} ({it.location}), score={it.match_score}"
                    for it in items[:5]
                )
                response = create_message_with_failover(
                    self._client,
                    model=AGENT_MODEL,
                    max_tokens=512,
                    system="Briefly annotate each job with why it's a good match. One sentence per job. Return as plain text, one annotation per line.",
                    messages=[{"role": "user", "content": f"Profile desired roles: {getattr(profile, 'desired_roles', [])}\n\nTop jobs:\n{jobs_ctx}"}],
                )
                annotations = cast(TextBlock, response.content[0]).text.strip().split("\n")
                for i, ann in enumerate(annotations[:5]):
                    if i < len(items):
                        items[i].annotation = ann.strip("- ")
            except Exception:
                logger.warning("Failed to generate feed annotations", exc_info=True)

        return DailyFeed(
            user_id=user_id,
            items=items[:25],
            new_count=len(items),
            high_match_count=high_match,
            summary=f"{len(items)} new matches found. {high_match} above 90% match.",
        )
