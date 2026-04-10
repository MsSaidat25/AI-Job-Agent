"""Shared request/response schemas for the API."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.models import ApplicationStatus, ExperienceLevel, JobType

_ALLOWED_TONES = {"professional", "creative", "technical", "executive", "academic"}


# ── Request schemas ──────────────────────────────────────────────────────────


class ProfileRequest(BaseModel):
    name: str = Field(..., max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    location: str = Field(..., max_length=200)
    skills: list[str] = Field(default_factory=list, max_length=100)
    experience_level: ExperienceLevel = ExperienceLevel.MID
    years_of_experience: int = Field(default=0, ge=0, le=70)
    education: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    work_history: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    desired_roles: list[str] = Field(default_factory=list, max_length=20)
    desired_job_types: list[JobType] = Field(default_factory=list, max_length=10)
    preferred_currency: str = Field(default="USD", max_length=5)
    desired_salary_min: Optional[int] = Field(default=None, ge=0)
    desired_salary_max: Optional[int] = Field(default=None, ge=0)
    languages: list[str] = Field(default=["English"], max_length=30)
    certifications: list[str] = Field(default_factory=list, max_length=50)
    portfolio_url: Optional[str] = Field(default=None, max_length=500)
    linkedin_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("portfolio_url", "linkedin_url", mode="before")
    @classmethod
    def validate_urls(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith(("https://", "http://")):
            raise ValueError("URL must start with https:// or http://")
        return v


class JobSearchRequest(BaseModel):
    location_filter: str = Field(default="", max_length=200)
    include_remote: bool = True
    max_results: int = Field(default=10, ge=1, le=50)


class MarketInsightsRequest(BaseModel):
    region: str = Field(..., max_length=200)
    industry: str = Field(..., max_length=200)


class ApplicationTipsRequest(BaseModel):
    region: str = Field(..., max_length=200)


class ResumeRequest(BaseModel):
    job_id: str = Field(..., max_length=200)
    tone: str = "professional"

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        if v.lower() not in _ALLOWED_TONES:
            raise ValueError(f"tone must be one of: {', '.join(sorted(_ALLOWED_TONES))}")
        return v.lower()


class CoverLetterRequest(BaseModel):
    job_id: str = Field(..., max_length=200)


class TrackApplicationRequest(BaseModel):
    job_id: str = Field(..., max_length=200)
    notes: str = Field(default="", max_length=2000)


class UpdateApplicationRequest(BaseModel):
    new_status: ApplicationStatus
    feedback: Optional[str] = Field(default=None, max_length=5000)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=5000)


class EmployerWaitlistRequest(BaseModel):
    email: EmailStr
    company_name: str = Field(default="", max_length=200)
    company_size: str = Field(default="", max_length=50)


# ── Response schemas ─────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    sessions: int
    db: str
    llm_configured: bool


class EmployerWaitlistResponse(BaseModel):
    message: str
    position: int


class SessionResponse(BaseModel):
    session_id: str


class ProfileResponse(BaseModel):
    profile_id: str
    message: str
    currency: str


class JobSearchResponse(BaseModel):
    response: str
    job_ids: list[str]
    job_cache_size: int


class AgentResponse(BaseModel):
    response: str


class ResumeParseResponse(BaseModel):
    name: str = ""
    email: str = ""
    phone: Optional[str] = None
    location: str = ""
    experience_level: str = "mid"
    years_of_experience: int = 0
    skills: list[str] = Field(default_factory=list)
    desired_roles: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
