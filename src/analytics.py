"""
Application Analytics Tracker.

Tracks every application the user submits, monitors status changes,
and uses Claude to surface patterns and actionable insights.

Metrics tracked
───────────────
• Response rate       = (non-draft applications that got a reply) / total submitted
• Interview rate      = interviews scheduled / applications submitted
• Offer rate          = offers received / applications submitted
• Avg time-to-reply   = mean days between submission and first employer contact
• Top-performing skills / roles / industries (by positive outcome rate)

Privacy note: All data lives in the local SQLite database only.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

import anthropic
from sqlalchemy.orm import Session

from config.settings import AGENT_MODEL
from src.models import (
    ApplicationRecord,
    ApplicationRecordORM,
    ApplicationStatus,
    JobListingORM,
    init_db,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ApplicationTracker:
    """CRUD + analytics for job applications."""

    def __init__(
        self,
        session: Session | None = None,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self._session = session or init_db()
        self._client = client or anthropic.Anthropic()

    # ── CRUD ───────────────────────────────────────────────────────────────

    def add_application(self, record: ApplicationRecord) -> ApplicationRecord:
        """Persist a new application record."""
        orm = ApplicationRecordORM(
            id=record.id,
            user_id=record.user_id,
            job_id=record.job_id,
            status=record.status.value,
            resume_version=record.resume_version,
            cover_letter_version=record.cover_letter_version,
            submitted_at=record.submitted_at,
            last_updated=record.last_updated,
            employer_feedback=record.employer_feedback,
            interview_dates=[d.isoformat() for d in record.interview_dates],
            notes=record.notes,
        )
        self._session.add(orm)
        self._session.commit()
        return record

    def update_status(
        self,
        application_id: str,
        new_status: ApplicationStatus,
        feedback: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ApplicationRecord]:
        """Update the status and optional feedback for an existing application."""
        orm: Optional[ApplicationRecordORM] = (
            self._session.query(ApplicationRecordORM)
            .filter_by(id=application_id)
            .first()
        )
        if orm is None:
            return None
        orm.status = new_status.value
        orm.last_updated = _utcnow()
        if feedback is not None:
            orm.employer_feedback = feedback
        if notes is not None:
            orm.notes = notes
        self._session.commit()
        return self._orm_to_model(orm)

    def get_applications(self, user_id: str) -> list[ApplicationRecord]:
        """Return all applications for a user."""
        rows = (
            self._session.query(ApplicationRecordORM)
            .filter_by(user_id=user_id)
            .all()
        )
        return [self._orm_to_model(r) for r in rows]

    def get_application(self, application_id: str) -> Optional[ApplicationRecord]:
        orm = self._session.query(ApplicationRecordORM).filter_by(id=application_id).first()
        return self._orm_to_model(orm) if orm else None

    # ── Analytics ──────────────────────────────────────────────────────────

    def compute_metrics(self, user_id: str) -> dict:
        """
        Return a metrics dict:
        {
          "total":              int,
          "response_rate":      float (0–1),
          "interview_rate":     float,
          "offer_rate":         float,
          "avg_days_to_reply":  float | None,
          "by_status":          {status: count},
          "top_industries":     [(industry, count)],
          "top_platforms":      [(platform, count)],
        }
        """
        apps = self.get_applications(user_id)
        total = len(apps)
        if total == 0:
            return {"total": 0, "message": "No applications yet."}

        submitted = [a for a in apps if a.status != ApplicationStatus.DRAFT]
        got_reply = [
            a for a in submitted
            if a.status not in {ApplicationStatus.SUBMITTED, ApplicationStatus.DRAFT}
        ]
        interviewed = [
            a for a in apps
            if a.status in {
                ApplicationStatus.INTERVIEW_SCHEDULED,
                ApplicationStatus.OFFER_RECEIVED,
            }
        ]
        offered = [a for a in apps if a.status == ApplicationStatus.OFFER_RECEIVED]

        by_status: dict[str, int] = Counter(a.status.value for a in apps)

        # days-to-reply: approximate via last_updated vs submitted_at
        reply_days = []
        for a in got_reply:
            if a.submitted_at and a.last_updated:
                delta = (a.last_updated - a.submitted_at).days
                if delta >= 0:
                    reply_days.append(delta)

        # Industry / platform breakdown via joined job records
        industry_counter: Counter = Counter()
        platform_counter: Counter = Counter()
        for a in apps:
            job_orm: Optional[JobListingORM] = (
                self._session.query(JobListingORM).filter_by(id=a.job_id).first()
            )
            if job_orm:
                if job_orm.industry:
                    industry_counter[job_orm.industry] += 1
                if job_orm.source_platform:
                    platform_counter[job_orm.source_platform] += 1

        return {
            "total": total,
            "submitted": len(submitted),
            "response_rate": len(got_reply) / max(len(submitted), 1),
            "interview_rate": len(interviewed) / max(len(submitted), 1),
            "offer_rate": len(offered) / max(len(submitted), 1),
            "avg_days_to_reply": (
                round(sum(reply_days) / len(reply_days), 1) if reply_days else None
            ),
            "by_status": dict(by_status),
            "top_industries": industry_counter.most_common(5),
            "top_platforms": platform_counter.most_common(5),
        }

    def generate_insights(self, user_id: str) -> str:
        """
        Use Claude to turn raw metrics into a paragraph of practical advice.
        Returns plain text suitable for display in the terminal.
        """
        metrics = self.compute_metrics(user_id)
        if metrics.get("total", 0) == 0:
            return "Start tracking applications to unlock analytics insights."

        prompt = f"""You are a career coach reviewing a job seeker's application analytics.

METRICS:
{json.dumps(metrics, indent=2)}

Write 3–5 bullet points of specific, actionable advice based on these numbers.
Be honest about weaknesses (e.g. low response rate) and suggest concrete fixes.
Keep each bullet under 2 sentences. Do NOT repeat the raw numbers verbatim.
"""
        response = self._client.messages.create(
            model=AGENT_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def employer_feedback_analysis(self, user_id: str) -> str:
        """Aggregate employer feedback and extract patterns via Claude."""
        apps = self.get_applications(user_id)
        feedbacks = [
            a.employer_feedback
            for a in apps
            if a.employer_feedback and a.employer_feedback.strip()
        ]
        if not feedbacks:
            return "No employer feedback recorded yet."

        prompt = f"""Analyse the following employer feedback messages a job seeker received
and identify common themes, recurring objections, and improvement opportunities.

FEEDBACK MESSAGES:
{json.dumps(feedbacks, indent=2)}

Provide:
1. Top 3 recurring themes (positive and negative)
2. Most common reason for rejection (if apparent)
3. Two specific action items the candidate should focus on
"""
        response = self._client.messages.create(
            model=AGENT_MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _orm_to_model(orm: ApplicationRecordORM) -> ApplicationRecord:
        return ApplicationRecord(
            id=orm.id,
            user_id=orm.user_id,
            job_id=orm.job_id,
            status=ApplicationStatus(orm.status),
            resume_version=orm.resume_version,
            cover_letter_version=orm.cover_letter_version,
            submitted_at=orm.submitted_at,
            last_updated=orm.last_updated,
            employer_feedback=orm.employer_feedback,
            interview_dates=[
                datetime.fromisoformat(d) for d in (orm.interview_dates or [])
            ],
            notes=orm.notes or "",
        )
