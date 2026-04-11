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
import re
import uuid
from datetime import date as _date
from typing import Any, Optional, cast

import httpx
from anthropic.types import TextBlock
from pydantic import BaseModel

from config.settings import (
    AGENT_MODEL,
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    ADZUNA_COUNTRY,
    GREENHOUSE_BOARDS,
    JSEARCH_API_KEY,
)
from src.job_boards_greenhouse import fetch_all as _greenhouse_fetch_all
from src.llm_client import create_message_with_failover
from src.models import JobListing, JobType, UserProfile
from src.utils import strip_json_fences

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HEADERS  = {
    "X-RapidAPI-Key":  JSEARCH_API_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
}

# Adzuna (fallback / parallel job search provider)
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


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

def _dedup_fingerprint(job: dict) -> tuple[str, str, str]:
    """Return a stable (source_url, title, company) tuple for dedup.

    JSearch and Adzuna often surface the same listing with different
    ``job_id`` values, so exact-id dedup alone doesn't catch cross-provider
    duplicates. The fingerprint normalizes whitespace/case and strips
    tracking query strings from the apply URL.
    """
    def _norm(s: Any) -> str:
        return " ".join(str(s or "").lower().split())

    url_raw = job.get("job_apply_link") or job.get("redirect_url") or job.get("source_url") or ""
    url = str(url_raw).split("?", 1)[0]
    title = _norm(job.get("job_title") or job.get("title") or "")
    company = _norm(job.get("employer_name") or job.get("company") or "")
    return (url, title, company)


def _build_query(profile: UserProfile, location_filter: str = "") -> str:
    role     = (profile.desired_roles[0] if profile.desired_roles else "software engineer")
    location = location_filter or profile.location or "Canada"
    return f"{role} in {location}"


def _score_job(job: dict, profile: UserProfile) -> tuple[int, str]:
    score   = 50
    reasons = []
    desc    = (job.get("job_description") or "").lower()
    title   = (job.get("job_title")       or "").lower()

    def _skill_pattern(skill: str) -> str:
        escaped = re.escape(skill.lower())
        if re.fullmatch(r'\w+', skill):
            return r'(?<!\w)' + escaped + r'(?!\w)'
        return r'(?<![A-Za-z0-9_])' + escaped + r'(?![A-Za-z0-9_])'

    matched = [
        s for s in (profile.skills or [])
        if re.search(_skill_pattern(s), desc)
        or re.search(_skill_pattern(s), title)
    ]
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


# ── Adzuna helpers ───────────────────────────────────────────────────────────

def _adzuna_normalise(result: dict) -> dict:
    """Convert an Adzuna result dict to the JSearch-compatible format.

    This lets the existing _to_listing / _score_job pipeline work unchanged.
    """
    location = result.get("location", {})
    area = location.get("area", [])
    city = area[-1] if area else ""
    state = area[-2] if len(area) >= 2 else ""
    country = area[0] if area else ""

    return {
        "job_id": f"adzuna-{result.get('id', uuid.uuid4())}",
        "job_title": result.get("title", ""),
        "employer_name": result.get("company", {}).get("display_name", ""),
        "job_description": result.get("description", ""),
        "job_city": city,
        "job_state": state,
        "job_country": country,
        "job_is_remote": "remote" in (result.get("title", "") + result.get("description", "")).lower(),
        "job_employment_type": result.get("contract_type", "full_time"),
        "job_min_salary": result.get("salary_min"),
        "job_max_salary": result.get("salary_max"),
        "job_posted_at_datetime_utc": result.get("created", ""),
        "job_apply_link": result.get("redirect_url", ""),
        "job_google_link": "",
        "job_publisher": "Adzuna",
    }


def _adzuna_params(query: str) -> dict[str, str]:
    """Build Adzuna API query parameters."""
    return {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": "20",
        "what": query,
        "max_days_old": "30",
        "content-type": "application/json",
    }


def _adzuna_url() -> str:
    return ADZUNA_BASE_URL.format(country=ADZUNA_COUNTRY)


def _adzuna_sync(query: str) -> list[dict]:
    """Blocking Adzuna HTTP call."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.get(_adzuna_url(), params=_adzuna_params(query))
            r.raise_for_status()
            results = r.json().get("results", [])
            return [_adzuna_normalise(item) for item in results]
    except Exception:
        logger.exception("Adzuna sync request failed for query: %s", query)
        return []


async def _adzuna_async(query: str) -> list[dict]:
    """Async Adzuna HTTP call."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(_adzuna_url(), params=_adzuna_params(query))
            r.raise_for_status()
            results = r.json().get("results", [])
            return [_adzuna_normalise(item) for item in results]
    except Exception:
        logger.exception("Adzuna async request failed for query: %s", query)
        return []


# ══════════════════════════════════════════════════════════════════════════════
#  CLASS-BASED INTERFACE  (used by src/agent.py — synchronous)
# ══════════════════════════════════════════════════════════════════════════════

class JobSearchEngine:
    """
    Synchronous job search used by JobAgent.
    Fetches real listings from JSearch and Adzuna, merges, and maps to JobListing models.
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
        query = _build_query(profile, location_filter)
        raw = _jsearch_sync(query) + _adzuna_sync(query)
        if not raw:
            return []
        # Deduplicate by job_id
        seen: set[str] = set()
        unique: list[dict] = []
        for j in raw:
            jid = j.get("job_id", "")
            if jid not in seen:
                seen.add(jid)
                unique.append(j)
        listings = sorted(
            [_to_listing(j, profile) for j in unique],
            key=lambda x: x.match_score or 0, reverse=True,
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
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=1024,
                system="You are a career skills analyst. Respond ONLY with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = cast(TextBlock, response.content[0]).text.strip()
            data = json.loads(strip_json_fences(text))
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
            resp = create_message_with_failover(
                self._client,
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
        except Exception:
            logger.exception("Market insight generation failed for %s / %s", region, industry)
            return MarketInsightLLM(
                region=region, industry=industry,
                summary=f"Market data for {industry} in {region} temporarily unavailable."
            )

    def get_application_tips(self, region: str) -> str:
        try:
            resp = create_message_with_failover(
                self._client,
                model=AGENT_MODEL, max_tokens=1024,
                system="You are an expert career coach with deep global hiring knowledge.",
                messages=[{"role": "user", "content": (
                    f"Key job application tips for applying in {region}: "
                    "CV/resume norms, cover letter expectations, interview etiquette, "
                    "cultural nuances, common mistakes."
                )}],
            )
            return next((b.text for b in resp.content if b.type == "text"), "No tips available.")
        except Exception:
            logger.exception("Application tips generation failed for %s", region)
            return f"Tips for {region} temporarily unavailable."


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
    Queries JSearch and Adzuna in parallel and merges results.
    Returns: (markdown_text, job_ids, raw_jobs)
    """
    import asyncio as _aio

    has_jsearch = bool(JSEARCH_API_KEY)
    has_adzuna = bool(ADZUNA_APP_ID and ADZUNA_APP_KEY)
    has_greenhouse = bool(GREENHOUSE_BOARDS)

    if not has_jsearch and not has_adzuna and not has_greenhouse:
        return (
            "⚠ No job search API configured. Set JSEARCH_API_KEY, "
            "ADZUNA_APP_ID/ADZUNA_APP_KEY, or GREENHOUSE_BOARDS.",
            [],
            [],
        )

    query = _build_query(profile, location_filter)

    async def _noop() -> list[dict]:
        return []

    # Fire all providers in parallel. Greenhouse has its own internal
    # fan-out across configured board tokens.
    jsearch_coro = _jsearch_async(query) if has_jsearch else _noop()
    adzuna_coro = _adzuna_async(query) if has_adzuna else _noop()
    greenhouse_coro = (
        _greenhouse_fetch_all(GREENHOUSE_BOARDS, query) if has_greenhouse else _noop()
    )
    jsearch_result, adzuna_result, greenhouse_result = await _aio.gather(
        jsearch_coro, adzuna_coro, greenhouse_coro,
    )

    raw: list[dict] = jsearch_result + adzuna_result + greenhouse_result

    if not raw:
        return (f"No jobs found for **{query}**. Try a broader location or different role.", [], [])

    # Deduplicate in two passes:
    #   1) exact job_id (catches intra-provider duplicates)
    #   2) a lightweight fingerprint over (source_url, normalized title,
    #      normalized company) to catch the same posting surfaced by
    #      *different* providers with different ``job_id`` values.
    seen_ids: set[str] = set()
    seen_fp: set[tuple[str, str, str]] = set()
    unique: list[dict] = []
    for j in raw:
        jid = j.get("job_id", "") or ""
        if jid and jid in seen_ids:
            continue
        fp = _dedup_fingerprint(j)
        if fp in seen_fp:
            continue
        if jid:
            seen_ids.add(jid)
        seen_fp.add(fp)
        unique.append(j)

    listings = sorted(
        [_to_listing(j, profile) for j in unique],
        key=lambda x: x.match_score or 0, reverse=True,
    )[:max_results]

    raw_by_id = {j["job_id"]: j for j in unique if j.get("job_id")}
    sources = set()
    if has_jsearch and jsearch_result:
        sources.add("JSearch")
    if has_adzuna and adzuna_result:
        sources.add("Adzuna")
    if has_greenhouse and greenhouse_result:
        sources.add("Greenhouse")
    source_label = " + ".join(sorted(sources)) if sources else "search"

    header = (
        f"# Job Search Results\n"
        f"**Query:** {query} · **Found:** {len(listings)} roles · **Sources:** {source_label}\n\n"
    )
    parts, job_ids, sorted_raw = [], [], []

    for i, listing in enumerate(listings, 1):
        job_ids.append(listing.id)
        sorted_raw.append(raw_by_id.get(listing.id, {}))
        parts.append(_format_md(listing, i))

    return header + "\n".join(parts), job_ids, sorted_raw
