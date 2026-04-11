"""Onboarding service -- AI-assisted profile creation."""

from __future__ import annotations

import logging
from typing import Any, cast

from anthropic.types import TextBlock

from config.settings import AGENT_MODEL
from src.llm_client import create_message_with_failover, get_llm_client
from src.utils import parse_json_response

logger = logging.getLogger(__name__)


class OnboardingService:
    """Generates onboarding content using LLM."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or get_llm_client()

    def generate_tasks_for_role(self, role: str) -> list[str]:
        """Return a list of common tasks for a given role title."""
        response = create_message_with_failover(
            self._client,
            model=AGENT_MODEL,
            max_tokens=1024,
            system="You are a career expert. Return a JSON array of 8-12 common daily tasks for the given job role. Return ONLY the JSON array, no other text.",
            messages=[{"role": "user", "content": f"What are the common daily tasks for a {role}?"}],
        )
        text = cast(TextBlock, response.content[0]).text
        result = parse_json_response(text)
        if isinstance(result, list):
            return [str(t) for t in result[:15]]
        return []

    def generate_skills_from_tasks(self, role: str, tasks: list[str]) -> list[str]:
        """Return skills relevant to the given role and selected tasks."""
        tasks_str = ", ".join(tasks[:15])
        response = create_message_with_failover(
            self._client,
            model=AGENT_MODEL,
            max_tokens=1024,
            system="You are a career expert. Return a JSON array of 10-20 relevant technical and soft skills based on the role and tasks. Return ONLY the JSON array.",
            messages=[{
                "role": "user",
                "content": f"Role: {role}\nTasks: {tasks_str}\n\nWhat skills are needed?",
            }],
        )
        text = cast(TextBlock, response.content[0]).text
        result = parse_json_response(text)
        if isinstance(result, list):
            return [str(s) for s in result[:25]]
        return []

    def generate_career_identity(
        self,
        name: str,
        skills: list[str],
        desired_roles: list[str],
        experience_level: str,
        interests: list[str] | None = None,
    ) -> str:
        """Generate a Career Identity Statement for the user's profile header."""
        response = create_message_with_failover(
            self._client,
            model=AGENT_MODEL,
            max_tokens=512,
            system=(
                "You are a career branding expert. Write a compelling 2-3 sentence Career Identity Statement "
                "for a job seeker. It should be professional, confident, and highlight their unique value. "
                "Return ONLY the statement text, no quotes or labels."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Name: {name}\n"
                    f"Experience Level: {experience_level}\n"
                    f"Key Skills: {', '.join(skills[:10])}\n"
                    f"Target Roles: {', '.join(desired_roles[:5])}\n"
                    f"Interests: {', '.join(interests[:5]) if interests else 'Not specified'}\n\n"
                    "Write a Career Identity Statement for this person."
                ),
            }],
        )
        return cast(TextBlock, response.content[0]).text.strip()
