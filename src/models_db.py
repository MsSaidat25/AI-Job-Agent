"""SQLAlchemy ORM models and PII encryption helpers.

Database bootstrap (engine, migrations, sessions) is in src/models_bootstrap.py.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

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
)
from sqlalchemy.orm import DeclarativeBase, relationship

from config.settings import ENCRYPT_USER_DATA
from src.models import (
    ApplicationStatus,
    ExperienceLevel,
    JobType,
    UserProfile,
)

logger = logging.getLogger(__name__)


# ���─ SQLAlchemy ORM ─────────────────────────────────────────────────────────

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
    career_identity_statement = Column(Text, nullable=True)
    preferred_locations = Column(JSON, nullable=True)
    remote_preference = Column(String(30), default="flexible")
    non_compete_companies = Column(JSON, nullable=True)
    interests = Column(JSON, nullable=True)
    firebase_uid = Column(String(128), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    applications = relationship("ApplicationRecordORM", back_populates="user")
    saved_jobs = relationship("SavedJobORM", back_populates="user")


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


class SavedJobORM(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (
        Index("ix_saved_jobs_user_job", "user_id", "job_id", unique=True),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    saved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserProfileORM", back_populates="saved_jobs")
    job = relationship("JobListingORM")


# ── Sprint 2 tables ───────────────────────────────────────────────────────


class DocumentVariantORM(Base):
    __tablename__ = "document_variants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("application_records.id", ondelete="SET NULL"), nullable=True, index=True)
    resume_content = Column(Text, nullable=True)
    cover_letter_content = Column(Text, nullable=True)
    resume_tone = Column(String(30), default="professional")
    ats_score = Column(Float, nullable=True)
    tailoring_notes = Column(Text, default="")
    status = Column(String(20), default="active")  # active, archived, winning
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Sprint 3 tables ───────────────────────────────────────────────────────


class DailyFeedORM(Base):
    __tablename__ = "daily_feeds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    jobs = Column(JSON)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    viewed = Column(Boolean, default=False)


class FollowUpScheduleORM(Base):
    __tablename__ = "follow_up_schedule"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("application_records.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_title = Column(String(500), default="")
    company = Column(String(300), default="")
    next_nudge_date = Column(DateTime, nullable=False, index=True)
    nudge_count = Column(Integer, default=0)
    nudge_type = Column(String(30), default="check_in")
    status = Column(String(20), default="active")  # active, paused, completed, archived
    last_response = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AutoApplySettingsORM(Base):
    __tablename__ = "auto_apply_settings"

    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), primary_key=True)
    enabled = Column(Boolean, default=False)
    confidence_threshold = Column(Float, default=0.85)
    safe_channels = Column(JSON, default=list)
    max_daily = Column(Integer, default=5)


class AutoApplyQueueORM(Base):
    __tablename__ = "auto_apply_queue"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    job_title = Column(String(500), default="")
    company = Column(String(300), default="")
    channel = Column(String(30), default="email")
    confidence_score = Column(Float, default=0.0)
    status = Column(String(20), default="queued")  # queued, approved, sent, rejected, failed
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmailOAuthTokenORM(Base):
    __tablename__ = "email_oauth_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    provider = Column(String(30), default="gmail")
    access_token_enc = Column(Text, nullable=True)
    refresh_token_enc = Column(Text, nullable=True)
    email_address = Column(String(500), nullable=True)
    scopes = Column(Text, default="")
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Sprint 5 tables ───────────────────────────────────────────────────────


class OfferORM(Base):
    __tablename__ = "offers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("job_listings.id", ondelete="SET NULL"), nullable=True)
    company = Column(String(300), nullable=False)
    role = Column(String(500), nullable=False)
    base_salary = Column(Integer, nullable=False)
    bonus = Column(Integer, nullable=True)
    equity = Column(String(200), nullable=True)
    benefits = Column(Text, default="")
    location = Column(String(200), default="")
    remote = Column(Boolean, default=False)
    status = Column(String(30), default="pending")  # pending, accepted, declined, expired
    deadline = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SavedSearchORM(Base):
    __tablename__ = "saved_searches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), default="")
    query = Column(Text, default="")
    filters = Column(JSON, default=dict)
    notify = Column(Boolean, default=True)
    frequency = Column(String(20), default="daily")
    last_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmployerWaitlistORM(Base):
    __tablename__ = "employer_waitlist"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(500), nullable=False, unique=True, index=True)
    company_name = Column(String(500), default="")
    company_size = Column(String(50), default="")
    signed_up_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── PII encryption helpers ─────────────────────────────────────────────

_ENCRYPTION_KEY: bytes | None = None
_ENCRYPTION_SALT: bytes | None = None


def _get_encryption_key() -> bytes:
    """Return (and cache) the PII encryption key derived from a passphrase."""
    global _ENCRYPTION_KEY, _ENCRYPTION_SALT
    if _ENCRYPTION_KEY is not None:
        return _ENCRYPTION_KEY
    import os
    from src.privacy import derive_key
    passphrase = os.environ.get("PII_ENCRYPTION_PASSPHRASE", "jobagent-default-dev-key")
    salt_hex = os.environ.get("PII_ENCRYPTION_SALT")
    salt = bytes.fromhex(salt_hex) if salt_hex else None
    _ENCRYPTION_KEY, _ENCRYPTION_SALT = derive_key(passphrase, salt)
    return _ENCRYPTION_KEY


def profile_to_orm(profile: UserProfile) -> UserProfileORM:
    """Convert a Pydantic UserProfile to ORM, encrypting PII if enabled."""
    name_val = profile.name
    email_val = profile.email
    phone_val = profile.phone

    if ENCRYPT_USER_DATA:
        from src.privacy import encrypt
        key = _get_encryption_key()
        name_val = encrypt(name_val, key)
        email_val = encrypt(email_val, key)
        if phone_val:
            phone_val = encrypt(phone_val, key)

    return UserProfileORM(
        id=profile.id,
        name_enc=name_val,
        email_enc=email_val,
        phone_enc=phone_val,
        location=profile.location,
        skills=profile.skills,
        experience_level=profile.experience_level.value,
        years_of_experience=profile.years_of_experience,
        education=profile.education,
        work_history=profile.work_history,
        desired_roles=profile.desired_roles,
        desired_job_types=[jt.value for jt in profile.desired_job_types],
        desired_salary_min=profile.desired_salary_min,
        desired_salary_max=profile.desired_salary_max,
        languages=profile.languages,
        certifications=profile.certifications,
        portfolio_url=profile.portfolio_url,
        linkedin_url=profile.linkedin_url,
        preferred_currency=profile.preferred_currency,
        career_identity_statement=profile.career_identity_statement,
        preferred_locations=profile.preferred_locations,
        remote_preference=profile.remote_preference,
        non_compete_companies=profile.non_compete_companies,
        interests=profile.interests,
        firebase_uid=profile.firebase_uid,
        created_at=profile.created_at,
    )


def orm_to_profile(orm: UserProfileORM) -> UserProfile:
    """Convert ORM row back to Pydantic, decrypting PII if enabled.

    Note: SQLAlchemy Column descriptors resolve to plain Python values at
    runtime, but pyright sees them as Column[T]. We cast through Any.
    """
    r: Any = orm  # bypass Column[T] vs T mismatch
    name_val: str = r.name_enc
    email_val: str = r.email_enc
    phone_val: str | None = r.phone_enc

    if ENCRYPT_USER_DATA:
        from src.privacy import decrypt
        key = _get_encryption_key()
        name_val = decrypt(name_val, key)
        email_val = decrypt(email_val, key)
        if phone_val:
            phone_val = decrypt(phone_val, key)

    return UserProfile(
        id=r.id,
        name=name_val,
        email=email_val,
        phone=phone_val,
        location=r.location,
        skills=r.skills or [],
        experience_level=ExperienceLevel(r.experience_level) if r.experience_level else ExperienceLevel.MID,
        years_of_experience=r.years_of_experience or 0,
        education=r.education or [],
        work_history=r.work_history or [],
        desired_roles=r.desired_roles or [],
        desired_job_types=[JobType(jt) for jt in (r.desired_job_types or [])],
        desired_salary_min=r.desired_salary_min,
        desired_salary_max=r.desired_salary_max,
        languages=r.languages or ["English"],
        certifications=r.certifications or [],
        portfolio_url=r.portfolio_url,
        linkedin_url=r.linkedin_url,
        preferred_currency=r.preferred_currency or "USD",
        career_identity_statement=r.career_identity_statement,
        preferred_locations=r.preferred_locations or [],
        remote_preference=r.remote_preference or "flexible",
        non_compete_companies=r.non_compete_companies or [],
        interests=r.interests or [],
        firebase_uid=r.firebase_uid,
    )


def reset_encryption_key() -> None:
    """Reset cached encryption key. Used by tests."""
    global _ENCRYPTION_KEY, _ENCRYPTION_SALT
    _ENCRYPTION_KEY = None
    _ENCRYPTION_SALT = None
