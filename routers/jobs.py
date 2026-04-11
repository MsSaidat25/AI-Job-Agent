"""Job search, market insights, and document generation endpoints."""

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter

from routers.schemas import (
    AgentResponse,
    ApplicationTipsRequest,
    CoverLetterRequest,
    JobDetailResponse,
    JobImportRequest,
    JobImportResponse,
    JobSearchRequest,
    JobSearchRequestV2,
    JobSearchResponse,
    JobSearchResponseV2,
    MarketInsightsRequest,
    ResumeRequest,
    SaveJobResponse,
    SavedJobListResponse,
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

    @router.post("/jobs/search/v2", response_model=JobSearchResponseV2)
    @limiter.limit("10/minute")
    async def search_jobs_v2(
        request: Request,
        body: JobSearchRequestV2,
        session_id: str = session_dep,
    ):
        """Enhanced job search with filters, sorting, and pagination."""
        agent = get_agent_fn(session_id)
        try:
            response_text, job_ids, raw_jobs = await search_jobs_live(
                profile=agent.profile,
                location_filter=body.location_filter,
                include_remote=body.include_remote,
                max_results=body.max_results,
            )
        except Exception:
            return JobSearchResponseV2(jobs=[], total=0, page=body.page, has_more=False)
        for job_id, job in zip(job_ids, raw_jobs):
            if len(agent._job_cache) >= agent._job_cache_max:
                oldest_key = next(iter(agent._job_cache))
                del agent._job_cache[oldest_key]
            agent._job_cache[job_id] = job

        # Build rich responses from cache
        jobs: list[JobDetailResponse] = []
        for job_id in job_ids:
            cached = agent._job_cache.get(job_id)
            if not cached:
                continue
            if isinstance(cached, dict):
                from routers.kanban import build_location
                jobs.append(JobDetailResponse(
                    id=job_id,
                    title=str(cached.get("job_title") or cached.get("title") or ""),
                    company=str(cached.get("employer_name") or cached.get("company") or ""),
                    location=build_location(cached),
                    remote_allowed=bool(cached.get("job_is_remote", False)),
                    job_type=str(cached.get("job_employment_type") or "full_time"),
                    description=(cached.get("job_description") or "")[:3000],
                    salary_min=cached.get("job_min_salary"),
                    salary_max=cached.get("job_max_salary"),
                    source_url=str(cached.get("job_apply_link") or cached.get("redirect_url") or ""),
                    source_platform=str(cached.get("_source") or ""),
                    match_score=cached.get("_match_score"),
                    match_rationale=cached.get("_match_rationale"),
                ))
            else:
                # JobListing Pydantic model
                jobs.append(JobDetailResponse(
                    id=job_id,
                    title=cached.title,
                    company=cached.company,
                    location=cached.location,
                    remote_allowed=cached.remote_allowed,
                    job_type=cached.job_type.value if hasattr(cached.job_type, "value") else str(cached.job_type),
                    description=cached.description[:3000],
                    requirements=cached.requirements,
                    nice_to_have=cached.nice_to_have,
                    salary_min=cached.salary_min,
                    salary_max=cached.salary_max,
                    currency=cached.currency,
                    posted_date=str(cached.posted_date) if cached.posted_date else None,
                    source_url=cached.source_url,
                    source_platform=cached.source_platform,
                    match_score=cached.match_score,
                    match_rationale=cached.match_rationale,
                ))

        # Apply post-filters
        if body.job_type:
            jobs = [j for j in jobs if body.job_type.lower() in j.job_type.lower()]
        if body.salary_min is not None:
            jobs = [j for j in jobs if j.salary_min is not None and j.salary_min >= body.salary_min]
        if body.salary_max is not None:
            jobs = [j for j in jobs if j.salary_max is not None and j.salary_max <= body.salary_max]

        # Sort
        if body.sort_by == "salary":
            jobs.sort(key=lambda j: j.salary_max or 0, reverse=True)
        elif body.sort_by == "date":
            jobs.sort(key=lambda j: j.posted_date or "", reverse=True)
        # relevance is the default order from scoring

        total = len(jobs)
        page_size = body.max_results
        start = (body.page - 1) * page_size
        paged = jobs[start:start + page_size]

        return JobSearchResponseV2(
            jobs=paged,
            total=total,
            page=body.page,
            has_more=start + page_size < total,
        )

    @router.get("/jobs/saved", response_model=SavedJobListResponse)
    @limiter.limit("30/minute")
    async def list_saved_jobs(
        request: Request,
        session_id: str = session_dep,
    ):
        """List all saved jobs for the current user."""
        from src.models import JobListingORM, SavedJobORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            saved_rows = (
                db.query(SavedJobORM)
                .filter_by(user_id=profile.id)
                .order_by(SavedJobORM.saved_at.desc())
                .all()
            )
            jobs: list[JobDetailResponse] = []
            for sr in saved_rows:
                r: Any = sr
                job_orm = db.query(JobListingORM).filter_by(id=r.job_id).first()
                if job_orm:
                    j: Any = job_orm
                    jobs.append(JobDetailResponse(
                        id=j.id, title=j.title, company=j.company,
                        location=j.location, remote_allowed=bool(j.remote_allowed),
                        job_type=j.job_type or "full_time",
                        description=(j.description or "")[:500],
                        salary_min=j.salary_min, salary_max=j.salary_max,
                        source_url=j.source_url or "",
                        source_platform=j.source_platform or "",
                        is_saved=True,
                    ))
            return SavedJobListResponse(jobs=jobs, total=len(jobs))
        finally:
            db.close()

    @router.get("/jobs/{job_id}", response_model=JobDetailResponse)
    @limiter.limit("30/minute")
    async def get_job_detail(
        request: Request,
        job_id: str,
        session_id: str = session_dep,
    ):
        """Get full details for a specific job by ID."""
        agent = get_agent_fn(session_id)
        cached = agent._job_cache.get(job_id)
        if not cached:
            # Try DB fallback
            from src.models import JobListingORM, init_db
            db = init_db()
            try:
                orm = db.query(JobListingORM).filter_by(id=job_id).first()
                if orm:
                    r: Any = orm
                    return JobDetailResponse(
                        id=r.id, title=r.title, company=r.company,
                        location=r.location, remote_allowed=bool(r.remote_allowed),
                        job_type=r.job_type or "full_time",
                        description=r.description or "",
                        requirements=r.requirements or [],
                        nice_to_have=r.nice_to_have or [],
                        salary_min=r.salary_min, salary_max=r.salary_max,
                        currency=r.currency or "USD",
                        posted_date=str(r.posted_date) if r.posted_date else None,
                        source_url=r.source_url or "",
                        source_platform=r.source_platform or "",
                        match_score=r.match_score,
                        match_rationale=r.match_rationale,
                    )
            finally:
                db.close()
            raise HTTPException(status_code=404, detail="Job not found.")

        if isinstance(cached, dict):
            return JobDetailResponse(
                id=job_id,
                title=cached.get("job_title", cached.get("title", "")),
                company=cached.get("employer_name", cached.get("company", "")),
                location=cached.get("job_city", cached.get("location", "")),
                remote_allowed=bool(cached.get("job_is_remote", False)),
                job_type=cached.get("job_employment_type", "full_time"),
                description=(cached.get("job_description", "") or "")[:3000],
                salary_min=cached.get("job_min_salary"),
                salary_max=cached.get("job_max_salary"),
                source_url=cached.get("job_apply_link", cached.get("redirect_url", "")),
                source_platform=cached.get("_source", ""),
                match_score=cached.get("_match_score"),
                match_rationale=cached.get("_match_rationale"),
            )
        return JobDetailResponse(
            id=job_id, title=cached.title, company=cached.company,
            location=cached.location, remote_allowed=cached.remote_allowed,
            job_type=cached.job_type.value if hasattr(cached.job_type, "value") else str(cached.job_type),
            description=cached.description[:3000],
            requirements=cached.requirements,
            nice_to_have=cached.nice_to_have,
            salary_min=cached.salary_min, salary_max=cached.salary_max,
            currency=cached.currency,
            posted_date=str(cached.posted_date) if cached.posted_date else None,
            source_url=cached.source_url,
            source_platform=cached.source_platform,
            match_score=cached.match_score,
            match_rationale=cached.match_rationale,
        )

    @router.post("/jobs/{job_id}/save", response_model=SaveJobResponse)
    @limiter.limit("30/minute")
    async def save_job(
        request: Request,
        job_id: str,
        session_id: str = session_dep,
    ):
        """Save a job to the user's saved jobs list."""
        from src.models import JobListingORM, SavedJobORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        agent = get_agent_fn(session_id)
        db = init_db()
        try:
            # Persist job listing if not already in DB
            existing_job = db.query(JobListingORM).filter_by(id=job_id).first()
            if not existing_job:
                cached = agent._job_cache.get(job_id)
                if not cached:
                    raise HTTPException(status_code=404, detail="Job not found in cache or database.")
                if isinstance(cached, dict):
                    job_orm = JobListingORM(
                        id=job_id,
                        title=cached.get("job_title", cached.get("title", "")),
                        company=cached.get("employer_name", cached.get("company", "")),
                        location=cached.get("job_city", cached.get("location", "")),
                        remote_allowed=bool(cached.get("job_is_remote", False)),
                        job_type=cached.get("job_employment_type", "full_time"),
                        description=cached.get("job_description", "")[:5000],
                        source_url=cached.get("job_apply_link", ""),
                        source_platform=cached.get("_source", ""),
                        salary_min=cached.get("job_min_salary"),
                        salary_max=cached.get("job_max_salary"),
                    )
                else:
                    job_orm = JobListingORM(
                        id=job_id, title=cached.title, company=cached.company,
                        location=cached.location, remote_allowed=cached.remote_allowed,
                        job_type=cached.job_type.value if hasattr(cached.job_type, "value") else str(cached.job_type),
                        description=cached.description[:5000],
                        requirements=cached.requirements,
                        nice_to_have=cached.nice_to_have,
                        salary_min=cached.salary_min, salary_max=cached.salary_max,
                        currency=cached.currency,
                        source_url=cached.source_url,
                        source_platform=cached.source_platform,
                    )
                db.add(job_orm)
                db.flush()

            # Check if already saved
            existing_save = db.query(SavedJobORM).filter_by(
                user_id=profile.id, job_id=job_id,
            ).first()
            if existing_save:
                return SaveJobResponse(message="Job already saved.", job_id=job_id, saved=True)

            saved = SavedJobORM(user_id=profile.id, job_id=job_id)
            db.add(saved)
            db.commit()
            return SaveJobResponse(message="Job saved.", job_id=job_id, saved=True)
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @router.delete("/jobs/{job_id}/save", response_model=SaveJobResponse)
    @limiter.limit("30/minute")
    async def unsave_job(
        request: Request,
        job_id: str,
        session_id: str = session_dep,
    ):
        """Remove a job from saved list."""
        from src.models import SavedJobORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            saved = db.query(SavedJobORM).filter_by(
                user_id=profile.id, job_id=job_id,
            ).first()
            if saved:
                db.delete(saved)
                db.commit()
            return SaveJobResponse(message="Job unsaved.", job_id=job_id, saved=False)
        finally:
            db.close()

    @router.post("/jobs/import", response_model=JobImportResponse)
    @limiter.limit("30/minute")
    async def import_job(
        request: Request,
        body: JobImportRequest,
        session_id: str = session_dep,
    ):
        """Import a job from the Chrome extension or manual entry."""
        from src.models import JobListingORM, init_db

        db = init_db()
        try:
            # Deduplicate by source_url
            if body.source_url:
                existing = db.query(JobListingORM).filter_by(source_url=body.source_url).first()
                if existing:
                    r: Any = existing
                    return JobImportResponse(
                        job_id=r.id, title=r.title, company=r.company, is_duplicate=True,
                    )

            job_id = str(uuid.uuid4())
            job_orm = JobListingORM(
                id=job_id,
                title=body.title,
                company=body.company,
                location=body.location,
                description=body.description[:5000],
                source_url=body.source_url,
                source_platform=body.source_platform,
            )
            db.add(job_orm)
            db.commit()

            # Also add to agent cache
            agent = get_agent_fn(session_id)
            agent._job_cache[job_id] = {
                "job_id": job_id,
                "job_title": body.title,
                "employer_name": body.company,
                "job_city": body.location,
                "job_description": body.description,
                "job_apply_link": body.source_url,
                "_source": body.source_platform,
            }

            return JobImportResponse(
                job_id=job_id, title=body.title, company=body.company,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

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
        job_title = job.get("job_title", "the role") if isinstance(job, dict) else job.title
        company = job.get("employer_name", "the company") if isinstance(job, dict) else job.company
        description = ((job.get("job_description") or "") if isinstance(job, dict) else job.description)[:1500]
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
        job_title = job.get("job_title", "the role") if isinstance(job, dict) else job.title
        company = job.get("employer_name", "the company") if isinstance(job, dict) else job.company
        description = ((job.get("job_description") or "") if isinstance(job, dict) else job.description)[:1500]
        apply_link = (job.get("job_apply_link", "") if isinstance(job, dict) else job.source_url)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(
                agent.chat,
                f"Generate a compelling cover letter for the '{job_title}' position at {company}. "
                f"Job description:\n\n{description}\n\n"
                "Make it personal, confident, and specific to this role and company."
                + (f"\nApplication link for reference: {apply_link}" if apply_link else ""),
            )
        return AgentResponse(response=response)
