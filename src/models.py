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

Pydantic + SQLAlchemy data models for the AI Job Agent.

Design decisions
────────────────
• Pydantic models are the public API / in-memory representations.
• SQLAlchemy ORM models are the persistence layer.
• No PII (name, email, phone) is stored in plaintext when ENCRYPT_USER_DATA=true.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config.settings import DB_PATH


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
    location: str                           # e.g. "Austin, TX, USA"
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
    source_platform: str = ""        # "LinkedIn", "Indeed", "Glassdoor", …
    industry: str = ""
    keywords: list[str] = Field(default_factory=list)
    # AI-computed fields (populated by agent)
    match_score: Optional[float] = None      # 0–100
    match_rationale: Optional[str] = None


class ApplicationRecord(BaseModel):
    """Tracks a single job application through its lifecycle."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    status: ApplicationStatus = ApplicationStatus.DRAFT
    resume_version: Optional[str] = None     # path / key
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
    job_growth_pct: Optional[float] = None   # year-over-year
    competition_level: str = "medium"        # low / medium / high
    cultural_notes: str = ""
    trending_roles: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GeneratedDocument(BaseModel):
    """A resume or cover letter produced by the document generator."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    doc_type: str                  # "resume" | "cover_letter"
    content: str                   # full text / markdown
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str = ""
    tailoring_notes: str = ""      # why specific edits were made
    ats_score: Optional[float] = None          # 0-100 ATS match percentage
    missing_keywords: list[str] = Field(default_factory=list)


# ── Career Dreamer models ─────────────────────────────────────────────────

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
    missing_skills: list[dict[str, Any]] = Field(default_factory=list)  # [{skill, learning_time_weeks, priority}]
    salary_current: Optional[int] = None
    salary_dream: Optional[int] = None
    feasibility_score: float = 0.0      # 0-100
    feasibility_rationale: str = ""
    recommendations: list[str] = Field(default_factory=list)


class DreamTimeline(BaseModel):
    """Week-by-week plan to achieve the dream role."""

    dream_role: str
    total_weeks: int = 0
    milestones: list[dict[str, Any]] = Field(default_factory=list)  # [{week, goal, actions, deliverable}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── SQLAlchemy ORM ─────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class UserProfileORM(Base):
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True)
    name_enc = Column(Text)           # encrypted blob
    email_enc = Column(Text)          # encrypted blob
    phone_enc = Column(Text, nullable=True)
    location = Column(String)
    skills = Column(JSON)
    experience_level = Column(String)
    years_of_experience = Column(Integer, default=0)
    education = Column(JSON)
    work_history = Column(JSON)
    desired_roles = Column(JSON)
    desired_job_types = Column(JSON)
    desired_salary_min = Column(Integer, nullable=True)
    desired_salary_max = Column(Integer, nullable=True)
    languages = Column(JSON)
    certifications = Column(JSON)
    portfolio_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    applications = relationship("ApplicationRecordORM", back_populates="user")


class JobListingORM(Base):
    __tablename__ = "job_listings"

    id = Column(String, primary_key=True)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    remote_allowed = Column(Boolean, default=False)
    job_type = Column(String)
    experience_level = Column(String)
    description = Column(Text)
    requirements = Column(JSON)
    nice_to_have = Column(JSON)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String, default="USD")
    posted_date = Column(Date, nullable=True)
    application_deadline = Column(Date, nullable=True)
    source_url = Column(String)
    source_platform = Column(String)
    industry = Column(String)
    keywords = Column(JSON)
    match_score = Column(Float, nullable=True)
    match_rationale = Column(Text, nullable=True)

    applications = relationship("ApplicationRecordORM", back_populates="job")


class ApplicationRecordORM(Base):
    __tablename__ = "application_records"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.id"))
    job_id = Column(String, ForeignKey("job_listings.id"))
    status = Column(String, default=ApplicationStatus.DRAFT.value)
    resume_version = Column(String, nullable=True)
    cover_letter_version = Column(String, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    employer_feedback = Column(Text, nullable=True)
    interview_dates = Column(JSON)
    notes = Column(Text, default="")

    user = relationship("UserProfileORM", back_populates="applications")
    job = relationship("JobListingORM", back_populates="applications")


class MarketInsightORM(Base):
    __tablename__ = "market_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String)
    industry = Column(String)
    top_skills_in_demand = Column(JSON)
    avg_salary_usd = Column(Integer, nullable=True)
    job_growth_pct = Column(Float, nullable=True)
    competition_level = Column(String, default="medium")
    cultural_notes = Column(Text, default="")
    trending_roles = Column(JSON)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GeneratedDocumentORM(Base):
    __tablename__ = "generated_documents"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.id"))
    job_id = Column(String, ForeignKey("job_listings.id"))
    doc_type = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    model_used = Column(String, default="")
    tailoring_notes = Column(Text, default="")
    ats_score = Column(Float, nullable=True)
    missing_keywords = Column(JSON, default=list)


class CareerDreamORM(Base):
    __tablename__ = "career_dreams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("user_profiles.id"))
    dream_role = Column(String)
    dream_industry = Column(String, default="")
    dream_location = Column(String, default="")
    timeline_months = Column(Integer, default=12)
    gap_report = Column(JSON, nullable=True)
    timeline_plan = Column(JSON, nullable=True)
    feasibility_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Database bootstrap ─────────────────────────────────────────────────────

def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> Session:
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()
