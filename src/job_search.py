"""
Job Search & Market Intelligence module.

Architecture
────────────
• JobSearchEngine  – orchestrates searches via pluggable source adapters.
• MarketIntelligenceService – uses Claude to synthesise regional/industry insights.
• Built-in mock adapter for offline / test use; real adapters can be dropped in.

Bias mitigation
───────────────
• Match scoring is based purely on skill overlap, role alignment, and location
  preferences — never on protected attributes.
• The LLM prompt explicitly instructs the model to ignore any demographic signals.
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import date, timedelta
from typing import Any, Optional

import anthropic

from config.settings import AGENT_MODEL, MAX_JOBS_PER_SEARCH, MAX_TOKENS
from src.models import ExperienceLevel, JobListing, JobType, MarketInsight, UserProfile
from src.privacy import sanitise_for_llm, strip_protected_attributes


# ── Mock job data (representative sample across geographies) ───────────────

_MOCK_JOBS: list[dict[str, Any]] = [
    {
        "title": "Senior Software Engineer",
        "company": "TechCorp",
        "location": "Austin, TX, USA",
        "remote_allowed": True,
        "job_type": JobType.FULL_TIME,
        "experience_level": ExperienceLevel.SENIOR,
        "description": "Build scalable backend services for our SaaS platform.",
        "requirements": ["Python", "AWS", "PostgreSQL", "REST APIs", "Docker"],
        "nice_to_have": ["Kubernetes", "GraphQL"],
        "salary_min": 130_000,
        "salary_max": 170_000,
        "currency": "USD",
        "source_platform": "LinkedIn",
        "industry": "Technology",
        "keywords": ["backend", "cloud", "python"],
    },
    {
        "title": "Data Scientist",
        "company": "AnalyticsPro",
        "location": "New York, NY, USA",
        "remote_allowed": False,
        "job_type": JobType.FULL_TIME,
        "experience_level": ExperienceLevel.MID,
        "description": "Develop predictive models and derive actionable insights.",
        "requirements": ["Python", "Machine Learning", "SQL", "TensorFlow"],
        "nice_to_have": ["Spark", "Airflow", "A/B Testing"],
        "salary_min": 110_000,
        "salary_max": 145_000,
        "currency": "USD",
        "source_platform": "Indeed",
        "industry": "Finance",
        "keywords": ["ML", "data", "analytics"],
    },
    {
        "title": "Frontend Developer",
        "company": "DesignHub",
        "location": "London, UK",
        "remote_allowed": True,
        "job_type": JobType.FULL_TIME,
        "experience_level": ExperienceLevel.MID,
        "description": "Craft pixel-perfect UIs with React and TypeScript.",
        "requirements": ["React", "TypeScript", "CSS", "REST APIs"],
        "nice_to_have": ["Next.js", "Storybook", "Figma"],
        "salary_min": 55_000,
        "salary_max": 80_000,
        "currency": "GBP",
        "source_platform": "Glassdoor",
        "industry": "Technology",
        "keywords": ["react", "frontend", "typescript"],
    },
    {
        "title": "Product Manager",
        "company": "InnovateCo",
        "location": "Berlin, Germany",
        "remote_allowed": True,
        "job_type": JobType.FULL_TIME,
        "experience_level": ExperienceLevel.SENIOR,
        "description": "Lead cross-functional teams to ship world-class products.",
        "requirements": ["Product Strategy", "Agile", "Stakeholder Management", "SQL"],
        "nice_to_have": ["B2B SaaS", "OKRs", "User Research"],
        "salary_min": 90_000,
        "salary_max": 120_000,
        "currency": "EUR",
        "source_platform": "XING",
        "industry": "Technology",
        "keywords": ["product", "agile", "roadmap"],
    },
    {
        "title": "DevOps Engineer",
        "company": "CloudBase",
        "location": "Remote",
        "remote_allowed": True,
        "job_type": JobType.REMOTE,
        "experience_level": ExperienceLevel.MID,
        "description": "Automate CI/CD pipelines and manage cloud infrastructure.",
        "requirements": ["Kubernetes", "Terraform", "AWS", "CI/CD", "Linux"],
        "nice_to_have": ["Prometheus", "Grafana", "Go"],
        "salary_min": 120_000,
        "salary_max": 155_000,
        "currency": "USD",
        "source_platform": "Remote.co",
        "industry": "Technology",
        "keywords": ["devops", "cloud", "kubernetes"],
    },
    {
        "title": "UX Designer",
        "company": "CreativeMinds",
        "location": "Toronto, Canada",
        "remote_allowed": False,
        "job_type": JobType.FULL_TIME,
        "experience_level": ExperienceLevel.MID,
        "description": "Design intuitive digital experiences grounded in user research.",
        "requirements": ["Figma", "User Research", "Prototyping", "Accessibility"],
        "nice_to_have": ["Motion Design", "HTML/CSS", "Design Systems"],
        "salary_min": 85_000,
        "salary_max": 110_000,
        "currency": "CAD",
        "source_platform": "Workopolis",
        "industry": "Media",
        "keywords": ["UX", "design", "figma"],
    },
    {
        "title": "Machine Learning Engineer",
        "company": "AIStart",
        "location": "San Francisco, CA, USA",
        "remote_allowed": True,
        "job_type": JobType.FULL_TIME,
        "experience_level": ExperienceLevel.SENIOR,
        "description": "Deploy and scale LLM-based products in production.",
        "requirements": ["Python", "PyTorch", "MLOps", "Docker", "LLMs"],
        "nice_to_have": ["RLHF", "vLLM", "Triton"],
        "salary_min": 160_000,
        "salary_max": 220_000,
        "currency": "USD",
        "source_platform": "LinkedIn",
        "industry": "Artificial Intelligence",
        "keywords": ["llm", "ml", "pytorch"],
    },
    {
        "title": "Marketing Analyst",
        "company": "GrowthLab",
        "location": "Sydney, Australia",
        "remote_allowed": False,
        "job_type": JobType.FULL_TIME,
        "experience_level": ExperienceLevel.ENTRY,
        "description": "Analyse campaign performance and support growth strategy.",
        "requirements": ["Google Analytics", "Excel", "SQL", "Data Visualisation"],
        "nice_to_have": ["Tableau", "Python", "A/B Testing"],
        "salary_min": 65_000,
        "salary_max": 85_000,
        "currency": "AUD",
        "source_platform": "Seek",
        "industry": "Marketing",
        "keywords": ["analytics", "marketing", "growth"],
    },
]


def _build_listing(raw: dict[str, Any], days_ago: int = 0) -> JobListing:
    today = date.today()
    return JobListing(
        id=str(uuid.uuid4()),
        posted_date=today - timedelta(days=days_ago),
        application_deadline=today + timedelta(days=30 - days_ago),
        **raw,
    )


# ── Job Search Engine ──────────────────────────────────────────────────────

class JobSearchEngine:
    """
    Searches for jobs matching the user profile.

    Currently uses a mock data source.  To integrate a real job board API:
        1. Implement a method like `_fetch_from_linkedin(profile)`.
        2. Call it inside `search()` and merge results.
    """

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic()

    # ── Public API ─────────────────────────────────────────────────────────

    def search(
        self,
        profile: UserProfile,
        max_results: int = MAX_JOBS_PER_SEARCH,
    ) -> list[JobListing]:
        """Return ranked job listings relevant to *profile*."""
        raw_listings = self._fetch_mock(profile)
        scored = self._score_with_llm(profile, raw_listings)
        scored.sort(key=lambda j: j.match_score or 0, reverse=True)
        return scored[:max_results]

    def filter_by_location(
        self,
        listings: list[JobListing],
        location: str,
        include_remote: bool = True,
    ) -> list[JobListing]:
        """Filter listings by location string (case-insensitive substring match)."""
        loc_lower = location.lower()
        return [
            j for j in listings
            if loc_lower in j.location.lower()
            or (include_remote and j.remote_allowed)
        ]

    # ── Private helpers ────────────────────────────────────────────────────

    def _fetch_mock(self, profile: UserProfile) -> list[JobListing]:
        """Return a shuffled subset of mock listings (simulates live search)."""
        sample = random.sample(_MOCK_JOBS, min(len(_MOCK_JOBS), MAX_JOBS_PER_SEARCH))
        return [_build_listing(r, days_ago=random.randint(0, 14)) for r in sample]

    def _score_with_llm(
        self, profile: UserProfile, listings: list[JobListing]
    ) -> list[JobListing]:
        """Ask Claude to score each listing for this profile (bias-safe)."""
        safe_profile = sanitise_for_llm(
            strip_protected_attributes(profile.model_dump())
        )
        listing_summaries = [
            {
                "id": j.id,
                "title": j.title,
                "requirements": j.requirements,
                "experience_level": j.experience_level,
                "location": j.location,
                "remote_allowed": j.remote_allowed,
                "industry": j.industry,
            }
            for j in listings
        ]

        prompt = f"""You are an unbiased job-matching assistant.

CANDIDATE (anonymised — no personal information):
{json.dumps(safe_profile, indent=2)}

JOB LISTINGS:
{json.dumps(listing_summaries, indent=2)}

Score each listing from 0 to 100 based ONLY on:
- Skill overlap with candidate's skills
- Alignment with desired roles
- Experience level fit
- Location / remote preference

IMPORTANT: Do NOT consider or infer any protected attributes (gender, age, ethnicity, etc.).

Return a JSON array: [{{"id": "...", "score": <0-100>, "rationale": "..."}}]
Return ONLY the JSON array, no other text.
"""
        response = self._client.messages.create(
            model=AGENT_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text.strip()
        # Defensive: strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        scores: list[dict] = json.loads(raw_text)

        score_map = {s["id"]: s for s in scores}
        for listing in listings:
            if listing.id in score_map:
                entry = score_map[listing.id]
                listing.match_score = entry.get("score")
                listing.match_rationale = entry.get("rationale")
        return listings


# ── Market Intelligence Service ────────────────────────────────────────────

class MarketIntelligenceService:
    """
    Generates actionable market insights for a given region + industry.

    Uses Claude to synthesise broad knowledge about job market conditions,
    in-demand skills, salary ranges, cultural hiring norms, and growth trends.
    """

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic()

    def get_insights(self, region: str, industry: str) -> MarketInsight:
        """Return a MarketInsight for the requested region and industry."""
        prompt = f"""You are a global job market analyst.

Provide a structured analysis of the **{industry}** job market in **{region}**.

Return ONLY valid JSON with these exact keys:
{{
  "top_skills_in_demand": ["skill1", "skill2", ...],
  "avg_salary_usd": <integer or null>,
  "job_growth_pct": <float year-over-year % or null>,
  "competition_level": "low" | "medium" | "high",
  "cultural_notes": "<hiring culture, CV norms, interview expectations>",
  "trending_roles": ["role1", "role2", ...]
}}

Be concise and factual. If data is unavailable, use null.
"""
        response = self._client.messages.create(
            model=AGENT_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data: dict = json.loads(raw)
        return MarketInsight(region=region, industry=industry, **data)

    def get_application_tips(self, region: str) -> str:
        """Return culturally-aware application tips for a region."""
        prompt = f"""You are a career coach familiar with hiring practices worldwide.

Provide 5–7 concise, actionable tips for job seekers applying to positions in **{region}**.
Cover: CV/resume format, cover letter expectations, interview etiquette, follow-up norms.
Format as a numbered list. Be specific to this region's culture.
"""
        response = self._client.messages.create(
            model=AGENT_MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
