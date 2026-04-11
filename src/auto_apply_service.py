"""Autonomous Apply Service -- confidence scoring, queue management, and auto-apply logic."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AutoApplySettings(BaseModel):
    user_id: str = ""
    enabled: bool = False
    confidence_threshold: float = 0.85
    safe_channels: list[str] = Field(default_factory=lambda: ["email", "career_page"])
    max_daily: int = 5
    humanize_documents: bool = True


class QueuedApplication(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    job_title: str = ""
    company: str = ""
    channel: str = ""
    confidence_score: float = 0.0
    status: str = "queued"  # queued, approved, sent, rejected, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""


class ApplyBriefing(BaseModel):
    total_queued: int = 0
    auto_applied: int = 0
    needs_review: int = 0
    blocked: int = 0
    summary: str = ""


class AutoApplyService:
    """Manages autonomous job application logic."""

    def score_confidence(
        self, job: Any, profile: Any,
    ) -> float:
        """Score match confidence between job and profile (0-100)."""
        score = 50.0

        # Check skills overlap
        if hasattr(profile, "skills") and profile.skills:
            job_desc = ""
            if isinstance(job, dict):
                job_desc = (job.get("job_description", "") or "").lower()
            elif hasattr(job, "description"):
                job_desc = (job.description or "").lower()

            if job_desc:
                matched = sum(1 for s in profile.skills if s.lower() in job_desc)
                skill_ratio = matched / max(len(profile.skills), 1)
                score += skill_ratio * 30

        # Check role match
        if hasattr(profile, "desired_roles") and profile.desired_roles:
            job_title = ""
            if isinstance(job, dict):
                job_title = (job.get("job_title", "") or "").lower()
            elif hasattr(job, "title"):
                job_title = (job.title or "").lower()

            for role in profile.desired_roles:
                if role.lower() in job_title:
                    score += 15
                    break

        # Check location match
        if hasattr(profile, "location") and profile.location:
            job_loc = ""
            if isinstance(job, dict):
                job_loc = (job.get("job_city", "") or "").lower()
            elif hasattr(job, "location"):
                job_loc = (job.location or "").lower()

            if profile.location.lower() in job_loc:
                score += 5

        return min(score, 100.0)

    def should_auto_apply(
        self, job: Any, profile: Any, settings: AutoApplySettings,
    ) -> bool:
        """Determine if a job should be auto-applied to."""
        if not settings.enabled:
            return False

        confidence = self.score_confidence(job, profile)
        if confidence < settings.confidence_threshold * 100:
            return False

        # Check non-compete
        company = ""
        if isinstance(job, dict):
            company = job.get("employer_name", job.get("company", ""))
        elif hasattr(job, "company"):
            company = job.company

        if hasattr(profile, "non_compete_companies"):
            if company.lower() in [c.lower() for c in profile.non_compete_companies]:
                return False

        return True

    def check_non_compete(self, company: str, excluded: list[str]) -> bool:
        """Return True if the company is excluded by non-compete."""
        return company.lower() in [c.lower() for c in excluded]

    def queue_application(
        self,
        job_id: str,
        user_id: str,
        job_title: str = "",
        company: str = "",
        channel: str = "email",
        confidence_score: float = 0.0,
    ) -> QueuedApplication:
        """Add an application to the review/send queue."""
        status = "queued"
        if confidence_score >= 85:
            status = "approved"  # Auto-approve high confidence

        return QueuedApplication(
            user_id=user_id,
            job_id=job_id,
            job_title=job_title,
            company=company,
            channel=channel,
            confidence_score=confidence_score,
            status=status,
        )

    def generate_briefing(
        self,
        queued: list[QueuedApplication],
    ) -> ApplyBriefing:
        """Generate a morning briefing summary."""
        auto_applied = sum(1 for q in queued if q.status == "sent")
        needs_review = sum(1 for q in queued if q.status == "queued")
        blocked = sum(1 for q in queued if q.status in ("rejected", "failed"))

        summary_parts = []
        if auto_applied:
            summary_parts.append(f"{auto_applied} applications sent automatically")
        if needs_review:
            summary_parts.append(f"{needs_review} awaiting your review")
        if blocked:
            summary_parts.append(f"{blocked} blocked or failed")

        return ApplyBriefing(
            total_queued=len(queued),
            auto_applied=auto_applied,
            needs_review=needs_review,
            blocked=blocked,
            summary=". ".join(summary_parts) + "." if summary_parts else "No applications in queue.",
        )
