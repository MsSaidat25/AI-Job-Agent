"""Kanban board API router -- drag-and-drop application tracking."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from src.models import ApplicationStatus

router = APIRouter(prefix="/api/kanban", tags=["kanban"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class KanbanColumn(BaseModel):
    status: str
    label: str
    color: str
    cards: list[KanbanCard] = Field(default_factory=list)


class KanbanCard(BaseModel):
    id: str
    job_id: str
    job_title: str = ""
    company: str = ""
    location: str = ""
    status: str
    submitted_at: Optional[str] = None
    last_updated: Optional[str] = None
    notes: str = ""
    match_score: Optional[float] = None
    source_url: str = ""


class KanbanBoardResponse(BaseModel):
    columns: list[KanbanColumn]
    total_cards: int


class MoveCardRequest(BaseModel):
    new_status: ApplicationStatus
    notes: Optional[str] = None


class MoveCardResponse(BaseModel):
    id: str
    old_status: str
    new_status: str
    message: str


# Column configuration matching ApplicationStatus enum
_COLUMNS = [
    {"status": ApplicationStatus.DRAFT.value, "label": "Saved", "color": "#6b7280"},
    {"status": ApplicationStatus.SUBMITTED.value, "label": "Applied", "color": "#3b82f6"},
    {"status": ApplicationStatus.UNDER_REVIEW.value, "label": "Under Review", "color": "#f59e0b"},
    {"status": ApplicationStatus.INTERVIEW_SCHEDULED.value, "label": "Interview", "color": "#8b5cf6"},
    {"status": ApplicationStatus.OFFER_RECEIVED.value, "label": "Offer", "color": "#10b981"},
    {"status": ApplicationStatus.REJECTED.value, "label": "Rejected", "color": "#ef4444"},
    {"status": ApplicationStatus.WITHDRAWN.value, "label": "Withdrawn", "color": "#9ca3af"},
]


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    session_dep: Any,
) -> None:
    """Wire Kanban endpoints using the app's shared dependencies."""

    @router.get("/board", response_model=KanbanBoardResponse)
    @limiter.limit("30/minute")
    async def get_board(request: Request, session_id: str = session_dep):
        """Return the full Kanban board with all columns and cards."""
        agent = get_agent_fn(session_id)
        records = await asyncio.to_thread(
            agent._tracker.get_applications, agent.profile.id,
        )

        # Build column map
        column_map: dict[str, list[KanbanCard]] = {col["status"]: [] for col in _COLUMNS}

        for rec in records:
            cached = agent._job_cache.get(rec.job_id, {})
            card = KanbanCard(
                id=rec.id,
                job_id=rec.job_id,
                job_title=cached.get("job_title", "Unknown Position"),
                company=cached.get("employer_name", "Unknown Company"),
                location=_build_location(cached),
                status=rec.status.value,
                submitted_at=rec.submitted_at.isoformat() if rec.submitted_at else None,
                last_updated=rec.last_updated.isoformat() if rec.last_updated else None,
                notes=rec.notes,
                match_score=cached.get("match_score"),
                source_url=cached.get("job_apply_link", ""),
            )
            if rec.status.value in column_map:
                column_map[rec.status.value].append(card)

        columns = [
            KanbanColumn(
                status=col["status"],
                label=col["label"],
                color=col["color"],
                cards=column_map.get(col["status"], []),
            )
            for col in _COLUMNS
        ]

        total = sum(len(col.cards) for col in columns)
        return KanbanBoardResponse(columns=columns, total_cards=total)

    @router.put("/cards/{card_id}/move", response_model=MoveCardResponse)
    @limiter.limit("30/minute")
    async def move_card(
        request: Request,
        card_id: str,
        body: MoveCardRequest,
        session_id: str = session_dep,
    ):
        """Move a card to a different column (update application status)."""
        agent = get_agent_fn(session_id)

        # Get current application
        app = await asyncio.to_thread(agent._tracker.get_application, card_id)
        if not app:
            raise HTTPException(status_code=404, detail="Application not found.")

        old_status = app.status.value

        # Update via tracker
        await asyncio.to_thread(
            agent._tracker.update_status,
            card_id,
            body.new_status,
            None,
            body.notes,
        )

        return MoveCardResponse(
            id=card_id,
            old_status=old_status,
            new_status=body.new_status.value,
            message=f"Moved from {old_status} to {body.new_status.value}",
        )

    @router.get("/cards/{card_id}", response_model=KanbanCard)
    @limiter.limit("30/minute")
    async def get_card(
        request: Request,
        card_id: str,
        session_id: str = session_dep,
    ):
        """Get details for a single Kanban card."""
        agent = get_agent_fn(session_id)
        app = await asyncio.to_thread(agent._tracker.get_application, card_id)
        if not app:
            raise HTTPException(status_code=404, detail="Application not found.")

        cached = agent._job_cache.get(app.job_id, {})
        return KanbanCard(
            id=app.id,
            job_id=app.job_id,
            job_title=cached.get("job_title", "Unknown Position"),
            company=cached.get("employer_name", "Unknown Company"),
            location=_build_location(cached),
            status=app.status.value,
            submitted_at=app.submitted_at.isoformat() if app.submitted_at else None,
            last_updated=app.last_updated.isoformat() if app.last_updated else None,
            notes=app.notes,
            match_score=cached.get("match_score"),
            source_url=cached.get("job_apply_link", ""),
        )


def _build_location(cached: dict[str, Any]) -> str:
    """Build location string from cached job data."""
    city = cached.get("job_city", "")
    state = cached.get("job_state", "")
    country = cached.get("job_country", "")
    parts = [p for p in [city, state, country] if p]
    return ", ".join(parts) if parts else ""
