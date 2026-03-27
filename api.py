# Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com). All Rights Reserved.
# avien@aviensolutions.com
"""
AI Job Agent — FastAPI REST Server.

Exposes the JobAgent's functionality as REST endpoints so that the
HTML frontend (frontend/index.html) can interact with it over HTTP.

Session design
──────────────
Each browser session gets a unique session_id (UUID).  The frontend
stores this in localStorage and sends it as the `X-Session-ID` header.
The server keeps a per-session JobAgent instance (with its job cache and
conversation history) in the `_sessions` dict.

Endpoints
─────────
POST  /api/session                — create a new session (returns session_id)
POST  /api/profile                — set/update user profile for a session
GET   /api/profile                — retrieve profile for a session
POST  /api/jobs/search            — search real jobs via JSearch API
POST  /api/market-insights        — get regional market report
POST  /api/application-tips       — get culturally-aware tips
POST  /api/documents/resume       — generate tailored resume
POST  /api/documents/cover-letter — generate cover letter
POST  /api/applications           — track a new application
PUT   /api/applications/{id}      — update an existing application
GET   /api/analytics              — compute metrics + AI insights
GET   /api/feedback               — employer feedback analysis
GET   /api/dashboard/summary      — structured metrics for dashboard
GET   /api/dashboard/applications — application list with job details
GET   /api/dashboard/activity     — recent activity timeline
GET   /api/dashboard/skills       — skill gap analysis vs job postings
POST  /api/chat                   — free-form chat with agent
DELETE /api/chat/reset            — clear conversation history
GET   /api/health                 — liveness check
"""

from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
import json as _json
import logging
import os
import threading
import time
import uuid
from typing import Any, Optional, cast

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()  # Must run before src.* imports which read env via config.settings

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, status  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sqlalchemy import text as sa_text  # noqa: E402
from pydantic import BaseModel, EmailStr, Field, field_validator  # noqa: E402
from slowapi import Limiter  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

from config.settings import (  # noqa: E402
    AGENT_MODEL,
    AUTH_ENABLED,
    LLM_API_KEY,
    USE_VERTEX_PRIMARY,
    VERTEX_PROJECT,
)
from src.auth import get_current_user_id  # noqa: E402
from src.llm_client import create_message_with_failover, get_llm_client  # noqa: E402
from src.agent import JobAgent  # noqa: E402
from src.job_search import search_jobs_live  # noqa: E402
from src.models import (  # noqa: E402
    ApplicationStatus,
    ExperienceLevel,
    JobType,
    UserProfile,
)
from src.utils import strip_json_fences  # noqa: E402


# ── App setup ────────────────────────────────────────────────────────────────

_TRUST_PROXY: bool = os.environ.get("TRUST_PROXY", "false").lower() == "true"


def _get_real_client_ip(request: Request) -> str:
    """Extract client IP for rate limiting.

    Only trusts X-Forwarded-For when TRUST_PROXY=true (i.e., behind a
    known reverse proxy like Cloud Run or nginx that strips/overwrites
    the header).
    """
    if _TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_get_real_client_ip)

# Disable OpenAPI/docs in production (when auth is enabled)
_docs_url: str | None = "/docs" if not AUTH_ENABLED else None
_redoc_url: str | None = "/redoc" if not AUTH_ENABLED else None


@asynccontextmanager
async def _lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    yield
    # Shutdown: collect all sessions under lock, close outside lock
    with _sessions_lock:
        all_sessions = list(_sessions.values())
        _sessions.clear()
    for session_data in all_sessions:
        _close_session_agent(session_data)
    logger.info("All sessions closed on shutdown.")


app = FastAPI(
    title="AI Job Agent API",
    description="REST interface for the AI-powered job application assistant.",
    version="2.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=_lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
_ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in _raw_origins.split(",")
    if o.strip()
] if _raw_origins else ["http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-ID"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    await _cleanup_sessions()
    # Attach a correlation ID for request tracing
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    logger.info("%s %s [rid=%s]", request.method, request.url.path, request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'"
    # HSTS: only trust X-Forwarded-Proto behind a known proxy
    scheme = request.url.scheme
    if _TRUST_PROXY:
        scheme = request.headers.get("X-Forwarded-Proto", scheme)
    if scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Serve frontend at /
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


# ── In-memory session store ──────────────────────────────────────────────────

# session_id → {"agent": JobAgent, "profile": UserProfile, "last_access": float, "lock": asyncio.Lock}
_sessions: dict[str, dict[str, Any]] = {}
_sessions_lock = threading.Lock()
_MAX_SESSIONS = 500
_SESSION_TTL_SECONDS = 3600  # 1 hour
_last_cleanup: float = 0.0
_CLEANUP_INTERVAL = 60  # Run cleanup at most once per 60 seconds


def _close_session_agent(session_data: dict[str, Any]) -> None:
    """Close the DB session held by a JobAgent to prevent connection leaks."""
    agent = session_data.get("agent")
    if agent and hasattr(agent, "close"):
        try:
            agent.close()
        except Exception:
            logger.warning("Error closing agent session", exc_info=True)


def _cleanup_sessions_sync() -> None:
    """Evict expired sessions and enforce max cap (sync, for use in threads).

    Throttled to run at most once per minute.
    """
    global _last_cleanup
    now = time.monotonic()
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    agents_to_close: list[dict[str, Any]] = []
    with _sessions_lock:
        # Double-check inside lock to prevent concurrent cleanups
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
        # If still over cap, evict oldest
        evicted_cap = 0
        while len(_sessions) > _MAX_SESSIONS:
            oldest = min(_sessions, key=lambda k: _sessions[k].get("last_access", 0))
            agents_to_close.append(_sessions[oldest])
            del _sessions[oldest]
            evicted_cap += 1
        if evicted_cap:
            logger.info("Evicted %d sessions over cap (%d max)", evicted_cap, _MAX_SESSIONS)
    # Close DB sessions outside the lock to avoid blocking
    for session_data in agents_to_close:
        _close_session_agent(session_data)


async def _cleanup_sessions() -> None:
    """Run session cleanup off the event loop to avoid blocking."""
    await asyncio.to_thread(_cleanup_sessions_sync)


def _touch_session(session_id: str) -> None:
    """Update last access time for a session."""
    with _sessions_lock:
        if session_id in _sessions:
            _sessions[session_id]["last_access"] = time.monotonic()


def _get_agent(session_id: str) -> JobAgent:
    """Return the JobAgent for a session, or raise 404."""
    with _sessions_lock:
        sess = _sessions.get(session_id)
        if not sess or not sess.get("agent"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or profile not set up. POST /api/profile first.",
            )
        agent = sess["agent"]
    _touch_session(session_id)
    return agent


def _get_session_lock(session_id: str) -> asyncio.Lock:
    """Return the per-session asyncio.Lock, or raise 404 if session missing."""
    with _sessions_lock:
        sess = _sessions.get(session_id)
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        return sess["lock"]


async def _require_session(
    user_id: str = Depends(get_current_user_id),
) -> str:
    """Validate identity (Bearer token or X-Session-ID) and ensure session exists."""
    with _sessions_lock:
        if user_id not in _sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found. POST /api/session first.",
            )
    return user_id


# Type alias for Depends injection used in endpoint signatures
_SessionId = Depends(_require_session)


# ── Request / Response schemas ───────────────────────────────────────────────

class ProfileRequest(BaseModel):
    name: str = Field(..., max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    location: str = Field(..., max_length=200)
    skills: list[str] = Field(default_factory=list, max_length=100)
    experience_level: ExperienceLevel = ExperienceLevel.MID
    years_of_experience: int = Field(default=0, ge=0, le=70)
    education: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    work_history: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    desired_roles: list[str] = Field(default_factory=list, max_length=20)
    desired_job_types: list[JobType] = Field(default_factory=list, max_length=10)
    preferred_currency: str = Field(default="USD", max_length=5)
    desired_salary_min: Optional[int] = Field(default=None, ge=0)
    desired_salary_max: Optional[int] = Field(default=None, ge=0)
    languages: list[str] = Field(default=["English"], max_length=30)
    certifications: list[str] = Field(default_factory=list, max_length=50)
    portfolio_url: Optional[str] = Field(default=None, max_length=500)
    linkedin_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("portfolio_url", "linkedin_url", mode="before")
    @classmethod
    def validate_urls(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith(("https://", "http://")):
            raise ValueError("URL must start with https:// or http://")
        return v


class JobSearchRequest(BaseModel):
    location_filter: str = Field(default="", max_length=200)
    include_remote: bool = True
    max_results: int = Field(default=10, ge=1, le=50)


class MarketInsightsRequest(BaseModel):
    region: str = Field(..., max_length=200)
    industry: str = Field(..., max_length=200)


class ApplicationTipsRequest(BaseModel):
    region: str = Field(..., max_length=200)


_ALLOWED_TONES = {"professional", "creative", "technical", "executive", "academic"}


class ResumeRequest(BaseModel):
    job_id: str = Field(..., max_length=200)
    tone: str = "professional"

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        if v.lower() not in _ALLOWED_TONES:
            raise ValueError(f"tone must be one of: {', '.join(sorted(_ALLOWED_TONES))}")
        return v.lower()


class CoverLetterRequest(BaseModel):
    job_id: str = Field(..., max_length=200)


class TrackApplicationRequest(BaseModel):
    job_id: str = Field(..., max_length=200)
    notes: str = Field(default="", max_length=2000)


class UpdateApplicationRequest(BaseModel):
    new_status: ApplicationStatus
    feedback: Optional[str] = Field(default=None, max_length=5000)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=5000)


# ── Response schemas ─────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    sessions: int
    db: str
    llm_configured: bool


class SessionResponse(BaseModel):
    session_id: str


class ProfileResponse(BaseModel):
    profile_id: str
    message: str
    currency: str


class JobSearchResponse(BaseModel):
    response: str
    job_ids: list[str]
    job_cache_size: int


class AgentResponse(BaseModel):
    response: str


# ── Dashboard router ──────────────────────────────────────────────────────────
# Dashboard response schemas and endpoints live in routers/dashboard.py
from routers.dashboard import router as dashboard_router, _setup_routes as _setup_dashboard  # noqa: E402


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the HTML frontend."""
    return FileResponse("frontend/index.html")


@app.get("/api/health", response_model=HealthResponse)
async def health():
    # Check DB connectivity using the cached engine
    db_status = "ok"
    try:
        from src.models import get_active_engine
        engine = get_active_engine()
        if engine is None:
            # Cold start: proactively initialise the engine so health checks pass
            from src.models import get_engine
            engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
    except Exception:
        db_status = "error"

    resp = HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        sessions=len(_sessions),
        db=db_status,
        llm_configured=bool(LLM_API_KEY) or (USE_VERTEX_PRIMARY and bool(VERTEX_PROJECT)),
    )
    if db_status != "ok":
        return JSONResponse(status_code=503, content=resp.model_dump())
    return resp


@app.post("/api/session", status_code=status.HTTP_201_CREATED, response_model=SessionResponse)
@limiter.limit("30/hour")
async def create_session(request: Request):
    """Create a new anonymous session. Returns a session_id to use in headers."""
    await _cleanup_sessions()
    session_id = str(uuid.uuid4())
    with _sessions_lock:
        _sessions[session_id] = {
            "agent": None, "profile": None,
            "last_access": time.monotonic(), "lock": asyncio.Lock(),
        }
    return SessionResponse(session_id=session_id)


@app.post("/api/profile", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
@limiter.limit("10/minute")
async def set_profile(
    request: Request,
    body: ProfileRequest,
    session_id: str = _SessionId,
):
    """Set or replace the user profile for a session. Initialises the JobAgent."""

    profile = UserProfile(
        name=body.name,
        email=body.email,
        phone=body.phone,
        location=body.location,
        skills=body.skills,
        experience_level=body.experience_level,
        years_of_experience=body.years_of_experience,
        education=body.education,
        work_history=body.work_history,
        desired_roles=body.desired_roles,
        desired_job_types=body.desired_job_types,
        desired_salary_min=body.desired_salary_min,
        desired_salary_max=body.desired_salary_max,
        languages=body.languages,
        certifications=body.certifications,
        portfolio_url=body.portfolio_url,
        linkedin_url=body.linkedin_url,
        preferred_currency=body.preferred_currency,
    )

    # Close previous agent's DB session if replacing
    with _sessions_lock:
        old = _sessions.get(session_id)
        if old:
            _close_session_agent(old)
        agent = JobAgent(profile=profile)
        # Preserve existing asyncio.Lock or create a new one
        existing_lock = old["lock"] if old and "lock" in old else asyncio.Lock()
        _sessions[session_id] = {
            "agent": agent, "profile": profile,
            "last_access": time.monotonic(), "lock": existing_lock,
        }

    return ProfileResponse(
        profile_id=profile.id,
        message="Profile saved and agent initialised.",
        currency=body.preferred_currency,
    )


@app.get("/api/profile", response_model=ProfileRequest)
@limiter.limit("30/minute")
async def get_profile(request: Request, session_id: str = _SessionId):
    """Return the profile associated with the session."""
    with _sessions_lock:
        sess = _sessions.get(session_id)
        if not sess or not sess.get("profile"):
            raise HTTPException(status_code=404, detail="No profile found for this session.")
        profile: UserProfile = sess["profile"]
    return profile.model_dump(mode="json")


@app.post("/api/jobs/search", response_model=JobSearchResponse)
@limiter.limit("10/minute")
async def search_jobs(
    request: Request,
    body: JobSearchRequest,
    session_id: str = _SessionId,
):
    """
    Search for REAL jobs using the JSearch API (pulls from Indeed, LinkedIn,
    Glassdoor, ZipRecruiter). Results are scored 0-100 against the user profile
    and cached in the session for use in Documents and Tracker.
    """
    agent = _get_agent(session_id)

    response_text, job_ids, raw_jobs = await search_jobs_live(
        profile=agent.profile,
        location_filter=body.location_filter,
        include_remote=body.include_remote,
        max_results=body.max_results,
    )

    # Cache raw jobs so Documents / Tracker can reference them by job_id
    for job_id, job in zip(job_ids, raw_jobs):
        if len(agent._job_cache) >= agent._job_cache_max:
            oldest_key = next(iter(agent._job_cache))
            del agent._job_cache[oldest_key]
        agent._job_cache[job_id] = job

    return JobSearchResponse(
        response=response_text,
        job_ids=job_ids,
        job_cache_size=len(agent._job_cache),
    )


@app.post("/api/market-insights", response_model=AgentResponse)
@limiter.limit("10/minute")
async def market_insights(
    request: Request,
    body: MarketInsightsRequest,
    session_id: str = _SessionId,
):
    """Get a job-market report for a region and industry."""
    agent = _get_agent(session_id)
    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat,
            f"Give me a detailed job market report for the {body.industry} industry in {body.region}. "
            "Include salary ranges, in-demand skills, top employers, and hiring trends."
        )
    return AgentResponse(response=response)


@app.post("/api/application-tips", response_model=AgentResponse)
@limiter.limit("10/minute")
async def application_tips(
    request: Request,
    body: ApplicationTipsRequest,
    session_id: str = _SessionId,
):
    """Get culturally-aware application tips for a region."""
    agent = _get_agent(session_id)
    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat,
            f"What are the best job application tips for applying in {body.region}? "
            "Include cultural nuances, CV vs resume norms, interview etiquette, and local expectations."
        )
    return AgentResponse(response=response)


@app.post("/api/documents/resume", response_model=AgentResponse)
@limiter.limit("5/minute")
async def generate_resume(
    request: Request,
    body: ResumeRequest,
    session_id: str = _SessionId,
):
    """Generate a tailored resume for a job in the current session cache."""
    agent = _get_agent(session_id)

    if body.job_id not in agent._job_cache:
        raise HTTPException(
            status_code=400,
            detail="Job ID not found in session cache. Run a job search first, then copy a Job ID.",
        )

    job = agent._job_cache[body.job_id]
    job_title = job.get("job_title", "the role")
    company = job.get("employer_name", "the company")
    description = (job.get("job_description") or "")[:1500]

    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat,
            f"Generate a {body.tone} resume tailored for the '{job_title}' role at {company}. "
            f"Here is the job description:\n\n{description}\n\n"
            "Tailor my skills, experience, and achievements to match this specific role."
        )
    return AgentResponse(response=response)


@app.post("/api/documents/cover-letter", response_model=AgentResponse)
@limiter.limit("5/minute")
async def generate_cover_letter(
    request: Request,
    body: CoverLetterRequest,
    session_id: str = _SessionId,
):
    """Generate a tailored cover letter for a job in the current session cache."""
    agent = _get_agent(session_id)

    if body.job_id not in agent._job_cache:
        raise HTTPException(
            status_code=400,
            detail="Job ID not found in session cache. Run a job search first, then copy a Job ID.",
        )

    job = agent._job_cache[body.job_id]
    job_title = job.get("job_title", "the role")
    company = job.get("employer_name", "the company")
    description = (job.get("job_description") or "")[:1500]
    apply_link = job.get("job_apply_link", "")

    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat,
            f"Generate a compelling cover letter for the '{job_title}' position at {company}. "
            f"Job description:\n\n{description}\n\n"
            "Make it personal, confident, and specific to this role and company."
            + (f"\nApplication link for reference: {apply_link}" if apply_link else "")
        )
    return AgentResponse(response=response)


@app.post("/api/applications", status_code=status.HTTP_201_CREATED, response_model=AgentResponse)
@limiter.limit("10/minute")
async def track_application(
    request: Request,
    body: TrackApplicationRequest,
    session_id: str = _SessionId,
):
    """Log a new job application."""
    agent = _get_agent(session_id)

    # Enrich with real job data if available
    job_info = ""
    if body.job_id in agent._job_cache:
        job = agent._job_cache[body.job_id]
        title = job.get("job_title", "")
        company = job.get("employer_name", "")
        job_info = f" ('{title}' at {company})"

    note_part = f" Notes: {body.notes}" if body.notes else ""
    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat,
            f"Track my application for job ID {body.job_id}{job_info}.{note_part} "
            "Log it as 'applied' status."
        )
    return AgentResponse(response=response)


@app.put("/api/applications/{application_id}", response_model=AgentResponse)
@limiter.limit("10/minute")
async def update_application(
    request: Request,
    application_id: str,
    body: UpdateApplicationRequest,
    session_id: str = _SessionId,
):
    """Update the status or feedback for an application."""
    agent = _get_agent(session_id)

    parts = [f"Update application {application_id} status to {body.new_status.value}."]
    if body.feedback:
        parts.append(f"The employer said: {body.feedback}")
    if body.notes:
        parts.append(f"Additional notes: {body.notes}")

    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat, " ".join(parts))
    return AgentResponse(response=response)


@app.get("/api/analytics", response_model=AgentResponse)
@limiter.limit("5/minute")
async def get_analytics(request: Request, session_id: str = _SessionId):
    """Return application metrics and AI-generated career insights."""
    agent = _get_agent(session_id)
    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat,
            "Show me my application analytics — response rates, interview conversions, "
            "top performing roles, and actionable career insights based on my history."
        )
    return AgentResponse(response=response)


@app.get("/api/feedback", response_model=AgentResponse)
@limiter.limit("5/minute")
async def get_feedback_analysis(request: Request, session_id: str = _SessionId):
    """Return AI analysis of employer feedback patterns."""
    agent = _get_agent(session_id)
    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat,
            "Analyse the patterns in the employer feedback I have received. "
            "What recurring themes are there? What should I improve?"
        )
    return AgentResponse(response=response)


# ── Dashboard router (wired below) ────────────────────────────────────────────
_setup_dashboard(limiter=limiter, get_agent_fn=_get_agent, session_dep=_SessionId)
app.include_router(dashboard_router)


@app.post("/api/chat", response_model=AgentResponse)
@limiter.limit("15/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    session_id: str = _SessionId,
):
    """Free-form conversation with the job agent."""
    agent = _get_agent(session_id)
    async with _get_session_lock(session_id):
        response = await asyncio.to_thread(agent.chat, body.message)
    return AgentResponse(response=response)


@app.delete("/api/chat/reset", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def reset_chat(request: Request, session_id: str = _SessionId):
    """Clear conversation history for the session (profile and job cache persist)."""
    agent = _get_agent(session_id)
    agent.reset_conversation()


# ── Resume parse proxy (keeps API key server-side) ───────────────────────────

class ResumeParseResponse(BaseModel):
    name: str = ""
    email: str = ""
    phone: Optional[str] = None
    location: str = ""
    experience_level: str = "mid"
    years_of_experience: int = 0
    skills: list[str] = Field(default_factory=list)
    desired_roles: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None


_RESUME_PARSE_PROMPT = (
    "Extract information from this resume. Return ONLY valid JSON, no markdown "
    'fences, no explanation:\n{"name":"","email":"","phone":"","location":"",'
    '"experience_level":"entry|mid|senior|lead|executive",'
    '"years_of_experience":0,"skills":[],"desired_roles":[],'
    '"certifications":[],"languages":[],"linkedin_url":"","portfolio_url":""}'
)


@app.post("/api/parse-resume", response_model=ResumeParseResponse)
@limiter.limit("5/minute")
async def parse_resume(
    request: Request,
    file: UploadFile,
    session_id: str = _SessionId,
):
    """Parse a resume file (PDF or text) via Claude and return structured JSON."""
    _ALLOWED_MIME = {"application/pdf", "text/plain", "text/csv", "text/markdown"}
    if not file.content_type:
        raise HTTPException(status_code=400, detail="File type not detected.")
    if file.content_type not in _ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(_ALLOWED_MIME)}")

    # Read in chunks to reject oversized files early
    _MAX_UPLOAD = 5_000_000
    chunks = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > _MAX_UPLOAD:
            raise HTTPException(status_code=400, detail="File too large (max 5 MB).")
        chunks.append(chunk)
    raw = b"".join(chunks)

    client = get_llm_client()

    if file.content_type == "application/pdf":
        b64 = base64.b64encode(raw).decode()
        messages = [{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                {"type": "text", "text": _RESUME_PARSE_PROMPT},
            ],
        }]
    else:
        text = raw.decode("utf-8", errors="replace")[:4000]
        messages = [{
            "role": "user",
            "content": _RESUME_PARSE_PROMPT + "\n\nResume:\n" + text,
        }]

    resp = create_message_with_failover(
        client,
        model=AGENT_MODEL,
        max_tokens=1000,
        messages=cast(Any, messages),
    )
    result_text = next((b.text for b in resp.content if b.type == "text"), "")
    if not result_text:
        raise HTTPException(status_code=502, detail="AI returned no text response.")
    clean = strip_json_fences(result_text)
    try:
        parsed = _json.loads(clean)
    except _json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Failed to parse AI response.") from exc
    try:
        return ResumeParseResponse(**parsed)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI response did not match expected resume schema.") from exc


# ── Dev entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
