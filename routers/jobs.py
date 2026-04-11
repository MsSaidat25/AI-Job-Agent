"""Job search, market insights, and document generation endpoints."""


import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter

from routers.schemas import (
    AgentResponse,
    ApplicationTipsRequest,
    CoverLetterRequest,
    JobSearchRequest,
    JobSearchResponse,
    MarketInsightsRequest,
    ResumeRequest,
)
from src.job_search import search_jobs_live

router = APIRouter(prefix="/api", tags=["jobs"])


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.post("/jobs/search", response_model=JobSearchResponse)
    @limiter.limit("10/minute")
    async def search_jobs(
        request: Request,
        body: JobSearchRequest,
        session_id: str = session_dep,
    ):
        """Search real jobs via JSearch API, scored against user profile."""
        agent = get_agent_fn(session_id)
        response_text, job_ids, raw_jobs = await search_jobs_live(
            profile=agent.profile,
            location_filter=body.location_filter,
            include_remote=body.include_remote,
            max_results=body.max_results,
        )
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

    @router.post("/market-insights", response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def market_insights(
        request: Request,
        body: MarketInsightsRequest,
        session_id: str = session_dep,
    ):
        """Get a job-market report for a region and industry."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Give me a detailed job market report for the {body.industry} industry in {body.region}. "
                "Include salary ranges, in-demand skills, top employers, and hiring trends.",
            )
        return AgentResponse(response=response)

    @router.post("/application-tips", response_model=AgentResponse)
    @limiter.limit("10/minute")
    async def application_tips(
        request: Request,
        body: ApplicationTipsRequest,
        session_id: str = session_dep,
    ):
        """Get culturally-aware application tips for a region."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"What are the best job application tips for applying in {body.region}? "
                "Include cultural nuances, CV vs resume norms, interview etiquette, and local expectations.",
            )
        return AgentResponse(response=response)

    @router.post("/documents/resume", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def generate_resume(
        request: Request,
        body: ResumeRequest,
        session_id: str = session_dep,
    ):
        """Generate a tailored resume for a cached job."""
        agent = get_agent_fn(session_id)
        if body.job_id not in agent._job_cache:
            raise HTTPException(status_code=400, detail="Job ID not found in session cache.")
        job = agent._job_cache[body.job_id]
        job_title = job.get("job_title", "the role")
        company = job.get("employer_name", "the company")
        description = (job.get("job_description") or "")[:1500]
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Generate a {body.tone} resume tailored for the '{job_title}' role at {company}. "
                f"Here is the job description:\n\n{description}\n\n"
                "Tailor my skills, experience, and achievements to match this specific role.",
            )
        return AgentResponse(response=response)

    @router.post("/documents/cover-letter", response_model=AgentResponse)
    @limiter.limit("5/minute")
    async def generate_cover_letter(
        request: Request,
        body: CoverLetterRequest,
        session_id: str = session_dep,
    ):
        """Generate a tailored cover letter for a cached job."""
        agent = get_agent_fn(session_id)
        if body.job_id not in agent._job_cache:
            raise HTTPException(status_code=400, detail="Job ID not found in session cache.")
        job = agent._job_cache[body.job_id]
        job_title = job.get("job_title", "the role")
        company = job.get("employer_name", "the company")
        description = (job.get("job_description") or "")[:1500]
        apply_link = job.get("job_apply_link", "")
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Generate a compelling cover letter for the '{job_title}' position at {company}. "
                f"Job description:\n\n{description}\n\n"
                "Make it personal, confident, and specific to this role and company."
                + (f"\nApplication link for reference: {apply_link}" if apply_link else ""),
            )
        return AgentResponse(response=response)
