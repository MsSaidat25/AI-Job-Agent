"""
Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com).
All Rights Reserved.
No part of this software or any of its contents may be reproduced, copied,
modified or adapted, without the prior written consent of the author, unless
otherwise indicated for stand-alone materials.
For permission requests, write to the publisher at the email address below:
avien@aviensolutions.com
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

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
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional, cast

import anthropic
from anthropic.types import TextBlock
from sqlalchemy.orm import Session, joinedload

from config.settings import AGENT_MODEL
from src.llm_client import create_message_with_failover
from src.models import (
    ApplicationRecord,
    ApplicationRecordORM,
    ApplicationStatus,
    init_db,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApplicationTracker:
    """CRUD + analytics for job applications."""

    def __init__(
        self,
        session: Session | None = None,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self._session = session or init_db()
        self._client = client or anthropic.Anthropic()

    def close(self) -> None:
        """Close the underlying DB session to release connections."""
        if self._session:
            self._session.close()

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
        orm.status = new_status.value  # type: ignore[assignment]
        orm.last_updated = _utcnow()  # type: ignore[assignment]
        if feedback is not None:
            orm.employer_feedback = feedback  # type: ignore[assignment]
        if notes is not None:
            orm.notes = notes  # type: ignore[assignment]
        self._session.commit()
        return self._orm_to_model(orm)

    def get_applications(self, user_id: str) -> list[ApplicationRecord]:
        """Return all applications for a user.

        Eager-loads the related ``JobListingORM`` so callers that access
        ``rec.job.*`` in a loop (e.g. kanban board rendering) don't trigger
        an N+1 query pattern.
        """
        rows = (
            self._session.query(ApplicationRecordORM)
            .options(joinedload(ApplicationRecordORM.job))
            .filter_by(user_id=user_id)
            .all()
        )
        return [self._orm_to_model(r) for r in rows]

    def get_application(self, application_id: str) -> Optional[ApplicationRecord]:
        orm = (
            self._session.query(ApplicationRecordORM)
            .options(joinedload(ApplicationRecordORM.job))
            .filter_by(id=application_id)
            .first()
        )
        return self._orm_to_model(orm) if orm else None

    # ── Analytics ──────────────────────────────────────────────────────────

    def compute_metrics(self, user_id: str) -> dict:
        """Return a metrics dict with rates, status counts, and breakdowns."""
        app_orms = (
            self._session.query(ApplicationRecordORM)
            .options(joinedload(ApplicationRecordORM.job))
            .filter_by(user_id=user_id)
            .all()
        )
        apps = [self._orm_to_model(orm) for orm in app_orms]
        if not apps:
            return {"total": 0, "message": "No applications yet."}

        rates = self._compute_rates(apps)
        breakdowns = self._compute_breakdowns(app_orms)
        return {**rates, **breakdowns}

    @staticmethod
    def _compute_rates(apps: list[ApplicationRecord]) -> dict:
        """Compute response/interview/offer rates and avg reply time."""
        submitted = [a for a in apps if a.status != ApplicationStatus.DRAFT]
        got_reply = [
            a for a in submitted
            if a.status not in {ApplicationStatus.SUBMITTED, ApplicationStatus.DRAFT}
        ]
        interviewed = [
            a for a in apps
            if a.status in {ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.OFFER_RECEIVED}
        ]
        offered = [a for a in apps if a.status == ApplicationStatus.OFFER_RECEIVED]
        n_sub = max(len(submitted), 1)

        reply_days = [
            (a.last_updated - a.submitted_at).days
            for a in got_reply
            if a.submitted_at and a.last_updated and (a.last_updated - a.submitted_at).days >= 0
        ]

        return {
            "total": len(apps),
            "submitted": len(submitted),
            "response_rate": len(got_reply) / n_sub,
            "interview_rate": len(interviewed) / n_sub,
            "offer_rate": len(offered) / n_sub,
            "avg_days_to_reply": round(sum(reply_days) / len(reply_days), 1) if reply_days else None,
            "by_status": dict(Counter(a.status.value for a in apps)),
        }

    @staticmethod
    def _compute_breakdowns(app_orms: list) -> dict:  # type: ignore[type-arg]
        """Extract industry and platform breakdowns from eager-loaded ORM records."""
        industry_counter: Counter = Counter()
        platform_counter: Counter = Counter()
        for orm in app_orms:
            job_orm = orm.job  # type: ignore[union-attr]
            if job_orm:
                if job_orm.industry:  # type: ignore[truthy-bool]
                    industry_counter[job_orm.industry] += 1
                if job_orm.source_platform:  # type: ignore[truthy-bool]
                    platform_counter[job_orm.source_platform] += 1
        return {
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
        response = create_message_with_failover(
            self._client,
            model=AGENT_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return cast(TextBlock, response.content[0]).text.strip()

    # ── Resume A/B: per-variant response-rate loop ────────────────────────

    def compute_variant_performance(self, user_id: str) -> dict:
        """Aggregate per-variant response rates for the A/B resume loop.

        For every ``DocumentVariantORM`` owned by ``user_id`` that has been
        linked to an application (``application_id`` not NULL), we count how
        many of those applications progressed past ``SUBMITTED`` -- i.e.
        received any form of employer response. That gives us a per-tone
        response rate we can rank, surface to the user, and feed back into
        document generation (the "winning" template).

        Returns a dict with:
            - ``variants`` — list of per-tone buckets, sorted by response rate
            - ``winning_variant_id`` — id of a sample variant from the top
              tone IF it has statistically meaningful signal, else None
            - ``total_variants`` — number of distinct tones with samples
        """
        from src.models import DocumentVariantORM  # local import to avoid cycles

        rows: list[Any] = (
            self._session.query(DocumentVariantORM)
            .filter(
                DocumentVariantORM.user_id == user_id,
                DocumentVariantORM.application_id.isnot(None),
            )
            .all()
        )
        if not rows:
            return {"variants": [], "winning_variant_id": None, "total_variants": 0}

        app_ids = {str(r.application_id) for r in rows if r.application_id}
        app_map: dict[str, ApplicationRecordORM] = {}
        if app_ids:
            app_rows = (
                self._session.query(ApplicationRecordORM)
                .filter(ApplicationRecordORM.id.in_(app_ids))
                .all()
            )
            for a in app_rows:
                app_map[str(a.id)] = a

        by_tone: dict[str, dict[str, Any]] = {}
        responded_statuses = {
            ApplicationStatus.UNDER_REVIEW.value,
            ApplicationStatus.INTERVIEW_SCHEDULED.value,
            ApplicationStatus.OFFER_RECEIVED.value,
            ApplicationStatus.REJECTED.value,
        }

        for v in rows:
            tone = str(v.resume_tone or "professional")
            bucket = by_tone.setdefault(
                tone,
                {
                    "resume_tone": tone,
                    "sample_variant_id": str(v.id),
                    "total_applications": 0,
                    "submitted": 0,
                    "responses": 0,
                    "interviews": 0,
                    "offers": 0,
                    "avg_ats_score": 0.0,
                    "_ats_sum": 0.0,
                    "_ats_count": 0,
                },
            )
            bucket["total_applications"] += 1
            if v.ats_score is not None:
                bucket["_ats_sum"] += float(v.ats_score)
                bucket["_ats_count"] += 1

            app = app_map.get(str(v.application_id))
            if app is None:
                continue
            status = str(app.status)
            if status != ApplicationStatus.DRAFT.value:
                bucket["submitted"] += 1
            if status in responded_statuses:
                bucket["responses"] += 1
            if status in (
                ApplicationStatus.INTERVIEW_SCHEDULED.value,
                ApplicationStatus.OFFER_RECEIVED.value,
            ):
                bucket["interviews"] += 1
            if status == ApplicationStatus.OFFER_RECEIVED.value:
                bucket["offers"] += 1

        variants: list[dict[str, Any]] = []
        for bucket in by_tone.values():
            denom = max(bucket["submitted"], 1)
            bucket["response_rate"] = round(bucket["responses"] / denom, 4)
            bucket["interview_rate"] = round(bucket["interviews"] / denom, 4)
            bucket["offer_rate"] = round(bucket["offers"] / denom, 4)
            if bucket["_ats_count"]:
                bucket["avg_ats_score"] = round(
                    bucket["_ats_sum"] / bucket["_ats_count"], 2
                )
            bucket.pop("_ats_sum", None)
            bucket.pop("_ats_count", None)
            variants.append(bucket)

        variants.sort(
            key=lambda v: (v["response_rate"], v["submitted"]),
            reverse=True,
        )

        # Declare a winner only when the signal is unambiguous:
        #   - top tone has >= 3 submissions AND beats runner-up by >= 10 pts, OR
        #   - top tone has >= 5 submissions AND hits a perfect response rate.
        winning_variant_id: Optional[str] = None
        if variants:
            top = variants[0]
            if top["submitted"] >= 3:
                runner_up = variants[1] if len(variants) > 1 else None
                margin = (
                    top["response_rate"] - runner_up["response_rate"]
                    if runner_up
                    else top["response_rate"]
                )
                if margin >= 0.10 or (top["submitted"] >= 5 and top["response_rate"] >= 1.0):
                    winning_variant_id = top["sample_variant_id"]

        return {
            "variants": variants,
            "winning_variant_id": winning_variant_id,
            "total_variants": len(variants),
        }

    def mark_winning_variant(self, variant_id: str) -> bool:
        """Persist ``status='winning'`` for a specific variant.

        Returns True if the row was found and updated, False otherwise.
        """
        from src.models import DocumentVariantORM

        orm = (
            self._session.query(DocumentVariantORM)
            .filter_by(id=variant_id)
            .first()
        )
        if orm is None:
            return False
        orm.status = "winning"  # type: ignore[assignment]
        self._session.commit()
        return True

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
        response = create_message_with_failover(
            self._client,
            model=AGENT_MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return cast(TextBlock, response.content[0]).text.strip()

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _orm_to_model(orm: ApplicationRecordORM) -> ApplicationRecord:
        orm_any = cast(Any, orm)
        return ApplicationRecord(
            id=orm_any.id,
            user_id=orm_any.user_id,
            job_id=orm_any.job_id,
            status=ApplicationStatus(orm_any.status),
            resume_version=orm_any.resume_version,
            cover_letter_version=orm_any.cover_letter_version,
            submitted_at=orm_any.submitted_at,
            last_updated=orm_any.last_updated,
            employer_feedback=orm_any.employer_feedback,
            interview_dates=[
                datetime.fromisoformat(d)
                for d in (orm_any.interview_dates or [])
                if isinstance(d, str)
            ],
            notes=orm_any.notes or "",
        )
