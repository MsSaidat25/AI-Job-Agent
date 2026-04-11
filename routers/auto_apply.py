"""Auto-apply endpoints (Sprint 3)."""

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from routers.schemas import AgentResponse

router = APIRouter(prefix="/api/auto-apply", tags=["auto-apply"])


# ── Request / Response schemas ───────────────────────────────────────────────


class AutoApplySettingsResponse(BaseModel):
    user_id: str
    enabled: bool = False
    confidence_threshold: float = 0.85
    safe_channels: list[str] = Field(default_factory=list)
    max_daily: int = 5


class AutoApplySettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    safe_channels: Optional[list[str]] = None
    max_daily: Optional[int] = Field(default=None, ge=1, le=50)


class QueueItem(BaseModel):
    id: str
    job_id: str
    job_title: str = ""
    company: str = ""
    channel: str = "email"
    confidence_score: float = 0.0
    status: str = "queued"
    reason: str = ""
    created_at: Optional[str] = None


class QueueListResponse(BaseModel):
    items: list[QueueItem]
    total: int


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.get("/settings", response_model=AutoApplySettingsResponse)
    @limiter.limit("30/minute")
    async def get_auto_apply_settings(
        request: Request,
        session_id: str = session_dep,
    ):
        """Get auto-apply settings for the current user."""
        from src.models import AutoApplySettingsORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            settings = db.query(AutoApplySettingsORM).filter_by(user_id=profile.id).first()
            if not settings:
                return AutoApplySettingsResponse(user_id=profile.id)
            s: Any = settings
            return AutoApplySettingsResponse(
                user_id=s.user_id,
                enabled=s.enabled,
                confidence_threshold=s.confidence_threshold,
                safe_channels=s.safe_channels or [],
                max_daily=s.max_daily,
            )
        finally:
            db.close()

    @router.put("/settings", response_model=AutoApplySettingsResponse)
    @limiter.limit("10/minute")
    async def update_auto_apply_settings(
        request: Request,
        body: AutoApplySettingsRequest,
        session_id: str = session_dep,
    ):
        """Update auto-apply settings."""
        from src.models import AutoApplySettingsORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            settings = db.query(AutoApplySettingsORM).filter_by(user_id=profile.id).first()
            if not settings:
                settings = AutoApplySettingsORM(user_id=profile.id)
                db.add(settings)
            s: Any = settings
            if body.enabled is not None:
                s.enabled = body.enabled
            if body.confidence_threshold is not None:
                s.confidence_threshold = body.confidence_threshold
            if body.safe_channels is not None:
                s.safe_channels = body.safe_channels
            if body.max_daily is not None:
                s.max_daily = body.max_daily
            db.commit()
            return AutoApplySettingsResponse(
                user_id=s.user_id,
                enabled=s.enabled,
                confidence_threshold=s.confidence_threshold,
                safe_channels=s.safe_channels or [],
                max_daily=s.max_daily,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.get("/queue", response_model=QueueListResponse)
    @limiter.limit("30/minute")
    async def get_auto_apply_queue(
        request: Request,
        session_id: str = session_dep,
    ):
        """View queued auto-apply applications."""
        from src.models import AutoApplyQueueORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            rows = (
                db.query(AutoApplyQueueORM)
                .filter_by(user_id=profile.id)
                .order_by(AutoApplyQueueORM.created_at.desc())
                .all()
            )
            items = []
            for row in rows:
                q: Any = row
                items.append(QueueItem(
                    id=q.id,
                    job_id=q.job_id,
                    job_title=q.job_title,
                    company=q.company,
                    channel=q.channel,
                    confidence_score=q.confidence_score,
                    status=q.status,
                    reason=q.reason,
                    created_at=str(q.created_at) if q.created_at else None,
                ))
            return QueueListResponse(items=items, total=len(items))
        finally:
            db.close()

    @router.post("/queue/{item_id}/approve", response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def approve_queue_item(
        request: Request,
        item_id: str,
        session_id: str = session_dep,
    ):
        """Approve a queued auto-apply application."""
        from src.models import AutoApplyQueueORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            item = db.query(AutoApplyQueueORM).filter_by(id=item_id).first()
            if not item:
                raise HTTPException(status_code=404, detail="Queue item not found.")
            q: Any = item
            if q.user_id != profile.id:
                raise HTTPException(status_code=403, detail="Access denied.")
            q.status = "approved"
            db.commit()
            return AgentResponse(response=f"Application to {q.company} approved for sending.")
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.post("/queue/{item_id}/reject", response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def reject_queue_item(
        request: Request,
        item_id: str,
        session_id: str = session_dep,
    ):
        """Reject a queued auto-apply application."""
        from src.models import AutoApplyQueueORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            item = db.query(AutoApplyQueueORM).filter_by(id=item_id).first()
            if not item:
                raise HTTPException(status_code=404, detail="Queue item not found.")
            q: Any = item
            if q.user_id != profile.id:
                raise HTTPException(status_code=403, detail="Access denied.")
            q.status = "rejected"
            db.commit()
            return AgentResponse(response=f"Application to {q.company} rejected.")
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.get("/briefing", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def morning_briefing(
        request: Request,
        session_id: str = session_dep,
    ):
        """Generate morning briefing on auto-apply queue status."""
        from src.auto_apply_service import AutoApplyService
        from src.session_store import get_session_profile

        get_session_profile(session_id)
        service = AutoApplyService()
        result = await asyncio.to_thread(service.generate_briefing, [])
        return AgentResponse(response=result.summary)
