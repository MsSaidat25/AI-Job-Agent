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
POST  /api/chat                   — free-form chat with agent
DELETE /api/chat/reset            — clear conversation history
GET   /api/health                 — liveness check
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()  # Must run before src.* imports which read env via config.settings

from fastapi import FastAPI, Header, HTTPException, status  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from src.agent import JobAgent  # noqa: E402
from src.job_search import search_jobs_live  # noqa: E402
from src.models import (  # noqa: E402
    ApplicationStatus,
    ExperienceLevel,
    JobType,
    UserProfile,
)


# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Job Agent API",
    description="REST interface for the AI-powered job application assistant.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend at /
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


# ── In-memory session store ──────────────────────────────────────────────────

# session_id → {"agent": JobAgent, "profile": UserProfile}
_sessions: dict[str, dict[str, Any]] = {}


def _get_agent(session_id: str) -> JobAgent:
    """Return the JobAgent for a session, or raise 404."""
    sess = _sessions.get(session_id)
    if not sess or not sess.get("agent"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or profile not set up. POST /api/profile first.",
        )
    return sess["agent"]


def _require_session_header(x_session_id: Optional[str]) -> str:
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Session-ID header is required.",
        )
    return x_session_id


# ── Request / Response schemas ───────────────────────────────────────────────

class ProfileRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    location: str
    skills: list[str] = []
    experience_level: ExperienceLevel = ExperienceLevel.MID
    years_of_experience: int = 0
    education: list[dict[str, Any]] = []
    work_history: list[dict[str, Any]] = []
    desired_roles: list[str] = []
    desired_job_types: list[JobType] = []
    preferred_currency: str = "USD"          # NEW — CAD / USD / GBP / EUR
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    languages: list[str] = ["English"]
    certifications: list[str] = []
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class JobSearchRequest(BaseModel):
    location_filter: str = ""
    include_remote: bool = True
    max_results: int = 10


class MarketInsightsRequest(BaseModel):
    region: str
    industry: str


class ApplicationTipsRequest(BaseModel):
    region: str


class ResumeRequest(BaseModel):
    job_id: str
    tone: str = "professional"


class CoverLetterRequest(BaseModel):
    job_id: str


class TrackApplicationRequest(BaseModel):
    job_id: str
    notes: str = ""


class UpdateApplicationRequest(BaseModel):
    new_status: ApplicationStatus
    feedback: Optional[str] = None
    notes: Optional[str] = None


class ChatRequest(BaseModel):
    message: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the HTML frontend."""
    return FileResponse("frontend/index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "sessions": len(_sessions)}


@app.post("/api/session", status_code=status.HTTP_201_CREATED)
async def create_session():
    """Create a new anonymous session. Returns a session_id to use in headers."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"agent": None, "profile": None}
    return {"session_id": session_id}


@app.post("/api/profile", status_code=status.HTTP_201_CREATED)
async def set_profile(
    body: ProfileRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Set or replace the user profile for a session. Initialises the JobAgent."""
    session_id = _require_session_header(x_session_id)

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
    )

    # Store preferred_currency directly on the profile object
    profile.preferred_currency = body.preferred_currency

    agent = JobAgent(profile=profile)
    _sessions[session_id] = {"agent": agent, "profile": profile}

    return {
        "profile_id": profile.id,
        "message": "Profile saved and agent initialised.",
        "currency": body.preferred_currency,
    }


@app.get("/api/profile")
async def get_profile(x_session_id: Optional[str] = Header(default=None)):
    """Return the profile associated with the session."""
    session_id = _require_session_header(x_session_id)
    sess = _sessions.get(session_id)
    if not sess or not sess.get("profile"):
        raise HTTPException(status_code=404, detail="No profile found for this session.")
    profile: UserProfile = sess["profile"]
    return profile.model_dump(mode="json")


@app.post("/api/jobs/search")
async def search_jobs(
    body: JobSearchRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """
    Search for REAL jobs using the JSearch API (pulls from Indeed, LinkedIn,
    Glassdoor, ZipRecruiter). Results are scored 0-100 against the user profile
    and cached in the session for use in Documents and Tracker.
    """
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)

    response_text, job_ids, raw_jobs = await search_jobs_live(
        profile=agent.profile,
        location_filter=body.location_filter,
        include_remote=body.include_remote,
        max_results=body.max_results,
    )

    # Cache raw jobs so Documents / Tracker can reference them by job_id
    if not hasattr(agent, "_job_cache"):
        agent._job_cache = {}
    for job_id, job in zip(job_ids, raw_jobs):
        agent._job_cache[job_id] = job

    return {
        "response": response_text,
        "job_ids": job_ids,
        "job_cache_size": len(agent._job_cache),
    }


@app.post("/api/market-insights")
async def market_insights(
    body: MarketInsightsRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Get a job-market report for a region and industry."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    response = agent.chat(
        f"Give me a detailed job market report for the {body.industry} industry in {body.region}. "
        "Include salary ranges, in-demand skills, top employers, and hiring trends."
    )
    return {"response": response}


@app.post("/api/application-tips")
async def application_tips(
    body: ApplicationTipsRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Get culturally-aware application tips for a region."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    response = agent.chat(
        f"What are the best job application tips for applying in {body.region}? "
        "Include cultural nuances, CV vs resume norms, interview etiquette, and local expectations."
    )
    return {"response": response}


@app.post("/api/documents/resume")
async def generate_resume(
    body: ResumeRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Generate a tailored resume for a job in the current session cache."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)

    if not hasattr(agent, "_job_cache") or body.job_id not in agent._job_cache:
        raise HTTPException(
            status_code=400,
            detail="Job ID not found in session cache. Run a job search first, then copy a Job ID.",
        )

    job = agent._job_cache[body.job_id]
    job_title = job.get("job_title", "the role")
    company = job.get("employer_name", "the company")
    description = (job.get("job_description") or "")[:1500]

    response = agent.chat(
        f"Generate a {body.tone} resume tailored for the '{job_title}' role at {company}. "
        f"Here is the job description:\n\n{description}\n\n"
        "Tailor my skills, experience, and achievements to match this specific role."
    )
    return {"response": response}


@app.post("/api/documents/cover-letter")
async def generate_cover_letter(
    body: CoverLetterRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Generate a tailored cover letter for a job in the current session cache."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)

    if not hasattr(agent, "_job_cache") or body.job_id not in agent._job_cache:
        raise HTTPException(
            status_code=400,
            detail="Job ID not found in session cache. Run a job search first, then copy a Job ID.",
        )

    job = agent._job_cache[body.job_id]
    job_title = job.get("job_title", "the role")
    company = job.get("employer_name", "the company")
    description = (job.get("job_description") or "")[:1500]
    apply_link = job.get("job_apply_link", "")

    response = agent.chat(
        f"Generate a compelling cover letter for the '{job_title}' position at {company}. "
        f"Job description:\n\n{description}\n\n"
        "Make it personal, confident, and specific to this role and company."
        + (f"\nApplication link for reference: {apply_link}" if apply_link else "")
    )
    return {"response": response}


@app.post("/api/applications", status_code=status.HTTP_201_CREATED)
async def track_application(
    body: TrackApplicationRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Log a new job application."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)

    # Enrich with real job data if available
    job_info = ""
    if hasattr(agent, "_job_cache") and body.job_id in agent._job_cache:
        job = agent._job_cache[body.job_id]
        title = job.get("job_title", "")
        company = job.get("employer_name", "")
        job_info = f" ('{title}' at {company})"

    note_part = f" Notes: {body.notes}" if body.notes else ""
    response = agent.chat(
        f"Track my application for job ID {body.job_id}{job_info}.{note_part} "
        "Log it as 'applied' status."
    )
    return {"response": response}


@app.put("/api/applications/{application_id}")
async def update_application(
    application_id: str,
    body: UpdateApplicationRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Update the status or feedback for an application."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)

    parts = [f"Update application {application_id} status to {body.new_status.value}."]
    if body.feedback:
        parts.append(f"The employer said: {body.feedback}")
    if body.notes:
        parts.append(f"Additional notes: {body.notes}")

    response = agent.chat(" ".join(parts))
    return {"response": response}


@app.get("/api/analytics")
async def get_analytics(x_session_id: Optional[str] = Header(default=None)):
    """Return application metrics and AI-generated career insights."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    response = agent.chat(
        "Show me my application analytics — response rates, interview conversions, "
        "top performing roles, and actionable career insights based on my history."
    )
    return {"response": response}


@app.get("/api/feedback")
async def get_feedback_analysis(x_session_id: Optional[str] = Header(default=None)):
    """Return AI analysis of employer feedback patterns."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    response = agent.chat(
        "Analyse the patterns in the employer feedback I have received. "
        "What recurring themes are there? What should I improve?"
    )
    return {"response": response}


@app.post("/api/chat")
async def chat(
    body: ChatRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Free-form conversation with the job agent."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    response = agent.chat(body.message)
    return {"response": response}


@app.delete("/api/chat/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_chat(x_session_id: Optional[str] = Header(default=None)):
    """Clear conversation history for the session (profile and job cache persist)."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    agent.reset_conversation()


# ── Dev entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
