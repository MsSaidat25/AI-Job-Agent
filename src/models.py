"""Pydantic domain models and re-exports for the AI Job Agent.

Pydantic models are defined here. SQLAlchemy ORM, database bootstrap,
and encryption helpers live in src/models_db.py but are re-exported
so existing ``from src.models import X`` imports continue to work.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ───────────────────────────────────────────────────────────

class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    REMOTE = "remote"


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    OFFER_RECEIVED = "offer_received"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


# ── Pydantic domain models ─────────────────────────────────────────────────

class UserProfile(BaseModel):
    """Everything we know about the job seeker (never logged externally)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: Optional[str] = None
    location: str
    skills: list[str] = Field(default_factory=list)
    experience_level: ExperienceLevel = ExperienceLevel.MID
    years_of_experience: int = 0
    education: list[dict[str, Any]] = Field(default_factory=list)
    work_history: list[dict[str, Any]] = Field(default_factory=list)
    desired_roles: list[str] = Field(default_factory=list)
    desired_job_types: list[JobType] = Field(default_factory=list)
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    languages: list[str] = Field(default_factory=lambda: ["English"])
    certifications: list[str] = Field(default_factory=list)
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    preferred_currency: str = "USD"
    career_identity_statement: Optional[str] = None
    preferred_locations: list[str] = Field(default_factory=list)
    remote_preference: str = "flexible"
    non_compete_companies: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    firebase_uid: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("skills", "desired_roles", mode="before")
    @classmethod
    def deduplicate(cls, v: list) -> list:
        return list(dict.fromkeys(v))


class JobListing(BaseModel):
    """A single job opportunity, normalised from any source."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    company: str
    location: str
    remote_allowed: bool = False
    job_type: JobType = JobType.FULL_TIME
    experience_level: ExperienceLevel = ExperienceLevel.MID
    description: str
    requirements: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    posted_date: Optional[date] = None
    application_deadline: Optional[date] = None
    source_url: str = ""
    source_platform: str = ""
    industry: str = ""
    keywords: list[str] = Field(default_factory=list)
    match_score: Optional[float] = None
    match_rationale: Optional[str] = None


class ApplicationRecord(BaseModel):
    """Tracks a single job application through its lifecycle."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    status: ApplicationStatus = ApplicationStatus.DRAFT
    resume_version: Optional[str] = None
    cover_letter_version: Optional[str] = None
    submitted_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    employer_feedback: Optional[str] = None
    interview_dates: list[datetime] = Field(default_factory=list)
    notes: str = ""


class MarketInsight(BaseModel):
    """Aggregated intelligence about a regional / sectoral job market."""

    region: str
    industry: str
    top_skills_in_demand: list[str] = Field(default_factory=list)
    avg_salary_usd: Optional[int] = None
    job_growth_pct: Optional[float] = None
    competition_level: str = "medium"
    cultural_notes: str = ""
    trending_roles: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GeneratedDocument(BaseModel):
    """A resume or cover letter produced by the document generator."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    doc_type: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str = ""
    tailoring_notes: str = ""
    ats_score: Optional[float] = None
    missing_keywords: list[str] = Field(default_factory=list)


class DreamScenario(BaseModel):
    """Input describing the user's dream career goal."""

    current_role: str = ""
    dream_role: str
    dream_industry: str = ""
    dream_location: str = ""
    timeline_months: int = 12


class GapReport(BaseModel):
    """Analysis of the gap between current profile and dream role."""

    dream_role: str
    overlapping_skills: list[str] = Field(default_factory=list)
    missing_skills: list[dict[str, Any]] = Field(default_factory=list)
    salary_current: Optional[int] = None
    salary_dream: Optional[int] = None
    feasibility_score: float = 0.0
    feasibility_rationale: str = ""
    recommendations: list[str] = Field(default_factory=list)


class DreamTimeline(BaseModel):
    """Week-by-week plan to achieve the dream role."""

    dream_role: str
    total_weeks: int = 0
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Re-exports from models_db (ORM, DB bootstrap, encryption) ─────────────
# Keep all existing ``from src.models import X`` working.

from src.models_db import (  # noqa: E402, F401
    Base,
    UserProfileORM,
    JobListingORM,
    ApplicationRecordORM,
    MarketInsightORM,
    GeneratedDocumentORM,
    CareerDreamORM,
    EmployerWaitlistORM,
    SavedJobORM,
    DocumentVariantORM,
    DailyFeedORM,
    FollowUpScheduleORM,
    AutoApplySettingsORM,
    AutoApplyQueueORM,
    EmailOAuthTokenORM,
    OfferORM,
    SavedSearchORM,
    profile_to_orm,
    orm_to_profile,
    reset_encryption_key,
)

from src.models_bootstrap import (  # noqa: E402, F401
    reset_db_state,
    get_active_engine,
    get_engine,
    init_db,
)

# These module-level names are patched by tests for DB isolation.
# They must exist here so monkeypatch("src.models.DB_PATH", ...) works.
from config.settings import DATABASE_URL, DATABASE_URL_FAILOVER, DB_PATH  # noqa: E402, F401
