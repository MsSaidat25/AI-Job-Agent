"""Rejection Restrategizer -- pattern detection and actionable advice from rejections."""

import logging
from typing import Any, cast

from anthropic.types import TextBlock
from pydantic import BaseModel, Field

from config.settings import AGENT_MODEL
from src.llm_client import create_message_with_failover, get_llm_client
from src.utils import parse_json_response

logger = logging.getLogger(__name__)


class RejectionPattern(BaseModel):
    pattern_type: str = ""  # company_type, role_level, industry, timing
    description: str = ""
    frequency: int = 0
    examples: list[str] = Field(default_factory=list)


class ResumeAdjustment(BaseModel):
    area: str = ""
    current: str = ""
    suggested: str = ""
    rationale: str = ""


class RestrategizerAdvice(BaseModel):
    patterns: list[RejectionPattern] = Field(default_factory=list)
    advice: list[str] = Field(default_factory=list)
    adjustments: list[ResumeAdjustment] = Field(default_factory=list)
    pivot_suggestions: list[str] = Field(default_factory=list)
    encouragement: str = ""


class RejectionRestrategizer:
    """Analyzes rejection patterns and generates actionable restrategizing advice."""

    def __init__(self, client: Any = None) -> None:
        self._client = client or get_llm_client()

    def detect_patterns(
        self, rejections: list[dict[str, Any]],
    ) -> list[RejectionPattern]:
        """Detect patterns across rejections."""
        if len(rejections) < 3:
            return []

        try:
            rej_summary = "\n".join(
                f"- {r.get('job_title', 'Unknown')} at {r.get('company', 'Unknown')} "
                f"(industry: {r.get('industry', 'unknown')}, level: {r.get('experience_level', 'unknown')})"
                for r in rejections[:20]
            )
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=1024,
                system=(
                    "Analyze these job rejections for patterns. Return JSON array of objects with: "
                    "pattern_type (company_type/role_level/industry/timing), description, "
                    "frequency (count), examples (array of specific jobs). "
                    "Look for common themes: company sizes, role levels, industries, timing patterns."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Rejected applications:\n{rej_summary}",
                }],
            )
            text = cast(TextBlock, response.content[0]).text
            result = parse_json_response(text)
            if isinstance(result, list):
                return [RejectionPattern(**p) for p in result]
        except Exception:
            logger.warning("Pattern detection failed", exc_info=True)
        return []

    def generate_advice(
        self, patterns: list[RejectionPattern], profile_summary: str,
    ) -> RestrategizerAdvice:
        """Generate actionable advice based on rejection patterns."""
        if not patterns:
            return RestrategizerAdvice(
                encouragement="Keep applying! It's too early to see patterns.",
            )

        try:
            patterns_text = "\n".join(
                f"- {p.pattern_type}: {p.description} ({p.frequency}x)"
                for p in patterns
            )
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=1500,
                system=(
                    "You are a career strategist. Based on rejection patterns, provide advice. "
                    "Return JSON with: advice (array of actionable tips), "
                    "adjustments (array of {area, current, suggested, rationale}), "
                    "pivot_suggestions (array of alternative roles/strategies), "
                    "encouragement (string, be constructive, never discouraging). "
                    "Be specific and sector-aware."
                ),
                messages=[{
                    "role": "user",
                    "content": (
                        f"Profile: {profile_summary}\n\n"
                        f"Rejection Patterns:\n{patterns_text}"
                    ),
                }],
            )
            text = cast(TextBlock, response.content[0]).text
            result = parse_json_response(text)
            if isinstance(result, dict):
                advice = RestrategizerAdvice(**result)
                advice.patterns = patterns
                return advice
        except Exception:
            logger.warning("Advice generation failed", exc_info=True)

        return RestrategizerAdvice(
            patterns=patterns,
            encouragement="Patterns detected but advice generation had an issue. Review the patterns manually.",
        )
