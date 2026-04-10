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

AI Job Agent — Main Orchestrator.

This module wires together every sub-system and exposes a single
`JobAgent` class that the UI layer interacts with.

Agent loop (tool-use pattern)
──────────────────────────────
The agent runs an agentic loop using Anthropic's tool-use API:

  1. User sends a natural-language request.
  2. Claude decides which tool(s) to call.
  3. The orchestrator executes the tools and feeds results back.
  4. Loop continues until Claude returns a final text response.

Tools exposed to the model
──────────────────────────
• search_jobs          – find matching listings
• get_market_insights  – regional job market report
• get_application_tips – culturally-aware advice for a region
• generate_resume      – tailored resume for a specific job
• generate_cover_letter– tailored cover letter
• track_application    – log a new application
• update_application   – update status / add feedback
• get_analytics        – compute success metrics
• get_feedback_analysis– analyse employer feedback patterns
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, cast

from anthropic.types import TextBlock

from config.settings import AGENT_MODEL, MAX_TOKENS
from src.llm_client import create_message_with_failover, get_llm_client
from src.analytics import ApplicationTracker
from src.career_dreamer import CareerDreamer
from src.document_generator import DocumentGenerator
from src.job_search import JobSearchEngine, MarketIntelligenceService
from src.models import (
    ApplicationRecord,
    ApplicationStatus,
    DreamScenario,
    UserProfile,
    init_db,
)

logger = logging.getLogger(__name__)


# ── Tool schemas (JSON Schema for Claude's tool-use API) ───────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_jobs",
        "description": (
            "Search for job listings that match the user's profile. "
            "Returns a ranked list of opportunities with match scores."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location_filter": {
                    "type": "string",
                    "description": "Optional region filter, e.g. 'Austin, TX'. Pass empty string for global.",
                },
                "include_remote": {
                    "type": "boolean",
                    "description": "Whether to include remote opportunities.",
                    "default": True,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 10).",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_market_insights",
        "description": "Get a detailed job market report for a specific region and industry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Geographic region, e.g. 'Berlin, Germany'"},
                "industry": {"type": "string", "description": "Industry sector, e.g. 'Technology'"},
            },
            "required": ["region", "industry"],
        },
    },
    {
        "name": "get_application_tips",
        "description": "Get culturally-aware job application tips for a specific region.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Geographic region, e.g. 'Japan'"},
            },
            "required": ["region"],
        },
    },
    {
        "name": "generate_resume",
        "description": "Generate a tailored resume for a specific job listing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "ID of the target job listing."},
                "tone": {
                    "type": "string",
                    "enum": ["professional", "creative", "technical", "executive", "academic"],
                    "description": "Desired tone of the resume.",
                    "default": "professional",
                },
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "generate_cover_letter",
        "description": "Generate a tailored cover letter for a specific job listing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "ID of the target job listing."},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "track_application",
        "description": "Log a new job application in the tracker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "ID of the job applied to."},
                "notes": {"type": "string", "description": "Optional notes about this application."},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "update_application",
        "description": "Update the status or feedback for an existing application.",
        "input_schema": {
            "type": "object",
            "properties": {
                "application_id": {"type": "string"},
                "new_status": {
                    "type": "string",
                    "enum": [s.value for s in ApplicationStatus],
                },
                "feedback": {"type": "string", "description": "Employer feedback, if any."},
                "notes": {"type": "string"},
            },
            "required": ["application_id", "new_status"],
        },
    },
    {
        "name": "list_applications",
        "description": (
            "List all tracked job applications with their current status, dates, and notes. "
            "Use this when the user wants to see their application history or check the status "
            "of a specific application."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_analytics",
        "description": "Get application success metrics and AI-generated career insights.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_feedback_analysis",
        "description": "Analyse patterns across all employer feedback received.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "career_dreamer",
        "description": (
            "Explore a dream career transition. Analyses skill gaps, scores feasibility, "
            "and builds a week-by-week plan to reach the dream role."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dream_role": {"type": "string", "description": "The dream job title, e.g. 'Machine Learning Engineer'"},
                "dream_industry": {"type": "string", "description": "Target industry, e.g. 'AI/ML'", "default": ""},
                "dream_location": {"type": "string", "description": "Target location, e.g. 'San Francisco, CA'", "default": ""},
                "timeline_months": {"type": "integer", "description": "Months to achieve the transition (default 12)", "default": 12},
            },
            "required": ["dream_role"],
        },
    },
    {
        "name": "analyze_skill_gaps",
        "description": (
            "Analyse skill gaps by comparing the user's profile against live job postings. "
            "Returns must-have gaps, nice-to-have gaps, hidden strengths, and upskill ROI."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Region to search jobs in, e.g. 'Berlin, Germany'", "default": ""},
            },
            "required": [],
        },
    },
    {
        "name": "score_ats_match",
        "description": (
            "Score how well a resume matches a job description for ATS (Applicant Tracking System) compatibility. "
            "Returns match percentage, missing keywords, and improvement suggestions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "ID of the job listing to score against."},
                "resume_text": {"type": "string", "description": "The resume text to score. If omitted, uses the last generated resume.", "default": ""},
            },
            "required": ["job_id"],
        },
    },
]


# ── Agent System Prompt ────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert AI Job Application Agent helping a job seeker
navigate the global job market.

Your capabilities:
• Search and rank job listings based on the user's skills and preferences
• Provide region-specific market intelligence and application tips
• Generate tailored resumes and cover letters for specific roles
• Score resumes for ATS (Applicant Tracking System) compatibility
• Analyse skill gaps against live job postings
• Explore dream career transitions with gap analysis and timelines
• Track application progress and analyse success patterns
• Offer unbiased, skill-based recommendations

Principles you ALWAYS follow:
1. Never discriminate or make recommendations based on protected attributes.
2. Be honest about fit: if a role is a stretch, say so constructively.
3. Respect user privacy: never repeat PII unnecessarily in conversation.
4. Be concise and actionable in your responses.
5. When you call a tool, explain to the user what you're doing and why.

After tool results arrive, synthesise them into clear, human-readable advice.
"""


# ── Main Agent Class ───────────────────────────────────────────────────────

class JobAgent:
    """
    Orchestrates the full job-application workflow via an agentic loop.

    Usage
    ─────
        agent = JobAgent(profile=user_profile)
        response = agent.chat("Find me senior Python jobs in Berlin")
        print(response)
    """

    def __init__(self, profile: UserProfile) -> None:
        self.profile = profile
        self._client = get_llm_client()
        self._session = init_db()
        self._search_engine = JobSearchEngine(self._client)
        self._market_svc = MarketIntelligenceService(self._client)
        self._doc_gen = DocumentGenerator(self._client)
        self._tracker = ApplicationTracker(self._session, self._client)
        self._career_dreamer = CareerDreamer(self._client)

        # In-memory caches for the current session
        # Values may be JobListing (from agent tool loop) or raw dicts (from api.py live search)
        self._job_cache: dict[str, Any] = {}
        self._job_cache_max = 200  # Prevent unbounded memory growth
        self._app_cache: dict[str, ApplicationRecord] = {}

        # Conversation history (capped to prevent unbounded memory growth)
        self._messages: list[dict[str, Any]] = []
        self._max_history = 50

    # ── Public API ─────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying database session to release connections."""
        if self._session:
            self._session.close()

    def chat(self, user_message: str) -> str:
        """
        Send a message to the agent and get a response.
        Runs the agentic tool-use loop internally.
        """
        self._messages.append({"role": "user", "content": user_message})
        # Trim history to prevent unbounded memory growth (keep first message for context)
        if len(self._messages) > self._max_history:
            self._messages = self._messages[:1] + self._messages[-(self._max_history - 1):]
        return self._agent_loop()

    def reset_conversation(self) -> None:
        """Clear conversation history (profile and caches persist)."""
        self._messages = []

    # ── Agentic loop ───────────────────────────────────────────────────────

    def _agent_loop(self, max_turns: int = 20) -> str:
        """Run Claude tool-use loop until a final text response is produced."""
        for _turn in range(max_turns):
            response = create_message_with_failover(
                self._client,
                model=AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                tools=cast(Any, TOOLS),
                messages=cast(Any, self._messages),
            )

            # Append assistant turn to history
            self._messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Extract the text response
                for block in response.content:
                    if isinstance(block, TextBlock):
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._dispatch_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                self._messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason
                break

        return "I reached the maximum number of processing steps. Please try a simpler request."

    # ── Tool dispatcher ────────────────────────────────────────────────────

    def _dispatch_tool(self, name: str, args: dict[str, Any]) -> str:
        try:
            if name == "search_jobs":
                return self._tool_search_jobs(**args)
            elif name == "get_market_insights":
                return self._tool_market_insights(**args)
            elif name == "get_application_tips":
                return self._tool_application_tips(**args)
            elif name == "generate_resume":
                return self._tool_generate_resume(**args)
            elif name == "generate_cover_letter":
                return self._tool_generate_cover_letter(**args)
            elif name == "track_application":
                return self._tool_track_application(**args)
            elif name == "update_application":
                return self._tool_update_application(**args)
            elif name == "list_applications":
                return self._tool_list_applications()
            elif name == "get_analytics":
                return self._tool_get_analytics()
            elif name == "get_feedback_analysis":
                return self._tool_feedback_analysis()
            elif name == "career_dreamer":
                return self._tool_career_dreamer(**args)
            elif name == "analyze_skill_gaps":
                return self._tool_analyze_skill_gaps(**args)
            elif name == "score_ats_match":
                return self._tool_score_ats_match(**args)
            else:
                return json.dumps({"error": f"Unknown tool: {name}"})
        except Exception:
            logger.exception("Tool %s failed", name)
            return json.dumps({"error": f"Tool '{name}' encountered an internal error."})

    # ── Tool implementations ───────────────────────────────────────────────

    def _tool_search_jobs(
        self,
        location_filter: str = "",
        include_remote: bool = True,
        max_results: int = 10,
    ) -> str:
        listings = self._search_engine.search(self.profile, max_results=max_results)
        if location_filter:
            listings = self._search_engine.filter_by_location(
                listings, location_filter, include_remote
            )
        # Cache for downstream tools (evict oldest if over cap)
        for j in listings:
            if len(self._job_cache) >= self._job_cache_max:
                oldest_key = next(iter(self._job_cache))
                del self._job_cache[oldest_key]
            self._job_cache[j.id] = j
        return json.dumps(
            [
                {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "remote": j.remote_allowed,
                    "salary": f"{j.currency} {j.salary_min}–{j.salary_max}"
                    if j.salary_min
                    else "Not disclosed",
                    "match_score": j.match_score,
                    "match_rationale": j.match_rationale,
                    "source": j.source_platform,
                    "url": j.source_url,
                }
                for j in listings
            ],
            indent=2,
        )

    def _tool_market_insights(self, region: str, industry: str) -> str:
        insight = self._market_svc.get_insights(region, industry)
        return json.dumps(insight.model_dump(mode="json"), indent=2)

    def _tool_application_tips(self, region: str) -> str:
        tips = self._market_svc.get_application_tips(region)
        return tips

    _ALLOWED_TONES = {"professional", "creative", "technical", "executive", "academic"}

    def _tool_generate_resume(self, job_id: str, tone: str = "professional") -> str:
        if tone not in self._ALLOWED_TONES:
            tone = "professional"
        job = self._job_cache.get(job_id)
        if not job:
            return json.dumps({"error": "Job not found in current session. Run search_jobs first."})
        doc = self._doc_gen.generate_resume(self.profile, job, tone)
        return json.dumps({
            "document_id": doc.id,
            "doc_type": doc.doc_type,
            "content": doc.content,
            "tailoring_notes": doc.tailoring_notes,
        })

    def _tool_generate_cover_letter(self, job_id: str) -> str:
        job = self._job_cache.get(job_id)
        if not job:
            return json.dumps({"error": "Job not found. Run search_jobs first."})
        doc = self._doc_gen.generate_cover_letter(self.profile, job)
        return json.dumps({
            "document_id": doc.id,
            "doc_type": doc.doc_type,
            "content": doc.content,
            "tailoring_notes": doc.tailoring_notes,
        })

    def _tool_track_application(self, job_id: str, notes: str = "") -> str:
        record = ApplicationRecord(
            id=str(uuid.uuid4()),
            user_id=self.profile.id,
            job_id=job_id,
            status=ApplicationStatus.SUBMITTED,
            submitted_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            notes=notes,
        )
        self._tracker.add_application(record)
        self._app_cache[record.id] = record
        return json.dumps({"application_id": record.id, "status": record.status.value})

    def _tool_update_application(
        self,
        application_id: str,
        new_status: str,
        feedback: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        # Validate application_id format to prevent prompt injection
        try:
            uuid.UUID(application_id)
        except ValueError:
            return json.dumps({"error": "Invalid application ID format."})
        updated = self._tracker.update_status(
            application_id,
            ApplicationStatus(new_status),
            feedback,
            notes,
        )
        if not updated:
            return json.dumps({"error": "Application not found."})
        return json.dumps({"application_id": application_id, "new_status": new_status})

    def list_applications(self) -> list[ApplicationRecord]:
        """Return all tracked applications for the current user (direct, no LLM)."""
        return self._tracker.get_applications(self.profile.id)

    def _tool_list_applications(self) -> str:
        apps = self._tracker.get_applications(self.profile.id)
        if not apps:
            return json.dumps({"applications": [], "total": 0, "message": "No applications tracked yet."})
        records = []
        for a in apps:
            job = self._job_cache.get(a.job_id)
            records.append({
                "id": a.id,
                "job_id": a.job_id,
                "job_title": getattr(job, "title", None),
                "company": getattr(job, "company", None),
                "status": a.status.value,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "last_updated": a.last_updated.isoformat(),
                "notes": a.notes or "",
            })
        return json.dumps({"applications": records, "total": len(records)}, indent=2)

    def _tool_get_analytics(self) -> str:
        metrics = self._tracker.compute_metrics(self.profile.id)
        insights = self._tracker.generate_insights(self.profile.id)
        return json.dumps({"metrics": metrics, "insights": insights}, indent=2)

    def _tool_feedback_analysis(self) -> str:
        return self._tracker.employer_feedback_analysis(self.profile.id)

    def _tool_career_dreamer(
        self,
        dream_role: str,
        dream_industry: str = "",
        dream_location: str = "",
        timeline_months: int = 12,
    ) -> str:
        scenario = DreamScenario(
            current_role=self.profile.desired_roles[0] if self.profile.desired_roles else "",
            dream_role=dream_role,
            dream_industry=dream_industry,
            dream_location=dream_location,
            timeline_months=timeline_months,
        )
        gap_report = self._career_dreamer.build_gap_report(self.profile, scenario)
        timeline = self._career_dreamer.build_timeline(gap_report, timeline_months)
        return json.dumps({
            "dream_role": dream_role,
            "feasibility_score": gap_report.feasibility_score,
            "feasibility_rationale": gap_report.feasibility_rationale,
            "overlapping_skills": gap_report.overlapping_skills,
            "missing_skills": gap_report.missing_skills,
            "salary_current": gap_report.salary_current,
            "salary_dream": gap_report.salary_dream,
            "recommendations": gap_report.recommendations,
            "timeline_weeks": timeline.total_weeks,
            "milestones": timeline.milestones,
        }, indent=2)

    def _tool_analyze_skill_gaps(self, region: str = "") -> str:
        result = self._search_engine.analyze_skill_gaps(self.profile, region)
        return json.dumps(result, indent=2)

    def _tool_score_ats_match(self, job_id: str, resume_text: str = "") -> str:
        job = self._job_cache.get(job_id)
        if not job:
            return json.dumps({"error": "Job not found in current session. Run search_jobs first."})
        if not resume_text:
            return json.dumps({"error": "No resume text provided. Generate a resume first or pass the text."})
        # Handle both JobListing objects and raw dicts from API live search
        if isinstance(job, dict):
            description = job.get("job_description", "") or job.get("description", "")
        else:
            description = job.description
        result = self._doc_gen.score_ats_match(resume_text, description)
        return json.dumps(result, indent=2)
