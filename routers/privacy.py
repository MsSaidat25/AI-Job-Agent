"""Privacy ledger and EU AI Act compliance export endpoints."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from slowapi import Limiter


router = APIRouter(prefix="/api/privacy", tags=["privacy"])


class LedgerEntry(BaseModel):
    id: str
    action: str
    tool_name: str = ""
    data_categories: list[str] = Field(default_factory=list)
    purpose: str = ""
    llm_provider: str = ""
    llm_model: str = ""
    retention_days: int = 0
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class LedgerResponse(BaseModel):
    entries: list[LedgerEntry] = Field(default_factory=list)
    total: int = 0


class PrivacyExportResponse(BaseModel):
    """EU AI Act-aligned compliance export.

    See ``src/privacy_ledger.py::export_for_user`` for the field contract.
    """
    generated_at: str
    user_id: str
    window_days: int
    system: dict[str, Any]
    risk_classification: dict[str, Any]
    data_categories_processed: list[str]
    retention_summary_days: dict[str, int]
    counts: dict[str, Any]
    entries: list[LedgerEntry]


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.get("/ledger", response_model=LedgerResponse)
    @limiter.limit("10/minute")
    async def get_ledger_endpoint(
        request: Request,
        limit: int = Query(100, ge=1, le=1000),
        session_id: str = session_dep,
    ):
        """Return the most recent ``limit`` privacy-ledger rows for the user."""
        from src.models import init_db
        from src.privacy_ledger import get_ledger
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)

        def _fetch():
            db = init_db()
            try:
                return get_ledger(db, profile.id, limit=limit)
            finally:
                db.close()

        entries = await asyncio.to_thread(_fetch)
        return LedgerResponse(
            entries=[LedgerEntry(**e) for e in entries],
            total=len(entries),
        )

    @router.get("/export", response_model=PrivacyExportResponse)
    @limiter.limit("5/minute")
    async def privacy_export(
        request: Request,
        window_days: int = Query(365, ge=1, le=3650),
        session_id: str = session_dep,
    ):
        """EU AI Act-aligned compliance export for the current user.

        Returns a JSON bundle covering system metadata, self-assessed risk
        classification, processed data categories, retention summary, and
        the raw ledger entries from the requested window. The frontend
        renders this as a JSON download.
        """
        from src.models import init_db
        from src.privacy_ledger import export_for_user
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)

        def _build():
            db = init_db()
            try:
                return export_for_user(db, profile.id, window_days=window_days)
            finally:
                db.close()

        bundle = await asyncio.to_thread(_build)
        return PrivacyExportResponse(
            generated_at=bundle["generated_at"],
            user_id=bundle["user_id"],
            window_days=bundle["window_days"],
            system=bundle["system"],
            risk_classification=bundle["risk_classification"],
            data_categories_processed=bundle["data_categories_processed"],
            retention_summary_days=bundle["retention_summary_days"],
            counts=bundle["counts"],
            entries=[LedgerEntry(**e) for e in bundle["entries"]],
        )
