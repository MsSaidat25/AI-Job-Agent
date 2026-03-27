# Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com). All Rights Reserved.
# avien@aviensolutions.com
"""
Career Dreamer -- "What if?" career exploration powered by AI.

Lets users explore dream career transitions with gap analysis,
feasibility scoring, and week-by-week actionable timelines.
"""
from __future__ import annotations

import json
import logging
from typing import cast

from anthropic import Anthropic
from anthropic.types import TextBlock

from config.settings import AGENT_MODEL, MAX_TOKENS
from src.llm_client import create_message_with_failover, get_llm_client
from src.models import DreamScenario, DreamTimeline, GapReport, UserProfile
from src.utils import parse_json_response as _parse_json_response

logger = logging.getLogger(__name__)


class CareerDreamer:
    """AI-powered career transition analysis and planning."""

    def __init__(self, client: Anthropic | None = None) -> None:
        self._client = client or get_llm_client()

    def build_gap_report(
        self,
        profile: UserProfile,
        dream: DreamScenario,
    ) -> GapReport:
        """Analyse the gap between the user's current profile and their dream role."""
        prompt = f"""Analyse the career gap between this person's current profile and their dream role.

=== CURRENT PROFILE ===
Skills: {", ".join(profile.skills)}
Experience level: {profile.experience_level.value} ({profile.years_of_experience} years)
Current/desired roles: {", ".join(profile.desired_roles)}
Location: {profile.location}
Education: {json.dumps(profile.education) if profile.education else "Not specified"}
Certifications: {", ".join(profile.certifications) if profile.certifications else "None"}

=== DREAM ROLE ===
Role: {dream.dream_role}
Industry: {dream.dream_industry or "Any"}
Location: {dream.dream_location or profile.location}
Timeline: {dream.timeline_months} months

Return ONLY valid JSON with these keys:
- "overlapping_skills": list of skills the person already has that are relevant
- "missing_skills": list of objects with "skill", "learning_time_weeks" (int), "priority" ("high"/"medium"/"low")
- "salary_current": estimated current salary (int, USD) based on their profile, or null
- "salary_dream": estimated salary for the dream role (int, USD), or null
- "feasibility_score": 0-100 how feasible this transition is in the given timeline
- "feasibility_rationale": 1-2 sentence explanation
- "recommendations": list of 3-5 actionable next steps
"""
        try:
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                system="You are an expert career transition coach. Respond ONLY with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = cast(TextBlock, response.content[0]).text
            data = _parse_json_response(text)

            feasibility = max(0.0, min(100.0, float(data.get("feasibility_score", 0))))

            return GapReport(
                dream_role=dream.dream_role,
                overlapping_skills=data.get("overlapping_skills", []),
                missing_skills=data.get("missing_skills", []),
                salary_current=data.get("salary_current"),
                salary_dream=data.get("salary_dream"),
                feasibility_score=feasibility,
                feasibility_rationale=data.get("feasibility_rationale", ""),
                recommendations=data.get("recommendations", []),
            )
        except Exception:
            logger.exception("Failed to build gap report for %s", dream.dream_role)
            return GapReport(
                dream_role=dream.dream_role,
                feasibility_score=0.0,
                feasibility_rationale="Unable to analyse at this time. Please try again.",
            )

    def score_feasibility(self, gap_report: GapReport) -> float:
        """Return the feasibility score (0-100) from an existing gap report.

        If the gap report was built with build_gap_report(), the score is
        already computed. This method exists for standalone re-scoring.
        """
        if gap_report.feasibility_score > 0:
            return gap_report.feasibility_score

        prompt = f"""Score the feasibility (0-100) of this career transition.

Dream role: {gap_report.dream_role}
Overlapping skills: {", ".join(gap_report.overlapping_skills)}
Missing skills: {len(gap_report.missing_skills)} skills needed
Salary jump: {gap_report.salary_current} -> {gap_report.salary_dream}

Return ONLY valid JSON: {{"feasibility_score": <int>, "rationale": "<reason>"}}
"""
        try:
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=256,
                system="You are a career feasibility analyst. Respond ONLY with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = cast(TextBlock, response.content[0]).text
            data = _parse_json_response(text)
            return max(0.0, min(100.0, float(data.get("feasibility_score", 0))))
        except Exception:
            logger.exception("Failed to score feasibility")
            return 0.0

    def build_timeline(
        self,
        gap_report: GapReport,
        months: int = 12,
    ) -> DreamTimeline:
        """Build a week-by-week plan to achieve the dream role."""
        if not gap_report.missing_skills and not gap_report.recommendations:
            return DreamTimeline(
                dream_role=gap_report.dream_role,
                total_weeks=0,
                milestones=[{"week": 1, "goal": "You already have the skills!", "actions": [], "deliverable": "Apply directly"}],
            )

        total_weeks = months * 4
        missing_summary = json.dumps(gap_report.missing_skills[:10]) if gap_report.missing_skills else "None identified"

        prompt = f"""Create a week-by-week career transition plan.

Dream role: {gap_report.dream_role}
Total weeks available: {total_weeks}
Missing skills to learn: {missing_summary}
Recommendations: {json.dumps(gap_report.recommendations)}
Current overlapping skills: {", ".join(gap_report.overlapping_skills[:10])}

Return ONLY valid JSON with:
- "milestones": list of objects, each with:
  - "week": int (the week number or range start)
  - "goal": short description of the milestone
  - "actions": list of 2-3 specific actions
  - "deliverable": what should be completed by this milestone

Create 6-10 milestones spread across the timeline. Group weeks logically.
"""
        try:
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                system="You are a career transition planner. Respond ONLY with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = cast(TextBlock, response.content[0]).text
            data = _parse_json_response(text)

            return DreamTimeline(
                dream_role=gap_report.dream_role,
                total_weeks=total_weeks,
                milestones=data.get("milestones", []),
            )
        except Exception:
            logger.exception("Failed to build timeline for %s", gap_report.dream_role)
            return DreamTimeline(
                dream_role=gap_report.dream_role,
                total_weeks=total_weeks,
                milestones=[],
            )
