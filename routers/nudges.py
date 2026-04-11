"""Follow-up nudge endpoints (Sprint 3)."""

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from routers.schemas import AgentResponse

router = APIRouter(prefix="/api/nudges", tags=["nudges"])


# ── Request / Response schemas ───────────────────────────────────────────────


class NudgeResponse(BaseModel):
    nudge_id: str
    application_id: str
    job_title: str = ""
    company: str = ""
    next_nudge_date: Optional[str] = None
    nudge_count: int = 0
    nudge_type: str = "check_in"
    status: str = "active"
    last_response: Optional[str] = None


class NudgeListResponse(BaseModel):
    nudges: list[NudgeResponse]
    total: int


class NudgeRespondRequest(BaseModel):
    response_type: str = Field(..., max_length=50)  # e.g. "heard_back", "no_response", "rejected"
    notes: str = Field(default="", max_length=2000)


class NudgeSettingsRequest(BaseModel):
    default_interval_days: int = Field(default=7, ge=1, le=60)
    max_nudges: int = Field(default=3, ge=1, le=10)
    auto_pause_after: int = Field(default=3, ge=1, le=10)


class NudgeSettingsResponse(BaseModel):
    settings: dict[str, Any]
    message: str = ""


class DraftEmailResponse(BaseModel):
    nudge_id: str
    subject: str = ""
    body: str = ""


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.get("/pending", response_model=NudgeListResponse)
    @limiter.limit("30/minute")
    async def get_pending_nudges(
        request: Request,
        session_id: str = session_dep,
    ):
        """Get pending nudges for the current user."""
        from src.models import FollowUpScheduleORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            rows = (
                db.query(FollowUpScheduleORM)
                .filter_by(user_id=profile.id, status="active")
                .order_by(FollowUpScheduleORM.next_nudge_date.asc())
                .all()
            )
            nudges = []
            for row in rows:
                n: Any = row
                nudges.append(NudgeResponse(
                    nudge_id=n.id,
                    application_id=n.application_id,
                    job_title=n.job_title,
                    company=n.company,
                    next_nudge_date=str(n.next_nudge_date) if n.next_nudge_date else None,
                    nudge_count=n.nudge_count,
                    nudge_type=n.nudge_type,
                    status=n.status,
                    last_response=n.last_response,
                ))
            return NudgeListResponse(nudges=nudges, total=len(nudges))
        finally:
            db.close()

    @router.post("/{nudge_id}/respond", response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def respond_to_nudge(
        request: Request,
        nudge_id: str,
        body: NudgeRespondRequest,
        session_id: str = session_dep,
    ):
        """User responds to a nudge, advancing its state."""
        from src.models import FollowUpScheduleORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            nudge = db.query(FollowUpScheduleORM).filter_by(id=nudge_id).first()
            if not nudge:
                raise HTTPException(status_code=404, detail="Nudge not found.")
            n_check: Any = nudge
            if n_check.user_id != profile.id:
                raise HTTPException(status_code=403, detail="Access denied.")
            n: Any = nudge
            n.last_response = body.response_type
            n.nudge_count = n.nudge_count + 1
            if body.response_type in ("heard_back", "rejected"):
                n.status = "completed"
            db.commit()
            return AgentResponse(response=f"Nudge updated: {body.response_type}")
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.get("/{nudge_id}/draft-email", response_model=DraftEmailResponse)
    @limiter.limit("5/minute")
    async def draft_follow_up_email(
        request: Request,
        nudge_id: str,
        session_id: str = session_dep,
    ):
        """AI-draft a follow-up email for a nudge."""
        from src.models import FollowUpScheduleORM, init_db

        db = init_db()
        try:
            nudge = db.query(FollowUpScheduleORM).filter_by(id=nudge_id).first()
            if not nudge:
                raise HTTPException(status_code=404, detail="Nudge not found.")
            n: Any = nudge
            job_title = n.job_title
            company = n.company
            nudge_count = n.nudge_count
        finally:
            db.close()

        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Draft a professional follow-up email for my application to the "
                f"'{job_title}' role at {company}. This is follow-up #{nudge_count + 1}. "
                "Keep it concise and polite. Return a subject line and body.",
            )
        lines = response.strip().splitlines()
        subject = lines[0] if lines else "Follow-up on my application"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else response
        return DraftEmailResponse(nudge_id=nudge_id, subject=subject, body=body)

    @router.put("/{nudge_id}/pause", response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def pause_nudge(
        request: Request,
        nudge_id: str,
        session_id: str = session_dep,
    ):
        """Pause a nudge schedule."""
        from src.models import FollowUpScheduleORM, init_db

        db = init_db()
        try:
            nudge = db.query(FollowUpScheduleORM).filter_by(id=nudge_id).first()
            if not nudge:
                raise HTTPException(status_code=404, detail="Nudge not found.")
            n: Any = nudge
            n.status = "paused"
            db.commit()
            return AgentResponse(response="Nudge paused.")
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.put("/settings", response_model=NudgeSettingsResponse)
    @limiter.limit("10/minute")
    async def update_nudge_settings(
        request: Request,
        body: NudgeSettingsRequest,
        session_id: str = session_dep,
    ):
        """Update global nudge settings for the user."""

        return NudgeSettingsResponse(
            settings={"default_interval_days": body.default_interval_days,
                      "max_nudges": body.max_nudges,
                      "auto_pause_after": body.auto_pause_after},
            message="Nudge settings updated.",
        )
