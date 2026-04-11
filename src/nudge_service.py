"""Follow-up Nudge Service -- automated application follow-up scheduling."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, cast

from anthropic.types import TextBlock
from pydantic import BaseModel, Field

from config.settings import AGENT_MODEL
from src.llm_client import create_message_with_failover, get_llm_client

logger = logging.getLogger(__name__)


# Nudge timeline: days after application submission
_NUDGE_SCHEDULE = [
    (3, "silent", "Application recently submitted. No action needed yet."),
    (7, "check_in", "Have you heard back from {company}?"),
    (14, "reminder", "Still no word after 2 weeks from {company}."),
    (21, "follow_up", "Time to send a follow-up email to {company}."),
    (30, "stale", "No response after a month from {company}. Consider moving on."),
]


class NudgeItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str
    user_id: str
    job_title: str = ""
    company: str = ""
    nudge_type: str = ""
    message: str = ""
    next_nudge_date: Optional[datetime] = None
    nudge_count: int = 0
    status: str = "active"
    draft_email: Optional[str] = None


class NudgeSettings(BaseModel):
    enabled: bool = True
    frequency: str = "standard"  # standard, gentle, aggressive
    quiet_hours_start: int = 22  # 10pm
    quiet_hours_end: int = 8    # 8am


class NudgeService:
    """Manages follow-up nudge schedules for applications."""

    def __init__(self, client: Any = None) -> None:
        self._client = client or get_llm_client()

    def create_nudge_schedule(
        self, application_id: str, user_id: str,
        job_title: str = "", company: str = "",
        submitted_at: Optional[datetime] = None,
    ) -> NudgeItem:
        """Create a new nudge schedule for an application."""
        base_date = submitted_at or datetime.now(timezone.utc)
        first_nudge_date = base_date + timedelta(days=7)  # First real nudge at day 7

        return NudgeItem(
            application_id=application_id,
            user_id=user_id,
            job_title=job_title,
            company=company,
            nudge_type="check_in",
            message=f"Have you heard back from {company}?",
            next_nudge_date=first_nudge_date,
            nudge_count=0,
            status="active",
        )

    def get_next_nudge(self, current_count: int, company: str = "") -> tuple[str, str, int]:
        """Get the next nudge type and message based on count."""
        for days, ntype, msg in _NUDGE_SCHEDULE:
            if days > (current_count * 7 + 3):
                return ntype, msg.format(company=company), days
        return "stale", f"No response after a month from {company}. Consider moving on.", 30

    def advance_nudge(self, nudge: NudgeItem) -> NudgeItem:
        """Advance to the next nudge in the schedule."""
        nudge.nudge_count += 1
        ntype, message, days = self.get_next_nudge(nudge.nudge_count, nudge.company)
        nudge.nudge_type = ntype
        nudge.message = message
        nudge.next_nudge_date = datetime.now(timezone.utc) + timedelta(days=days)
        if ntype == "stale":
            nudge.status = "completed"
        return nudge

    def draft_follow_up_email(
        self, job_title: str, company: str, nudge_count: int,
        user_name: str = "",
    ) -> str:
        """Generate an AI-drafted follow-up email."""
        try:
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=512,
                system=(
                    "You are a career communication expert. Draft a professional, warm follow-up email "
                    "for a job application. Keep it brief (3-4 paragraphs max). "
                    "Do not be pushy or desperate. Be genuinely interested and professional."
                ),
                messages=[{
                    "role": "user",
                    "content": (
                        f"Job Title: {job_title}\n"
                        f"Company: {company}\n"
                        f"Follow-up number: {nudge_count}\n"
                        f"Applicant name: {user_name or 'the applicant'}\n\n"
                        "Draft a follow-up email."
                    ),
                }],
            )
            return cast(TextBlock, response.content[0]).text.strip()
        except Exception:
            logger.warning("Failed to draft follow-up email", exc_info=True)
            return ""
