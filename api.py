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
POST  /api/session            — create a new session (returns session_id)
POST  /api/profile            — set/update user profile for a session
GET   /api/profile            — retrieve profile for a session
POST  /api/jobs/search        — search jobs
POST  /api/market-insights    — get regional market report
POST  /api/application-tips   — get culturally-aware tips
POST  /api/documents/resume   — generate tailored resume
POST  /api/documents/cover-letter — generate cover letter
POST  /api/applications       — track a new application
PUT   /api/applications/{id}  — update an existing application
GET   /api/analytics          — compute metrics + AI insights
GET   /api/feedback           — employer feedback analysis
POST  /api/chat               — free-form chat with agent
DELETE /api/chat/reset        — clear conversation history
GET   /api/health             — liveness check
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent import JobAgent
from src.models import (
    ApplicationStatus,
    ExperienceLevel,
    JobType,
    UserProfile,
)


# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Job Agent API",
    description="REST interface for the AI-powered job application assistant.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the frontend directory so index.html is served at /
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


# ── In-memory session store ──────────────────────────────────────────────────

# session_id → {"agent": JobAgent, "profile": UserProfile}
_sessions: dict[str, dict[str, Any]] = {}


def _get_agent(session_id: str) -> JobAgent:
    """Return the JobAgent for a session, or raise 404."""
    sess = _sessions.get(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found. POST /api/profile first.",
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

class EducationEntry(BaseModel):
    degree: str = ""
    institution: str = ""
    year: Optional[int] = None
    field: str = ""


class WorkEntry(BaseModel):
    title: str = ""
    company: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    description: str = ""


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
    """Create a new anonymous session.  Returns a session_id to use in headers."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"agent": None, "profile": None}
    return {"session_id": session_id}


@app.post("/api/profile", status_code=status.HTTP_201_CREATED)
async def set_profile(
    body: ProfileRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Set or replace the user profile for a session.  Initialises the JobAgent."""
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

    agent = JobAgent(profile=profile)
    _sessions[session_id] = {"agent": agent, "profile": profile}

    return {"profile_id": profile.id, "message": "Profile saved and agent initialised."}


@app.get("/api/profile")
async def get_profile(x_session_id: Optional[str] = Header(default=None)):
    """Return the profile associated with the session."""
    session_id = _require_session_header(x_session_id)
    sess = _sessions.get(session_id)
    if not sess or not sess.get("profile"):
        raise HTTPException(status_code=404, detail="No profile found for this session.")
    profile: UserProfile = sess["profile"]
    # Return safe subset (omit encrypted PII fields from wire if desired)
    return profile.model_dump(mode="json")


@app.post("/api/jobs/search")
async def search_jobs(
    body: JobSearchRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Search for jobs matching the user profile."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)

    # Call through agent chat so the agentic loop runs and caches jobs
    query_parts = ["Search for jobs"]
    if body.location_filter:
        query_parts.append(f"in {body.location_filter}")
    if body.include_remote:
        query_parts.append("including remote opportunities")
    query_parts.append(f"and show me up to {body.max_results} results")

    response = agent.chat(" ".join(query_parts))
    return {"response": response, "job_cache_size": len(agent._job_cache)}


@app.post("/api/market-insights")
async def market_insights(
    body: MarketInsightsRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """Get a job-market report for a region and industry."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    response = agent.chat(
        f"Give me a detailed job market report for the {body.industry} industry in {body.region}."
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
        "Include cultural nuances and local norms."
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

    if body.job_id not in agent._job_cache:
        raise HTTPException(
            status_code=400,
            detail="Job ID not found in session cache. Run a job search first.",
        )

    response = agent.chat(
        f"Generate a {body.tone} resume tailored for job ID {body.job_id}."
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

    if body.job_id not in agent._job_cache:
        raise HTTPException(
            status_code=400,
            detail="Job ID not found in session cache. Run a job search first.",
        )

    response = agent.chat(
        f"Generate a compelling cover letter for job ID {body.job_id}."
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

    note_part = f" Notes: {body.notes}" if body.notes else ""
    response = agent.chat(
        f"Track my application for job ID {body.job_id}.{note_part}"
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
        "Show me my application analytics, success metrics, and career insights."
    )
    return {"response": response}


@app.get("/api/feedback")
async def get_feedback_analysis(x_session_id: Optional[str] = Header(default=None)):
    """Return AI analysis of employer feedback patterns."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    response = agent.chat(
        "Analyse the patterns in the employer feedback I have received so far."
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
    """Clear the conversation history for the session (profile and job cache persist)."""
    session_id = _require_session_header(x_session_id)
    agent = _get_agent(session_id)
    agent.reset_conversation()


# ── Dev entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
