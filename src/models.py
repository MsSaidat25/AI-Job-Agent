"""
Pydantic + SQLAlchemy data models for the AI Job Agent.

Design decisions
────────────────
• Pydantic models are the public API / in-memory representations.
• SQLAlchemy ORM models are the persistence layer.
• No PII (name, email, phone) is stored in plaintext when ENCRYPT_USER_DATA=true.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
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
    created_at: datetime = Field(default_factory=datetime.utcnow)

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
    last_updated: datetime = Field(default_factory=datetime.utcnow)
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
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class GeneratedDocument(BaseModel):
    """A resume or cover letter produced by the document generator."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    doc_type: str                  # "resume" | "cover_letter"
    content: str                   # full text / markdown
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = ""
    tailoring_notes: str = ""      # why specific edits were made


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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    last_updated = Column(DateTime, default=datetime.utcnow)
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
    last_updated = Column(DateTime, default=datetime.utcnow)


class GeneratedDocumentORM(Base):
    __tablename__ = "generated_documents"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.id"))
    job_id = Column(String, ForeignKey("job_listings.id"))
    doc_type = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String, default="")
    tailoring_notes = Column(Text, default="")


# ── Database bootstrap ─────────────────────────────────────────────────────

def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> Session:
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()
