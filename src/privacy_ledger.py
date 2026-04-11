"""Privacy ledger -- append-only audit of data-touching actions.

Exists to satisfy the transparency + record-keeping obligations of the EU
AI Act (Art. 12 "automatic recording of events", Art. 13 "transparency and
provision of information", Art. 26 "obligations of deployers"), and more
generally to give users a durable, human-readable trail of every place
their profile / resume / application data was processed.

The surface area is deliberately small:

* ``log_event(...)`` -- call from any hot path that processes user data.
  Swallows DB failures so an instrumentation outage never takes down the
  agent. Never stores the actual PII -- just the category labels and a
  purpose string.
* ``get_ledger(user_id, since=None, limit=None)`` -- read back entries.
* ``export_for_user(user_id)`` -- return an EU AI Act-aligned bundle that
  can be served from the API as a JSON download.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# Canonical set of data categories. Keep in sync with docs/privacy.md when
# new categories are introduced -- the export schema depends on this list.
DATA_CATEGORIES: frozenset[str] = frozenset({
    "profile",              # user_profile fields (name, email, location, skills)
    "resume_content",       # generated resume text, uploaded resume bytes
    "cover_letter_content",
    "job_description",      # third-party job posting text
    "application_feedback", # employer-supplied status / feedback
    "analytics_metric",     # aggregated, non-identifying counts
    "auth_event",           # login / signup / session creation
})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def log_event(
    session: Session,
    *,
    user_id: str,
    action: str,
    tool_name: str = "",
    data_categories: Iterable[str] = (),
    purpose: str = "",
    llm_provider: str = "",
    llm_model: str = "",
    retention_days: int = 90,
    details: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Append a single row to the privacy ledger.

    Returns the inserted row id on success, ``None`` on any failure (DB
    errors, bad category, etc.). Callers **must not** depend on success --
    the ledger is advisory telemetry; failing it must never block the main
    agent work.
    """
    from src.models import PrivacyLedgerORM  # local import to avoid cycles

    categories = [c for c in data_categories if c in DATA_CATEGORIES]
    unknown = [c for c in data_categories if c not in DATA_CATEGORIES]
    if unknown:
        logger.warning("privacy_ledger: unknown data_categories %s", unknown)

    try:
        row = PrivacyLedgerORM(
            user_id=user_id,
            action=action,
            tool_name=tool_name,
            data_categories=categories,
            purpose=purpose,
            llm_provider=llm_provider,
            llm_model=llm_model,
            retention_days=retention_days,
            details=details or {},
            created_at=_utcnow(),
        )
        session.add(row)
        session.commit()
        return str(row.id)
    except Exception:
        logger.exception("privacy_ledger: failed to log event %s for user %s", action, user_id)
        try:
            session.rollback()
        except Exception:
            pass
        return None


def get_ledger(
    session: Session,
    user_id: str,
    *,
    since: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Return ledger rows for a user, newest first, as plain dicts.

    ``since`` filters by ``created_at >= since``. ``limit`` caps the row
    count. Neither parameter is required; omit both to get the full trail
    (use carefully for very active users).
    """
    from src.models import PrivacyLedgerORM

    q = session.query(PrivacyLedgerORM).filter_by(user_id=user_id)
    if since is not None:
        q = q.filter(PrivacyLedgerORM.created_at >= since)
    q = q.order_by(PrivacyLedgerORM.created_at.desc())
    if limit is not None:
        q = q.limit(limit)

    results: list[dict[str, Any]] = []
    for row in q.all():
        r: Any = row
        results.append({
            "id": str(r.id),
            "action": r.action,
            "tool_name": r.tool_name or "",
            "data_categories": list(r.data_categories or []),
            "purpose": r.purpose or "",
            "llm_provider": r.llm_provider or "",
            "llm_model": r.llm_model or "",
            "retention_days": r.retention_days or 0,
            "details": dict(r.details or {}),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return results


def export_for_user(
    session: Session,
    user_id: str,
    *,
    window_days: int = 365,
) -> dict[str, Any]:
    """Return an EU AI Act-aligned compliance export bundle.

    The bundle is designed to be served directly as a JSON download and
    contains the fields a user (or a supervisory authority) would need to
    understand how the system processed their data in the last
    ``window_days``.

    Layout:
      - ``generated_at``     — ISO timestamp of export
      - ``user_id``          — subject identifier
      - ``window_days``      — lookback window
      - ``system``           — provider/operator info (static)
      - ``risk_classification`` — our self-assessment under the EU AI Act
      - ``data_categories_processed`` — union of categories seen in the window
      - ``retention_summary``   — per-category max retention days observed
      - ``entries``             — the raw ledger rows in the window
      - ``counts``              — quick roll-ups (by action, by category)
    """
    since = _utcnow() - timedelta(days=window_days)
    entries = get_ledger(session, user_id, since=since)

    cats_seen: set[str] = set()
    retention_by_cat: dict[str, int] = {}
    counts_by_action: dict[str, int] = {}
    counts_by_category: dict[str, int] = {}

    for e in entries:
        action = e["action"]
        counts_by_action[action] = counts_by_action.get(action, 0) + 1
        for c in e["data_categories"]:
            cats_seen.add(c)
            counts_by_category[c] = counts_by_category.get(c, 0) + 1
            prev = retention_by_cat.get(c, 0)
            retention_by_cat[c] = max(prev, int(e.get("retention_days") or 0))

    return {
        "generated_at": _utcnow().isoformat(),
        "user_id": user_id,
        "window_days": window_days,
        "system": {
            "name": "AI Job Agent",
            "operator": "AVIEN SOLUTIONS INC",
            "purpose": "Assist a single user with job search, match scoring, "
                       "and document generation. No cross-user profiling or "
                       "automated hiring decisions are performed.",
            "data_storage": "Local SQLite or the user's configured database; "
                            "PII at rest is AES-256-GCM encrypted.",
        },
        "risk_classification": {
            "eu_ai_act_category": "limited_risk",
            "rationale": (
                "The system provides decision support to a single data "
                "subject (the job seeker); it does not make autonomous "
                "hiring decisions nor process data of third parties beyond "
                "public job postings. This places it outside the high-risk "
                "Annex III categories and in the 'limited risk + "
                "transparency obligations' tier."
            ),
            "human_oversight": (
                "Every outbound application, resume, or cover letter "
                "requires user approval in the UI before transmission. "
                "The agent never submits applications without explicit "
                "user action."
            ),
        },
        "data_categories_processed": sorted(cats_seen),
        "retention_summary_days": retention_by_cat,
        "counts": {
            "total_events": len(entries),
            "by_action": counts_by_action,
            "by_category": counts_by_category,
        },
        "entries": entries,
    }
