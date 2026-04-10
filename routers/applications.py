"""Application tracking, analytics, and feedback endpoints."""


import asyncio
from typing import Any

from fastapi import APIRouter, Request, status
from slowapi import Limiter

from routers.schemas import (
    AgentResponse,
    TrackApplicationRequest,
    UpdateApplicationRequest,
)

router = APIRouter(prefix="/api", tags=["applications"])


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.post("/applications", status_code=status.HTTP_201_CREATED, response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def track_application(
        request: Request,
        body: TrackApplicationRequest,
        session_id: str = session_dep,
    ):
        """Log a new job application."""
        agent = get_agent_fn(session_id)
        job_info = ""
        if body.job_id in agent._job_cache:
            job = agent._job_cache[body.job_id]
            title = job.get("job_title", "")
            company = job.get("employer_name", "")
            job_info = f" ('{title}' at {company})"
        note_part = f" Notes: {body.notes}" if body.notes else ""
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Track my application for job ID {body.job_id}{job_info}.{note_part} "
                "Log it as 'applied' status.",
            )
        return AgentResponse(response=response)

    @router.put("/applications/{application_id}", response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def update_application(
        request: Request,
        application_id: str,
        body: UpdateApplicationRequest,
        session_id: str = session_dep,
    ):
        """Update the status or feedback for an application."""
        agent = get_agent_fn(session_id)
        parts = [f"Update application {application_id} status to {body.new_status.value}."]
        if body.feedback:
            parts.append(f"The employer said: {body.feedback}")
        if body.notes:
            parts.append(f"Additional notes: {body.notes}")
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(agent.chat, " ".join(parts))
        return AgentResponse(response=response)

    @router.get("/analytics", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def get_analytics(request: Request, session_id: str = session_dep):
        """Return application metrics and AI-generated career insights."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                "Show me my application analytics -- response rates, interview conversions, "
                "top performing roles, and actionable career insights based on my history.",
            )
        return AgentResponse(response=response)

    @router.get("/feedback", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def get_feedback_analysis(request: Request, session_id: str = session_dep):
        """Return AI analysis of employer feedback patterns."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                "Analyse the patterns in the employer feedback I have received. "
                "What recurring themes are there? What should I improve?",
            )
        return AgentResponse(response=response)
