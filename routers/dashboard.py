"""Dashboard API router - structured JSON endpoints (no LLM calls)."""
from __future__ import annotations

import asyncio
import re
from collections import Counter
from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from src.models import ApplicationStatus

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ── Response schemas ───────────────────────────────────────────────────────

class DashboardSummaryResponse(BaseModel):
    total_applications: int = 0
    submitted: int = 0
    response_rate: float = 0.0
    interview_rate: float = 0.0
    offer_rate: float = 0.0
    avg_days_to_reply: Optional[float] = None
    by_status: dict[str, int] = Field(default_factory=dict)
    top_industries: list[list[Any]] = Field(default_factory=list)
    top_platforms: list[list[Any]] = Field(default_factory=list)
    cached_jobs: int = 0


class DashboardApplicationItem(BaseModel):
    id: str
    job_id: str
    status: str
    submitted_at: Optional[str] = None
    last_updated: Optional[str] = None
    employer_feedback: Optional[str] = None
    notes: str = ""
    job_title: Optional[str] = None
    job_company: Optional[str] = None
    job_location: Optional[str] = None
    match_score: Optional[float] = None


class DashboardApplicationsResponse(BaseModel):
    applications: list[DashboardApplicationItem]
    total: int


class DashboardActivityItem(BaseModel):
    timestamp: str
    event: str
    detail: str


class DashboardActivityResponse(BaseModel):
    activity: list[DashboardActivityItem]


class DashboardSkillsResponse(BaseModel):
    user_skills: list[str]
    in_demand_skills: list[str]
    matching_skills: list[str]
    gap_skills: list[str]
    match_pct: float = 0.0


# Common tech skills for extraction from job descriptions
_COMMON_TECH_SKILLS = [
    "python", "javascript", "typescript", "react", "node.js", "sql", "aws",
    "docker", "kubernetes", "java", "go", "rust", "c++", "ruby", "php",
    "terraform", "azure", "gcp", "postgresql", "mongodb", "redis", "graphql",
    "rest", "ci/cd", "git", "linux", "agile", "scrum", "machine learning",
    "deep learning", "data science", "devops", "microservices", "fastapi",
    "django", "flask", "spring", "angular", "vue", "svelte", "next.js",
]


def _setup_routes(
    limiter: Limiter,
    get_agent_fn,  # type: ignore[no-untyped-def]
    session_dep: Any,
) -> None:
    """Wire endpoints using the app's shared dependencies.

    Called once from api.py after the router is imported.
    """

    @router.get("/summary", response_model=DashboardSummaryResponse)
    @limiter.limit("30/minute")
    async def dashboard_summary(request: Request, session_id: str = session_dep):
        """Return structured application metrics for the frontend dashboard."""
        agent = get_agent_fn(session_id)
        metrics = await asyncio.to_thread(
            agent._tracker.compute_metrics, agent.profile.id,
        )

        return DashboardSummaryResponse(
            total_applications=metrics.get("total", 0),
            submitted=metrics.get("submitted", 0),
            response_rate=metrics.get("response_rate", 0.0),
            interview_rate=metrics.get("interview_rate", 0.0),
            offer_rate=metrics.get("offer_rate", 0.0),
            avg_days_to_reply=metrics.get("avg_days_to_reply"),
            by_status=metrics.get("by_status", {}),
            top_industries=metrics.get("top_industries", []),
            top_platforms=metrics.get("top_platforms", []),
            cached_jobs=len(agent._job_cache),
        )

    @router.get("/applications", response_model=DashboardApplicationsResponse)
    @limiter.limit("30/minute")
    async def dashboard_applications(request: Request, session_id: str = session_dep):
        """Return all applications with job details for the dashboard table."""
        agent = get_agent_fn(session_id)
        records = await asyncio.to_thread(
            agent._tracker.get_applications, agent.profile.id,
        )

        items: list[DashboardApplicationItem] = []
        for rec in records:
            job_title = job_company = job_location = None
            match_score: float | None = None
            cached = agent._job_cache.get(rec.job_id)
            if cached:
                job_title = cached.get("job_title")
                job_company = cached.get("employer_name")
                city = cached.get("job_city", "")
                state = cached.get("job_state", "")
                job_location = ", ".join(p for p in [city, state] if p) or None
                match_score = cached.get("match_score")

            items.append(DashboardApplicationItem(
                id=rec.id,
                job_id=rec.job_id,
                status=rec.status.value,
                submitted_at=rec.submitted_at.isoformat() if rec.submitted_at else None,
                last_updated=rec.last_updated.isoformat() if rec.last_updated else None,
                employer_feedback=rec.employer_feedback,
                notes=rec.notes,
                job_title=job_title,
                job_company=job_company,
                job_location=job_location,
                match_score=match_score,
            ))

        return DashboardApplicationsResponse(applications=items, total=len(items))

    @router.get("/activity", response_model=DashboardActivityResponse)
    @limiter.limit("30/minute")
    async def dashboard_activity(request: Request, session_id: str = session_dep):
        """Return recent application activity as a timeline."""
        agent = get_agent_fn(session_id)
        records = await asyncio.to_thread(
            agent._tracker.get_applications, agent.profile.id,
        )

        events: list[DashboardActivityItem] = []
        for rec in records:
            cached = agent._job_cache.get(rec.job_id)
            job_label = ""
            if cached:
                job_label = f"{cached.get('job_title', '')} at {cached.get('employer_name', '')}"

            if rec.submitted_at:
                events.append(DashboardActivityItem(
                    timestamp=rec.submitted_at.isoformat(),
                    event="applied",
                    detail=f"Applied to {job_label}" if job_label else f"Applied (job {rec.job_id[:8]}...)",
                ))
            if rec.status not in {ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED} and rec.last_updated:
                events.append(DashboardActivityItem(
                    timestamp=rec.last_updated.isoformat(),
                    event=rec.status.value,
                    detail=f"Status changed to {rec.status.value}"
                           + (f" for {job_label}" if job_label else ""),
                ))

        events.sort(key=lambda e: e.timestamp, reverse=True)
        return DashboardActivityResponse(activity=events[:50])

    @router.get("/skills", response_model=DashboardSkillsResponse)
    @limiter.limit("15/minute")
    async def dashboard_skills(request: Request, session_id: str = session_dep):
        """Compare user skills against cached job postings to show gaps."""
        agent = get_agent_fn(session_id)
        user_skills = [s.lower() for s in (agent.profile.skills or [])]

        demand_counter: Counter[str] = Counter()
        for job in agent._job_cache.values():
            desc = (job.get("job_description") or "").lower()
            title = (job.get("job_title") or "").lower()
            combined = desc + " " + title
            for skill in user_skills:
                if re.search(r'\b' + re.escape(skill) + r'\b', combined):
                    demand_counter[skill] += 1
            for kw in _COMMON_TECH_SKILLS:
                if re.search(r'\b' + re.escape(kw) + r'\b', combined):
                    demand_counter[kw] += 1

        in_demand = [s for s, _ in demand_counter.most_common(20)]
        matching = [s for s in user_skills if s in in_demand]
        gaps = [s for s in in_demand if s not in user_skills]

        match_pct = (len(matching) / len(in_demand) * 100) if in_demand else 0.0

        return DashboardSkillsResponse(
            user_skills=agent.profile.skills or [],
            in_demand_skills=in_demand,
            matching_skills=matching,
            gap_skills=gaps[:15],
            match_pct=round(match_pct, 1),
        )
