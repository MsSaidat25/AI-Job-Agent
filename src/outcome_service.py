"""Outcome Learning Service -- correlate resume variants with callback rates."""

import logging
from typing import Any, Optional, cast

from anthropic.types import TextBlock
from pydantic import BaseModel, Field

from config.settings import AGENT_MODEL
from src.llm_client import create_message_with_failover, get_llm_client

logger = logging.getLogger(__name__)


class VariantInsight(BaseModel):
    variant_id: str = ""
    tone: str = ""
    job_type: str = ""
    result: str = ""  # callback, rejection, no_response
    keywords_used: list[str] = Field(default_factory=list)
    score: Optional[float] = None


class WinningPatterns(BaseModel):
    best_tones: list[str] = Field(default_factory=list)
    best_keywords: list[str] = Field(default_factory=list)
    best_formats: list[str] = Field(default_factory=list)
    callback_rate_by_tone: dict[str, float] = Field(default_factory=dict)
    top_performing_sectors: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


class OutcomeLearningService:
    """Learns from application outcomes to improve future applications."""

    def __init__(self, client: Any = None) -> None:
        self._client = client or get_llm_client()

    def correlate_variants(
        self, applications: list[dict[str, Any]], variants: list[dict[str, Any]],
    ) -> list[VariantInsight]:
        """Correlate document variants with application outcomes."""
        insights: list[VariantInsight] = []
        for app in applications:
            status = app.get("status", "")
            result = "no_response"
            if status in ("interview_scheduled", "offer_received"):
                result = "callback"
            elif status == "rejected":
                result = "rejection"

            # Find matching variant
            app_id = app.get("id", "")
            matching_variant = next(
                (v for v in variants if v.get("application_id") == app_id), None,
            )
            if matching_variant:
                insights.append(VariantInsight(
                    variant_id=matching_variant.get("id", ""),
                    tone=matching_variant.get("resume_tone", ""),
                    result=result,
                    score=matching_variant.get("ats_score"),
                ))

        return insights

    def get_winning_patterns(
        self, insights: list[VariantInsight],
    ) -> WinningPatterns:
        """Analyze patterns from variant insights to find winning strategies."""
        if not insights:
            return WinningPatterns(insights=["Not enough data yet. Apply to more jobs to see patterns."])

        # Calculate callback rate by tone
        tone_counts: dict[str, dict[str, int]] = {}
        for ins in insights:
            if ins.tone not in tone_counts:
                tone_counts[ins.tone] = {"total": 0, "callbacks": 0}
            tone_counts[ins.tone]["total"] += 1
            if ins.result == "callback":
                tone_counts[ins.tone]["callbacks"] += 1

        callback_rates = {
            tone: counts["callbacks"] / max(counts["total"], 1)
            for tone, counts in tone_counts.items()
        }

        best_tones = sorted(callback_rates, key=callback_rates.get, reverse=True)  # type: ignore[arg-type]

        return WinningPatterns(
            best_tones=best_tones[:3],
            callback_rate_by_tone=callback_rates,
            insights=[
                f"Your {best_tones[0]} tone resumes perform best" if best_tones else "Keep applying to build data",
                f"Callback rate: {max(callback_rates.values()) * 100:.0f}% for best tone" if callback_rates else "",
            ],
        )

    def generate_insights(
        self, applications: list[dict[str, Any]], variants: list[dict[str, Any]],
    ) -> str:
        """Generate AI-powered outcome insights."""
        if len(applications) < 3:
            return "Need at least 3 applications to generate insights. Keep applying!"

        try:
            apps_summary = "\n".join(
                f"- {a.get('job_title', 'Unknown')} at {a.get('company', 'Unknown')}: {a.get('status', 'unknown')}"
                for a in applications[:20]
            )
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=1024,
                system=(
                    "You are a career strategist analyzing application outcomes. "
                    "Provide actionable insights about what's working and what's not. "
                    "Be specific and constructive. Focus on patterns, not individual applications."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Application history:\n{apps_summary}",
                }],
            )
            return cast(TextBlock, response.content[0]).text.strip()
        except Exception:
            logger.warning("Insight generation failed", exc_info=True)
            return "Unable to generate insights at this time."
