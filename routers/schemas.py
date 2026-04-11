"""Shared request/response schemas for the API."""

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
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
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


# ── Auth schemas ──────────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(..., max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=1, max_length=4096)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=2048)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    id_token: str = Field(..., min_length=1, max_length=4096)
    new_password: str = Field(..., min_length=6, max_length=128)


class ChangePasswordResponse(BaseModel):
    message: str


class AuthResponse(BaseModel):
    id_token: str
    refresh_token: str
    user_id: str
    expires_in: int


# ── Onboarding schemas ────────────────────────────────────────────────────────


class GenerateTasksRequest(BaseModel):
    role: str = Field(..., max_length=200)


class GenerateTasksResponse(BaseModel):
    tasks: list[str]
    role: str


class GenerateSkillsRequest(BaseModel):
    role: str = Field(..., max_length=200)
    selected_tasks: list[str] = Field(..., max_length=50)


class GenerateSkillsResponse(BaseModel):
    skills: list[str]


class GenerateIdentityRequest(BaseModel):
    name: str = Field(..., max_length=200)
    skills: list[str] = Field(default_factory=list)
    desired_roles: list[str] = Field(default_factory=list)
    experience_level: ExperienceLevel = ExperienceLevel.MID
    interests: list[str] = Field(default_factory=list)


class GenerateIdentityResponse(BaseModel):
    statement: str
    label: str = "STARTER DRAFT"


class ConfirmProfileRequest(ProfileRequest):
    career_identity_statement: Optional[str] = None
    preferred_locations: list[str] = Field(default_factory=list)
    remote_preference: str = Field(default="flexible", max_length=30)
    non_compete_companies: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


# ── Enhanced Job Search schemas ───────────────────────────────────────────────


class JobSearchRequestV2(BaseModel):
    location_filter: str = Field(default="", max_length=200)
    include_remote: bool = True
    max_results: int = Field(default=10, ge=1, le=50)
    job_type: Optional[str] = Field(default=None, max_length=50)
    experience_level: Optional[str] = Field(default=None, max_length=50)
    salary_min: Optional[int] = Field(default=None, ge=0)
    salary_max: Optional[int] = Field(default=None, ge=0)
    date_posted: Optional[str] = Field(default=None, max_length=20)
    sort_by: str = Field(default="relevance", pattern="^(relevance|date|salary)$")
    page: int = Field(default=1, ge=1)


class JobDetailResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str
    remote_allowed: bool = False
    job_type: str = "full_time"
    experience_level: str = "mid"
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    posted_date: Optional[str] = None
    source_url: str = ""
    source_platform: str = ""
    match_score: Optional[float] = None
    match_rationale: Optional[str] = None
    is_saved: bool = False


class JobSearchResponseV2(BaseModel):
    jobs: list[JobDetailResponse]
    total: int
    page: int
    has_more: bool


class SaveJobResponse(BaseModel):
    message: str
    job_id: str
    saved: bool


class SavedJobListResponse(BaseModel):
    jobs: list[JobDetailResponse]
    total: int


# ── Job Import schema (Chrome extension) ─────────────────────────────────────


class JobImportRequest(BaseModel):
    title: str = Field(..., max_length=500)
    company: str = Field(..., max_length=300)
    location: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=10000)
    salary_text: Optional[str] = Field(default=None, max_length=200)
    source_url: str = Field(default="", max_length=2000)
    source_platform: str = Field(default="", max_length=100)


class JobImportResponse(BaseModel):
    job_id: str
    title: str
    company: str
    is_duplicate: bool = False
