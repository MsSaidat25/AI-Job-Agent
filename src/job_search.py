# Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com). All Rights Reserved.
# avien@aviensolutions.com
"""
Job Search — Live data via JSearch API (Indeed / LinkedIn / Glassdoor).

Exports two interfaces:
  1. JobSearchEngine + MarketIntelligenceService  — classes used by agent.py (sync)
  2. search_jobs_live()                           — async function used by api.py
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Optional, cast

import httpx
from anthropic.types import TextBlock
from pydantic import BaseModel

from config.settings import AGENT_MODEL
from src.models import JobListing, JobType, UserProfile

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

JSEARCH_API_KEY  = os.getenv("JSEARCH_API_KEY", "")
JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HEADERS  = {
    "X-RapidAPI-Key":  JSEARCH_API_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
}


# ── Market insight model ──────────────────────────────────────────────────────
# This is the LLM-response schema used by MarketIntelligenceService.
# It differs from src.models.MarketInsight which is the persistence/ORM model.

class MarketInsightLLM(BaseModel):
    region:         str
    industry:       str
    summary:        str
    avg_salary_min: Optional[int]  = None
    avg_salary_max: Optional[int]  = None
    top_skills:     list[str]      = []
    top_employers:  list[str]      = []
    hiring_trend:   str            = ""
    tips:           str            = ""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_query(profile: UserProfile, location_filter: str = "") -> str:
    role     = (profile.desired_roles[0] if profile.desired_roles else "software engineer")
    location = location_filter or profile.location or "Canada"
    return f"{role} in {location}"


def _score_job(job: dict, profile: UserProfile) -> tuple[int, str]:
    score   = 50
    reasons = []
    desc    = (job.get("job_description") or "").lower()
    title   = (job.get("job_title")       or "").lower()

    matched = [s for s in (profile.skills or []) if s.lower() in desc or s.lower() in title]
    score  += min(len(matched) * 5, 30)
    if matched:
        reasons.append(f"Skills: {', '.join(matched[:4])}")

    for role in (profile.desired_roles or []):
        if role.lower() in title:
            score += 10
            reasons.append(f"Title matches '{role}'")
            break

    desired_type_values = [jt.value if isinstance(jt, JobType) else jt for jt in (profile.desired_job_types or [])]
    if job.get("job_is_remote") and "remote" in desired_type_values:
        score += 5
        reasons.append("Remote")

    min_s = job.get("job_min_salary")
    max_s = job.get("job_max_salary")
    if min_s and profile.desired_salary_min and min_s >= profile.desired_salary_min:
        score += 5
    if max_s and profile.desired_salary_max and max_s <= profile.desired_salary_max:
        score += 5

    emp = (job.get("job_employment_type") or "").lower()
    for jt in (profile.desired_job_types or []):
        jt_val = jt.value if isinstance(jt, JobType) else jt
        if jt_val.replace("_", " ") in emp:
            score += 5
            break

    score     = min(max(score, 0), 100)
    rationale = "; ".join(reasons) if reasons else "General profile match"
    return score, rationale


def _to_listing(job: dict, profile: UserProfile) -> JobListing:
    score, rationale = _score_job(job, profile)
    city     = job.get("job_city")    or ""
    state    = job.get("job_state")   or ""
    country  = job.get("job_country") or ""
    location = ", ".join(p for p in [city, state, country] if p) or "Location not listed"
    currency = getattr(profile, "preferred_currency", None) or "USD"

    raw_type = (job.get("job_employment_type") or "full_time").lower().replace(" ", "_")
    try:
        job_type = JobType(raw_type)
    except ValueError:
        job_type = JobType.FULL_TIME

    raw_date = (job.get("job_posted_at_datetime_utc") or "")[:10] or None
    from datetime import date as _date
    posted_date: _date | None = None
    if raw_date:
        try:
            posted_date = _date.fromisoformat(raw_date)
        except ValueError:
            posted_date = None

    return JobListing(
        id              = job.get("job_id") or str(uuid.uuid4()),
        title           = job.get("job_title")       or "Untitled Role",
        company         = job.get("employer_name")   or "Unknown Company",
        location        = location,
        remote_allowed  = job.get("job_is_remote", False),
        job_type        = job_type,
        description     = (job.get("job_description") or "")[:2000],
        requirements    = [],
        salary_min      = job.get("job_min_salary"),
        salary_max      = job.get("job_max_salary"),
        currency        = currency,
        source_platform = job.get("job_publisher")   or "JSearch",
        source_url      = job.get("job_apply_link")  or job.get("job_google_link") or "",
        posted_date     = posted_date,
        match_score     = score,
        match_rationale = rationale,
    )


def _format_md(job: JobListing, index: int) -> str:
    score  = job.match_score or 0
    icon   = "🟡" if score >= 80 else "🟢" if score >= 60 else "🔵"
    salary = (
        f"{job.currency} {int(job.salary_min):,} – {int(job.salary_max):,}"
        if job.salary_min and job.salary_max else
        f"{job.currency} {int(job.salary_min):,}+" if job.salary_min else
        "Salary not listed"
    )
    remote  = " · Remote" if job.remote_allowed else ""
    apply   = f"\n**Apply:** {job.source_url}" if job.source_url else ""
    desc    = job.description[:300] + ("…" if len(job.description) > 300 else "")
    return (
        f"## {index}. {job.title}\n"
        f"**Company:** {job.company}\n"
        f"**Location:** {job.location}{remote}\n"
        f"**Salary:** {salary} · **Posted:** {job.posted_date}\n"
        f"**Match:** {icon} {score}/100 — {job.match_rationale}\n"
        f"{desc}{apply}\n---"
    )


def _jsearch_sync(query: str) -> list[dict]:
    """Blocking HTTP call — safe to call from synchronous agent loop."""
    if not JSEARCH_API_KEY:
        return []
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.get(JSEARCH_BASE_URL, headers=JSEARCH_HEADERS,
                      params={"query": query, "page": "1", "num_pages": "1", "date_posted": "month"})
            r.raise_for_status()
            return r.json().get("data", [])
    except Exception:
        logger.exception("JSearch sync request failed for query: %s", query)
        return []


async def _jsearch_async(query: str) -> list[dict]:
    """Async HTTP call — used by search_jobs_live()."""
    if not JSEARCH_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(JSEARCH_BASE_URL, headers=JSEARCH_HEADERS,
                            params={"query": query, "page": "1", "num_pages": "1", "date_posted": "month"})
            r.raise_for_status()
            return r.json().get("data", [])
    except Exception:
        logger.exception("JSearch async request failed for query: %s", query)
        return []


# ══════════════════════════════════════════════════════════════════════════════
#  CLASS-BASED INTERFACE  (used by src/agent.py — synchronous)
# ══════════════════════════════════════════════════════════════════════════════

class JobSearchEngine:
    """
    Synchronous job search used by JobAgent.
    Fetches real listings from JSearch and maps them to JobListing models.
    The `client` shim is kept for API compatibility but not used for searching.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def search(
        self,
        profile:        UserProfile,
        location_filter: str  = "",
        include_remote:  bool = True,
        max_results:     int  = 10,
    ) -> list[JobListing]:
        query   = _build_query(profile, location_filter)
        raw     = _jsearch_sync(query)
        if not raw:
            return []
        listings = sorted(
            [_to_listing(j, profile) for j in raw],
            key=lambda x: x.match_score or 0, reverse=True
        )
        return listings[:max_results]

    def filter_by_location(
        self,
        listings:       list[JobListing],
        location_filter: str,
        include_remote:  bool = True,
    ) -> list[JobListing]:
        loc    = location_filter.lower()
        result = [
            j for j in listings
            if loc in j.location.lower() or (include_remote and j.remote_allowed)
        ]
        return result or listings   # fallback: return all if nothing matched

    def analyze_skill_gaps(
        self,
        profile: UserProfile,
        region: str = "",
    ) -> dict[str, Any]:
        """Analyse skill gaps by comparing the user's profile against live job postings.

        Returns must-have gaps, nice-to-have gaps, hidden strengths, and upskill ROI.
        """
        listings = self.search(profile, location_filter=region, max_results=10)
        if not listings:
            return {
                "must_have_gaps": [],
                "nice_to_have_gaps": [],
                "hidden_strengths": [],
                "upskill_roi": [],
                "analysis_note": "No job listings found to analyse. Try a broader search.",
            }

        descriptions = "\n---\n".join(
            f"Title: {j.title}\nCompany: {j.company}\nDescription: {j.description[:500]}"
            for j in listings[:8]
        )

        prompt = f"""Analyse skill gaps for this job seeker based on real job postings.

=== CANDIDATE ===
Skills: {", ".join(profile.skills)}
Experience: {profile.experience_level.value} ({profile.years_of_experience} years)
Target roles: {", ".join(profile.desired_roles)}

=== JOB POSTINGS ({len(listings)} found) ===
{descriptions}

Return ONLY valid JSON with:
- "must_have_gaps": list of skills in 70%+ of postings that the candidate lacks, each as {{"skill": str, "frequency_pct": int}}
- "nice_to_have_gaps": list of skills in 30-70% of postings the candidate lacks, same format
- "hidden_strengths": list of skills the candidate has that appear in <20% of postings (competitive advantage)
- "upskill_roi": list of {{"skill": str, "estimated_salary_bump_pct": int, "learning_effort": "low"|"medium"|"high"}}
"""
        try:
            response = self._client.messages.create(
                model=AGENT_MODEL,
                max_tokens=1024,
                system="You are a career skills analyst. Respond ONLY with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = cast(TextBlock, response.content[0]).text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            return {
                "must_have_gaps": data.get("must_have_gaps", []),
                "nice_to_have_gaps": data.get("nice_to_have_gaps", []),
                "hidden_strengths": data.get("hidden_strengths", []),
                "upskill_roi": data.get("upskill_roi", []),
            }
        except Exception:
            logger.exception("Skill gap analysis failed")
            return {
                "must_have_gaps": [],
                "nice_to_have_gaps": [],
                "hidden_strengths": [],
                "upskill_roi": [],
                "error": "Skill gap analysis temporarily unavailable.",
            }


class MarketIntelligenceService:
    """AI-powered market intelligence — stays AI-generated (correct tool for qualitative data)."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def get_insights(self, region: str, industry: str) -> MarketInsightLLM:
        try:
            resp = self._client.messages.create(
                model=AGENT_MODEL, max_tokens=1024,
                system="You are a job market analyst. Respond ONLY with valid JSON — no markdown fences.",
                messages=[{"role": "user", "content": (
                    f"Job market report for {industry} in {region}. "
                    "Return JSON with keys: summary, avg_salary_min, avg_salary_max, "
                    "top_skills (list), top_employers (list), hiring_trend, tips."
                )}],
            )
            text = next((b.text for b in resp.content if b.type == "text"), "{}")
            data = json.loads(text.strip())
            return MarketInsightLLM(region=region, industry=industry, **data)
        except Exception as e:
            return MarketInsightLLM(
                region=region, industry=industry,
                summary=f"Market data for {industry} in {region} temporarily unavailable. ({e})"
            )

    def get_application_tips(self, region: str) -> str:
        try:
            resp = self._client.messages.create(
                model=AGENT_MODEL, max_tokens=1024,
                system="You are an expert career coach with deep global hiring knowledge.",
                messages=[{"role": "user", "content": (
                    f"Key job application tips for applying in {region}: "
                    "CV/resume norms, cover letter expectations, interview etiquette, "
                    "cultural nuances, common mistakes."
                )}],
            )
            return next((b.text for b in resp.content if b.type == "text"), "No tips available.")
        except Exception as e:
            return f"Tips for {region} temporarily unavailable. ({e})"


# ══════════════════════════════════════════════════════════════════════════════
#  ASYNC INTERFACE  (used directly by api.py)
# ══════════════════════════════════════════════════════════════════════════════

async def search_jobs_live(
    profile:        UserProfile,
    location_filter: str  = "",
    include_remote:  bool = True,
    max_results:     int  = 10,
) -> tuple[str, list[str], list[dict]]:
    """
    Async live job search for api.py endpoints.
    Returns: (markdown_text, job_ids, raw_jobs)
    """
    if not JSEARCH_API_KEY:
        return ("⚠ JSEARCH_API_KEY not set. Add it to your .env file.", [], [])

    query = _build_query(profile, location_filter)
    raw   = await _jsearch_async(query)

    if not raw:
        return (f"No jobs found for **{query}**. Try a broader location or different role.", [], [])

    listings = sorted(
        [_to_listing(j, profile) for j in raw],
        key=lambda x: x.match_score or 0, reverse=True
    )[:max_results]

    raw_by_id = {j["job_id"]: j for j in raw if j.get("job_id")}
    header    = f"# Job Search Results\n**Query:** {query} · **Found:** {len(listings)} roles\n\n"
    parts, job_ids, sorted_raw = [], [], []

    for i, listing in enumerate(listings, 1):
        job_ids.append(listing.id)
        sorted_raw.append(raw_by_id.get(listing.id, {}))
        parts.append(_format_md(listing, i))

    return header + "\n".join(parts), job_ids, sorted_raw
