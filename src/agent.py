"""
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
import uuid
from datetime import datetime
from typing import Any, Optional

import anthropic

from config.settings import AGENT_MODEL, MAX_TOKENS
from src.analytics import ApplicationTracker
from src.document_generator import DocumentGenerator
from src.job_search import JobSearchEngine, MarketIntelligenceService
from src.models import (
    ApplicationRecord,
    ApplicationStatus,
    ExperienceLevel,
    JobListing,
    JobType,
    UserProfile,
    init_db,
)


# ── Tool schemas (JSON Schema for Claude's tool-use API) ───────────────────

TOOLS: list[dict] = [
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
                    "enum": ["professional", "creative", "technical"],
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
        "name": "get_analytics",
        "description": "Get application success metrics and AI-generated career insights.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_feedback_analysis",
        "description": "Analyse patterns across all employer feedback received.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


# ── Agent System Prompt ────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert AI Job Application Agent helping a job seeker
navigate the global job market.

Your capabilities:
• Search and rank job listings based on the user's skills and preferences
• Provide region-specific market intelligence and application tips
• Generate tailored resumes and cover letters for specific roles
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
        self._client = anthropic.Anthropic()
        self._session = init_db()
        self._search_engine = JobSearchEngine(self._client)
        self._market_svc = MarketIntelligenceService(self._client)
        self._doc_gen = DocumentGenerator(self._client)
        self._tracker = ApplicationTracker(self._session, self._client)

        # In-memory caches for the current session
        self._job_cache: dict[str, JobListing] = {}
        self._app_cache: dict[str, ApplicationRecord] = {}

        # Conversation history
        self._messages: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """
        Send a message to the agent and get a response.
        Runs the agentic tool-use loop internally.
        """
        self._messages.append({"role": "user", "content": user_message})
        return self._agent_loop()

    def reset_conversation(self) -> None:
        """Clear conversation history (profile and caches persist)."""
        self._messages = []

    # ── Agentic loop ───────────────────────────────────────────────────────

    def _agent_loop(self) -> str:
        """Run Claude tool-use loop until a final text response is produced."""
        while True:
            response = self._client.messages.create(
                model=AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self._messages,
            )

            # Append assistant turn to history
            self._messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Extract the text response
                for block in response.content:
                    if hasattr(block, "text"):
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

        return "I encountered an unexpected issue. Please try again."

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
            elif name == "get_analytics":
                return self._tool_get_analytics()
            elif name == "get_feedback_analysis":
                return self._tool_feedback_analysis()
            else:
                return json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

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
        # Cache for downstream tools
        for j in listings:
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

    def _tool_generate_resume(self, job_id: str, tone: str = "professional") -> str:
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
            submitted_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
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
        updated = self._tracker.update_status(
            application_id,
            ApplicationStatus(new_status),
            feedback,
            notes,
        )
        if not updated:
            return json.dumps({"error": "Application not found."})
        return json.dumps({"application_id": application_id, "new_status": new_status})

    def _tool_get_analytics(self) -> str:
        metrics = self._tracker.compute_metrics(self.profile.id)
        insights = self._tracker.generate_insights(self.profile.id)
        return json.dumps({"metrics": metrics, "insights": insights}, indent=2)

    def _tool_feedback_analysis(self) -> str:
        return self._tracker.employer_feedback_analysis(self.profile.id)
