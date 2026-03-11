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
"""
"""
FastAPI layer for AI Job Agent.

Endpoints
─────────
POST /chat          — send a message; returns response + job_cache_size
DELETE /session     — clear conversation history for a session
GET  /health        — liveness probe

Sessions are stored in-memory (keyed by session_id UUID).  Each session holds
one JobAgent instance so conversation history and the job cache persist across
requests within the same session.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent import JobAgent
from src.models import ExperienceLevel, JobType, UserProfile

app = FastAPI(title="AI Job Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store ────────────────────────────────────────────────
_sessions: dict[str, JobAgent] = {}


# ── Request / Response models ──────────────────────────────────────────────

class ProfilePayload(BaseModel):
    name: str
    email: str
    location: str = "Remote"
    skills: list[str] = []
    desired_roles: list[str] = []
    experience_level: str = "mid"
    years_of_experience: int = 0
    languages: list[str] = ["English"]
    desired_job_types: list[str] = ["full_time"]
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    profile: Optional[ProfilePayload] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    job_cache_size: int


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_profile(payload: ProfilePayload) -> UserProfile:
    try:
        exp_level = ExperienceLevel(payload.experience_level.lower())
    except ValueError:
        exp_level = ExperienceLevel.MID

    job_types = []
    for t in payload.desired_job_types:
        try:
            job_types.append(JobType(t.lower()))
        except ValueError:
            pass
    if not job_types:
        job_types = [JobType.FULL_TIME]

    return UserProfile(
        name=payload.name,
        email=payload.email,
        location=payload.location,
        skills=payload.skills,
        desired_roles=payload.desired_roles,
        experience_level=exp_level,
        years_of_experience=payload.years_of_experience,
        languages=payload.languages,
        desired_job_types=job_types,
        desired_salary_min=payload.desired_salary_min,
        desired_salary_max=payload.desired_salary_max,
    )


def _get_or_create_agent(session_id: str | None, profile: ProfilePayload | None) -> tuple[str, JobAgent]:
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    if not profile:
        raise HTTPException(
            status_code=400,
            detail="A 'profile' is required when starting a new session.",
        )

    sid = session_id or str(uuid.uuid4())
    agent = JobAgent(_make_profile(profile))
    _sessions[sid] = agent
    return sid, agent


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "active_sessions": len(_sessions)}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    session_id, agent = _get_or_create_agent(req.session_id, req.profile)
    response = agent.chat(req.message)
    return {"response": response, "job_cache_size": len(agent._job_cache), "session_id": session_id}


@app.delete("/session/{session_id}")
def clear_session(session_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    _sessions[session_id].reset_conversation()
    return {"session_id": session_id, "status": "cleared"}
