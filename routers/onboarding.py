"""Onboarding endpoints: resume upload, conversational wizard, identity statement."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request
from slowapi import Limiter

from routers.schemas import (
    ConfirmProfileRequest,
    GenerateIdentityRequest,
    GenerateIdentityResponse,
    GenerateSkillsRequest,
    GenerateSkillsResponse,
    GenerateTasksRequest,
    GenerateTasksResponse,
    ProfileResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    session_dep: Any,
) -> None:
    from src.agent import JobAgent
    from src.models import UserProfile, init_db, profile_to_orm
    from src.onboarding_service import OnboardingService
    from src.session_store import set_session_agent

    _svc = OnboardingService()

    @router.post("/generate-tasks", response_model=GenerateTasksResponse)
    @limiter.limit("15/minute")
    async def generate_tasks(request: Request, body: GenerateTasksRequest):
        """Generate common tasks for a role (onboarding step 2)."""
        tasks = await asyncio.to_thread(_svc.generate_tasks_for_role, body.role)
        return GenerateTasksResponse(tasks=tasks, role=body.role)

    @router.post("/generate-skills", response_model=GenerateSkillsResponse)
    @limiter.limit("15/minute")
    async def generate_skills(request: Request, body: GenerateSkillsRequest):
        """Generate skills from role + selected tasks (onboarding step 3)."""
        skills = await asyncio.to_thread(
            _svc.generate_skills_from_tasks, body.role, body.selected_tasks,
        )
        return GenerateSkillsResponse(skills=skills)

    @router.post("/generate-identity-statement", response_model=GenerateIdentityResponse)
    @limiter.limit("10/minute")
    async def generate_identity(request: Request, body: GenerateIdentityRequest):
        """Generate a Career Identity Statement (onboarding step 5)."""
        statement = await asyncio.to_thread(
            _svc.generate_career_identity,
            body.name,
            body.skills,
            body.desired_roles,
            body.experience_level.value,
            body.interests,
        )
        return GenerateIdentityResponse(statement=statement)

    @router.post("/confirm-profile", response_model=ProfileResponse, status_code=201)
    @limiter.limit("10/minute")
    async def confirm_profile(
        request: Request,
        body: ConfirmProfileRequest,
        session_id: str = session_dep,
    ):
        """Finalize profile after onboarding wizard, persist to DB, create agent."""
        profile = UserProfile(
            name=body.name,
            email=body.email,
            phone=body.phone,
            location=body.location,
            skills=body.skills,
            experience_level=body.experience_level,
            years_of_experience=body.years_of_experience,
            education=body.education,
            work_history=body.work_history,
            desired_roles=body.desired_roles,
            desired_job_types=body.desired_job_types,
            desired_salary_min=body.desired_salary_min,
            desired_salary_max=body.desired_salary_max,
            languages=body.languages,
            certifications=body.certifications,
            portfolio_url=body.portfolio_url,
            linkedin_url=body.linkedin_url,
            preferred_currency=body.preferred_currency,
            career_identity_statement=body.career_identity_statement,
            preferred_locations=body.preferred_locations,
            remote_preference=body.remote_preference,
            non_compete_companies=body.non_compete_companies,
            interests=body.interests,
        )

        # Persist to DB
        db = init_db()
        try:
            orm_obj = profile_to_orm(profile)
            db.merge(orm_obj)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist profile")
        finally:
            db.close()

        agent = JobAgent(profile=profile)
        set_session_agent(session_id, agent, profile)
        return ProfileResponse(
            profile_id=profile.id,
            message="Profile created and agent initialised.",
            currency=body.preferred_currency,
        )
