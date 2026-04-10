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

import threading
import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    Index,
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
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

import logging

from config.settings import DATABASE_URL, DATABASE_URL_FAILOVER, DB_PATH

logger = logging.getLogger(__name__)


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

    id = Column(String(36), primary_key=True)
    name_enc = Column(Text, nullable=False)
    email_enc = Column(Text, nullable=False)
    phone_enc = Column(Text, nullable=True)
    location = Column(String(200), nullable=False)
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
    preferred_currency = Column(String(5), default="USD")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    applications = relationship("ApplicationRecordORM", back_populates="user")


class JobListingORM(Base):
    __tablename__ = "job_listings"

    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=False)
    company = Column(String(300), nullable=False)
    location = Column(String(200), nullable=False)
    remote_allowed = Column(Boolean, default=False)
    job_type = Column(String(50))
    experience_level = Column(String(50))
    description = Column(Text, nullable=False)
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
    __table_args__ = (
        Index("ix_application_records_user_status", "user_id", "status"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), default=ApplicationStatus.DRAFT.value, nullable=False, index=True)
    resume_version = Column(String, nullable=True)
    cover_letter_version = Column(String, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    last_updated = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    employer_feedback = Column(Text, nullable=True)
    interview_dates = Column(JSON)
    notes = Column(Text, default="")

    user = relationship("UserProfileORM", back_populates="applications")
    job = relationship("JobListingORM", back_populates="applications")


class MarketInsightORM(Base):
    __tablename__ = "market_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String(200), nullable=False, index=True)
    industry = Column(String(200), nullable=False, index=True)
    top_skills_in_demand = Column(JSON)
    avg_salary_usd = Column(Integer, nullable=True)
    job_growth_pct = Column(Float, nullable=True)
    competition_level = Column(String, default="medium")
    cultural_notes = Column(Text, default="")
    trending_roles = Column(JSON)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GeneratedDocumentORM(Base):
    __tablename__ = "generated_documents"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    model_used = Column(String, default="")
    tailoring_notes = Column(Text, default="")
    ats_score = Column(Float, nullable=True)
    missing_keywords = Column(JSON, default=list)


class CareerDreamORM(Base):
    __tablename__ = "career_dreams"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    dream_role = Column(String, nullable=False)
    dream_industry = Column(String, default="")
    dream_location = Column(String, default="")
    timeline_months = Column(Integer, default=12)
    gap_report = Column(JSON, nullable=True)
    timeline_plan = Column(JSON, nullable=True)
    feasibility_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmployerWaitlistORM(Base):
    __tablename__ = "employer_waitlist"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(500), nullable=False, unique=True, index=True)
    company_name = Column(String(500), default="")
    company_size = Column(String(50), default="")
    signed_up_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Database bootstrap ─────────────────────────────────────────────────────

_active_engine = None
_init_lock = threading.RLock()
_tables_created = False
_SessionFactory: sessionmaker | None = None


def reset_db_state() -> None:
    """Reset cached engine and session factory. Used by tests for isolation."""
    global _active_engine, _tables_created, _SessionFactory
    with _init_lock:
        _active_engine = None
        _tables_created = False
        _SessionFactory = None

def get_active_engine():
    """Return the currently cached engine, or None if not yet initialised."""
    return _active_engine


def _enable_sqlite_fk(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
    """Enable foreign key enforcement for SQLite connections."""
    import sqlite3

    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


def get_engine(failover: bool = False):
    """Return a cached SQLAlchemy engine, creating one if needed.

    Priority:
      1. DATABASE_URL (Cloud SQL PostgreSQL) -- primary
      2. DATABASE_URL_FAILOVER (Supabase PostgreSQL) -- failover
      3. sqlite:///data/job_agent.db -- local development
    """
    global _active_engine
    if _active_engine is not None and not failover:
        return _active_engine
    with _init_lock:
        # Double-check after acquiring lock
        if _active_engine is not None and not failover:
            return _active_engine
        url = DATABASE_URL_FAILOVER if failover else DATABASE_URL
        if failover and not DATABASE_URL_FAILOVER:
            logger.error(
                "Failover requested but DATABASE_URL_FAILOVER is not configured; "
                "refusing to silently fall back to SQLite."
            )
            raise ValueError(
                "DATABASE_URL_FAILOVER must be set when failover=True is requested"
            )
        if url:
            engine = create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False,
            )
        else:
            from sqlalchemy import event

            engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
            event.listen(engine, "connect", _enable_sqlite_fk)
        _active_engine = engine
        return engine


def _run_migrations(engine) -> None:  # type: ignore[no-untyped-def]
    """Run Alembic migrations to HEAD, falling back to create_all for fresh DBs."""
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        with engine.begin() as conn:
            alembic_cfg.attributes["connection"] = conn
            command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception:
        # Fallback: if Alembic is unavailable or migrations fail (e.g. fresh DB
        # without alembic_version table), create tables directly and stamp HEAD.
        logger.warning("Alembic migration failed, falling back to create_all", exc_info=True)
        Base.metadata.create_all(engine)
        try:
            from alembic import command
            from alembic.config import Config

            alembic_cfg = Config("alembic.ini")
            command.stamp(alembic_cfg, "head")
            logger.info("Stamped database at Alembic HEAD after create_all fallback")
        except Exception:
            logger.warning("Could not stamp Alembic HEAD", exc_info=True)


def init_db() -> Session:
    """Initialise the database, with automatic failover on connection error.

    Tries the primary database first.  If it's unreachable and a failover
    URL is configured, retries against the failover.  Falls back to SQLite
    when no DATABASE_URL is set at all.

    Returns a new Session bound to the cached engine.
    """
    global _active_engine, _tables_created, _SessionFactory
    from sqlalchemy import text

    with _init_lock:
        for attempt_failover in (False, True):
            try:
                engine = get_engine(failover=attempt_failover)
                # Verify the connection is alive
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                if not _tables_created:
                    _run_migrations(engine)
                    _tables_created = True
                if _SessionFactory is None or _SessionFactory.kw.get("bind") is not engine:
                    _SessionFactory = sessionmaker(bind=engine)
                if attempt_failover:
                    logger.warning("Using failover database")
                return _SessionFactory()
            except (OperationalError, DBAPIError) as exc:
                if not attempt_failover and DATABASE_URL_FAILOVER:
                    logger.warning("Primary database unreachable, trying failover: %s", exc)
                    # Reset cached engine so failover creates a new one
                    _active_engine = None
                    _tables_created = False
                    _SessionFactory = None
                    continue
                raise
    # Unreachable, but satisfies the type checker
    raise RuntimeError("Database initialisation failed")
