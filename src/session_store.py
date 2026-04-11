"""In-memory session store for per-user JobAgent instances."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from fastapi import Depends, HTTPException, status

from src.auth import get_current_user_id

logger = logging.getLogger(__name__)

_sessions: dict[str, dict[str, Any]] = {}
_user_to_session: dict[str, str] = {}  # Firebase UID -> session_id
_sessions_lock = threading.Lock()
_MAX_SESSIONS = 500
_SESSION_TTL_SECONDS = 3600
_last_cleanup: float = 0.0
_CLEANUP_INTERVAL = 60


def get_sessions() -> dict[str, dict[str, Any]]:
    return _sessions


def close_session_agent(session_data: dict[str, Any]) -> None:
    agent = session_data.get("agent")
    if agent and hasattr(agent, "close"):
        try:
            agent.close()
        except Exception:
            logger.warning("Error closing agent session", exc_info=True)


def _cleanup_sessions_sync() -> None:
    global _last_cleanup
    now = time.monotonic()
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    agents_to_close: list[dict[str, Any]] = []
    with _sessions_lock:
        if now - _last_cleanup < _CLEANUP_INTERVAL:
            return
        _last_cleanup = now
        expired = [
            sid for sid, s in _sessions.items()
            if now - s.get("last_access", 0) > _SESSION_TTL_SECONDS
        ]
        if expired:
            logger.info("Evicting %d expired sessions", len(expired))
        for sid in expired:
            agents_to_close.append(_sessions[sid])
            del _sessions[sid]
            # Clean reverse mapping
            uids = [u for u, s in _user_to_session.items() if s == sid]
            for u in uids:
                del _user_to_session[u]
        evicted_cap = 0
        while len(_sessions) > _MAX_SESSIONS:
            oldest = min(_sessions, key=lambda k: _sessions[k].get("last_access", 0))
            agents_to_close.append(_sessions[oldest])
            del _sessions[oldest]
            evicted_cap += 1
        if evicted_cap:
            logger.info("Evicted %d sessions over cap (%d max)", evicted_cap, _MAX_SESSIONS)
    for session_data in agents_to_close:
        close_session_agent(session_data)


async def cleanup_sessions() -> None:
    await asyncio.to_thread(_cleanup_sessions_sync)


def touch_session(session_id: str) -> None:
    with _sessions_lock:
        if session_id in _sessions:
            _sessions[session_id]["last_access"] = time.monotonic()


def get_agent(session_id: str):  # type: ignore[no-untyped-def]
    """Return the JobAgent for a session, or raise 404."""
    from src.agent import JobAgent  # deferred to avoid circular import

    with _sessions_lock:
        sess = _sessions.get(session_id)
        if not sess or not sess.get("agent"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or profile not set up. POST /api/profile first.",
            )
        agent: JobAgent = sess["agent"]
    touch_session(session_id)
    return agent


def get_session_lock(session_id: str) -> asyncio.Lock:
    with _sessions_lock:
        sess = _sessions.get(session_id)
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        return sess["lock"]


def create_session(user_id: str | None = None) -> str:
    """Create a new empty session and return the session_id.

    When *user_id* is supplied (authenticated flow), the session is keyed
    by the user_id itself and a reverse mapping is stored so
    ``require_session`` can find it.  When omitted (legacy flow), a random
    UUID is used as before.
    """
    import uuid

    session_id = str(uuid.uuid4())
    with _sessions_lock:
        # If an authenticated user already has a session, return it
        if user_id and user_id in _user_to_session:
            existing = _user_to_session[user_id]
            if existing in _sessions:
                touch_session(existing)
                return existing
        _sessions[session_id] = {
            "agent": None, "profile": None,
            "last_access": time.monotonic(), "lock": asyncio.Lock(),
        }
        if user_id:
            _user_to_session[user_id] = session_id
    return session_id


def set_session_agent(session_id: str, agent: Any, profile: Any) -> None:
    """Replace the agent and profile for a session."""
    with _sessions_lock:
        old = _sessions.get(session_id)
        if old:
            close_session_agent(old)
        existing_lock = old["lock"] if old and "lock" in old else asyncio.Lock()
        _sessions[session_id] = {
            "agent": agent, "profile": profile,
            "last_access": time.monotonic(), "lock": existing_lock,
        }


def get_session_profile(session_id: str) -> Any:
    """Return the profile for a session, or raise 404."""
    with _sessions_lock:
        sess = _sessions.get(session_id)
        if not sess or not sess.get("profile"):
            raise HTTPException(status_code=404, detail="No profile found for this session.")
        return sess["profile"]


def close_all_sessions() -> None:
    """Close all sessions (for shutdown)."""
    with _sessions_lock:
        all_sessions = list(_sessions.values())
        _sessions.clear()
        _user_to_session.clear()
    for session_data in all_sessions:
        close_session_agent(session_data)
    logger.info("All sessions closed on shutdown.")


def delete_session(session_id: str) -> None:
    """Delete a session by ID (sign-out)."""
    with _sessions_lock:
        sess = _sessions.pop(session_id, None)
        # Also remove reverse mapping
        user_ids_to_remove = [
            uid for uid, sid in _user_to_session.items() if sid == session_id
        ]
        for uid in user_ids_to_remove:
            del _user_to_session[uid]
    if sess:
        close_session_agent(sess)


async def require_session(
    user_id: str = Depends(get_current_user_id),
) -> str:
    # Fast path: check for an existing session under the lock. Must release
    # the lock before calling ``create_session`` because that function
    # acquires ``_sessions_lock`` itself and ``threading.Lock`` is NOT
    # reentrant — holding it across the call would deadlock.
    with _sessions_lock:
        if user_id in _sessions:
            return user_id
        mapped = _user_to_session.get(user_id)
        if mapped and mapped in _sessions:
            return mapped

    # Slow path: auto-create a session for authenticated Bearer users.
    # Reading AUTH_ENABLED via a deferred import so tests that monkeypatch
    # ``config.settings.AUTH_ENABLED`` get the patched value on each call.
    from config.settings import AUTH_ENABLED
    if AUTH_ENABLED:
        return create_session(user_id=user_id)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found. POST /api/session first.",
    )


SessionId = Depends(require_session)
