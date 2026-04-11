"""AI Job Agent -- Main Orchestrator.

Wires together every sub-system and exposes a single `JobAgent` class.
Tool schemas live in src/agent_tools.py.
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
from src.privacy import sanitise_for_llm, strip_protected_attributes
from src.agent_tools import TOOLS, SYSTEM_PROMPT
from src.analytics import ApplicationTracker
from src.career_dreamer import CareerDreamer
from src.document_generator import DocumentGenerator
from src.interview_service import InterviewPrepService
from src.job_search import JobSearchEngine, MarketIntelligenceService
from src.outcome_service import OutcomeLearningService
from src.restrategizer import RejectionRestrategizer
from src.salary_service import SalaryCalibrationService
from src.models import (
    ApplicationRecord,
    ApplicationStatus,
    DreamScenario,
    UserProfile,
    init_db,
)

logger = logging.getLogger(__name__)


class JobAgent:
    """Orchestrates the full job-application workflow via an agentic loop."""

    def __init__(self, profile: UserProfile) -> None:
        self.profile = profile
        self._client = get_llm_client()
        self._session = init_db()
        self._search_engine = JobSearchEngine(self._client)
        self._market_svc = MarketIntelligenceService(self._client)
        self._doc_gen = DocumentGenerator(self._client)
        self._tracker = ApplicationTracker(self._session, self._client)
        self._career_dreamer = CareerDreamer(self._client)
        self._salary_svc = SalaryCalibrationService(self._client)
        self._interview_svc = InterviewPrepService(self._client)
        self._outcome_svc = OutcomeLearningService(self._client)
        self._restrategizer = RejectionRestrategizer(self._client)

        self._job_cache: dict[str, Any] = {}
        self._job_cache_max = 200
        self._app_cache: dict[str, ApplicationRecord] = {}
        self._messages: list[dict[str, Any]] = []
        self._max_history = 50

    # ── Privacy helpers ────────────────────────────────────────────────────

    def _safe_profile_dict(self) -> dict[str, Any]:
        """Profile dict safe for LLM context: no PII, no protected attributes."""
        raw = self.profile.model_dump(mode="json")
        return sanitise_for_llm(strip_protected_attributes(raw))

    # ── Public API ─────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying database session to release connections."""
        if self._session:
            self._session.close()

    def chat(self, user_message: str) -> str:
        """Send a message and get a response via the agentic tool-use loop."""
        self._messages.append({"role": "user", "content": user_message})
        if len(self._messages) > self._max_history:
            self._messages = self._messages[:1] + self._messages[-(self._max_history - 1):]
        return self._agent_loop()

    def reset_conversation(self) -> None:
        """Clear conversation history (profile and caches persist)."""
        self._messages = []

    def list_applications(self) -> list[ApplicationRecord]:
        """Return all tracked applications for the current user (direct, no LLM)."""
        return self._tracker.get_applications(self.profile.id)

    # ── Agentic loop ───────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        safe = self._safe_profile_dict()
        profile_ctx = json.dumps(safe, indent=2)
        return f"{SYSTEM_PROMPT}\n\nUser profile context (safe fields only):\n{profile_ctx}"

    def _agent_loop(self, max_turns: int = 20) -> str:
        system = self._build_system_prompt()
        for _turn in range(max_turns):
            try:
                response = create_message_with_failover(
                    self._client,
                    model=AGENT_MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system,
                    tools=cast(Any, TOOLS),
                    messages=cast(Any, self._messages),
                )
            except Exception as exc:
                logger.error("LLM call failed in agent loop: %s", exc)
                return f"I'm unable to process your request right now. The AI service returned an error: {type(exc).__name__}. Please try again shortly."
            self._messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
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
                break

        return "I reached the maximum number of processing steps. Please try a simpler request."

    # ── Tool dispatcher ────────────────────────────────────────────────────

    def _dispatch_tool(self, name: str, args: dict[str, Any]) -> str:
        try:
            handler = self._TOOL_MAP.get(name)
            if handler:
                return handler(self, **args)
            return json.dumps({"error": f"Unknown tool: {name}"})
        except Exception:
            logger.exception("Tool %s failed", name)
            return json.dumps({"error": f"Tool '{name}' encountered an internal error."})

    # ── Tool implementations ───────────────────────────────────────────────

    def _tool_search_jobs(self, location_filter: str = "", include_remote: bool = True, max_results: int = 10) -> str:
        listings = self._search_engine.search(self.profile, max_results=max_results)
        if location_filter:
            listings = self._search_engine.filter_by_location(listings, location_filter, include_remote)
        for j in listings:
            if len(self._job_cache) >= self._job_cache_max:
                del self._job_cache[next(iter(self._job_cache))]
            self._job_cache[j.id] = j
        return json.dumps([{
            "id": j.id, "title": j.title, "company": j.company, "location": j.location,
            "remote": j.remote_allowed,
            "salary": f"{j.currency} {j.salary_min}-{j.salary_max}" if j.salary_min else "Not disclosed",
            "match_score": j.match_score, "match_rationale": j.match_rationale,
            "source": j.source_platform, "url": j.source_url,
        } for j in listings], indent=2)

    def _tool_market_insights(self, region: str, industry: str) -> str:
        return json.dumps(self._market_svc.get_insights(region, industry).model_dump(mode="json"), indent=2)

    def _tool_application_tips(self, region: str) -> str:
        return self._market_svc.get_application_tips(region)

    _ALLOWED_TONES = {"professional", "creative", "technical", "executive", "academic"}

    def _tool_generate_resume(self, job_id: str, tone: str = "professional") -> str:
        if tone not in self._ALLOWED_TONES:
            tone = "professional"
        job = self._job_cache.get(job_id)
        if not job:
            return json.dumps({"error": "Job not found in current session. Run search_jobs first."})
        doc = self._doc_gen.generate_resume(self.profile, job, tone)
        return json.dumps({"document_id": doc.id, "doc_type": doc.doc_type, "content": doc.content, "tailoring_notes": doc.tailoring_notes})

    def _tool_generate_cover_letter(self, job_id: str) -> str:
        job = self._job_cache.get(job_id)
        if not job:
            return json.dumps({"error": "Job not found. Run search_jobs first."})
        doc = self._doc_gen.generate_cover_letter(self.profile, job)
        return json.dumps({"document_id": doc.id, "doc_type": doc.doc_type, "content": doc.content, "tailoring_notes": doc.tailoring_notes})

    def _tool_track_application(self, job_id: str, notes: str = "") -> str:
        record = ApplicationRecord(
            id=str(uuid.uuid4()), user_id=self.profile.id, job_id=job_id,
            status=ApplicationStatus.SUBMITTED,
            submitted_at=datetime.now(timezone.utc), last_updated=datetime.now(timezone.utc), notes=notes,
        )
        self._tracker.add_application(record)
        self._app_cache[record.id] = record
        return json.dumps({"application_id": record.id, "status": record.status.value})

    def _tool_update_application(self, application_id: str, new_status: str, feedback: Optional[str] = None, notes: Optional[str] = None) -> str:
        try:
            uuid.UUID(application_id)
        except ValueError:
            return json.dumps({"error": "Invalid application ID format."})
        updated = self._tracker.update_status(application_id, ApplicationStatus(new_status), feedback, notes)
        if not updated:
            return json.dumps({"error": "Application not found."})
        return json.dumps({"application_id": application_id, "new_status": new_status})

    def _tool_list_applications(self) -> str:
        apps = self._tracker.get_applications(self.profile.id)
        if not apps:
            return json.dumps({"applications": [], "total": 0, "message": "No applications tracked yet."})
        records = [{"id": a.id, "job_id": a.job_id, "job_title": getattr(self._job_cache.get(a.job_id), "title", None),
                     "company": getattr(self._job_cache.get(a.job_id), "company", None), "status": a.status.value,
                     "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                     "last_updated": a.last_updated.isoformat(), "notes": a.notes or ""} for a in apps]
        return json.dumps({"applications": records, "total": len(records)}, indent=2)

    def _tool_get_analytics(self) -> str:
        return json.dumps({"metrics": self._tracker.compute_metrics(self.profile.id),
                           "insights": self._tracker.generate_insights(self.profile.id)}, indent=2)

    def _tool_feedback_analysis(self) -> str:
        return self._tracker.employer_feedback_analysis(self.profile.id)

    def _tool_career_dreamer(self, dream_role: str, dream_industry: str = "", dream_location: str = "", timeline_months: int = 12) -> str:
        scenario = DreamScenario(
            current_role=self.profile.desired_roles[0] if self.profile.desired_roles else "",
            dream_role=dream_role, dream_industry=dream_industry, dream_location=dream_location, timeline_months=timeline_months,
        )
        gap = self._career_dreamer.build_gap_report(self.profile, scenario)
        tl = self._career_dreamer.build_timeline(gap, timeline_months)
        return json.dumps({"dream_role": dream_role, "feasibility_score": gap.feasibility_score,
                           "feasibility_rationale": gap.feasibility_rationale, "overlapping_skills": gap.overlapping_skills,
                           "missing_skills": gap.missing_skills, "salary_current": gap.salary_current, "salary_dream": gap.salary_dream,
                           "recommendations": gap.recommendations, "timeline_weeks": tl.total_weeks, "milestones": tl.milestones}, indent=2)

    def _tool_analyze_skill_gaps(self, region: str = "") -> str:
        return json.dumps(self._search_engine.analyze_skill_gaps(self.profile, region), indent=2)

    def _tool_score_ats_match(self, job_id: str, resume_text: str = "") -> str:
        job = self._job_cache.get(job_id)
        if not job:
            return json.dumps({"error": "Job not found in current session. Run search_jobs first."})
        if not resume_text:
            return json.dumps({"error": "No resume text provided. Generate a resume first or pass the text."})
        desc = job.get("job_description", "") or job.get("description", "") if isinstance(job, dict) else job.description
        return json.dumps(self._doc_gen.score_ats_match(resume_text, desc), indent=2)

    # ── Sprint 2 tools ────────────────────────────────────────────────────

    def _tool_salary_calibrate(self, role: str, locations: list[str] | None = None) -> str:
        locs = locations or [self.profile.location or "United States"]
        result = self._salary_svc.calibrate(role, locs, self.profile.skills)
        return json.dumps(result.model_dump(mode="json"), indent=2)

    def _tool_save_dream(self, dream_role: str, dream_industry: str = "", dream_location: str = "") -> str:
        from src.models import CareerDreamORM
        dream_orm = CareerDreamORM(
            user_id=self.profile.id,
            dream_role=dream_role,
            dream_industry=dream_industry,
            dream_location=dream_location,
        )
        self._session.add(dream_orm)
        self._session.commit()
        return json.dumps({"saved": True, "dream_id": dream_orm.id, "dream_role": dream_role})

    # ── Sprint 3 tools ────────────────────────────────────────────────────

    def _tool_prepare_interview(self, job_id: str) -> str:
        job = self._job_cache.get(job_id)
        if not job:
            return json.dumps({"error": "Job not found. Run search_jobs first."})
        if isinstance(job, dict):
            title = job.get("job_title", job.get("title", ""))
            company = job.get("employer_name", job.get("company", ""))
            desc = job.get("job_description", "")
        else:
            title, company, desc = job.title, job.company, job.description
        package = self._interview_svc.full_prep(title, company, desc, self.profile.skills)
        return json.dumps(package.model_dump(mode="json"), indent=2)

    def _tool_debrief_interview(self, job_id: str, how_it_went: str, questions_asked: str = "", concerns: str = "") -> str:
        job = self._job_cache.get(job_id)
        title = "the role"
        company = "the company"
        if job:
            if isinstance(job, dict):
                title = job.get("job_title", job.get("title", title))
                company = job.get("employer_name", job.get("company", company))
            else:
                title, company = job.title, job.company
        report = self._interview_svc.debrief(title, company, {
            "How did it go?": how_it_went,
            "Questions asked": questions_asked,
            "Concerns": concerns,
        })
        return json.dumps(report.model_dump(mode="json"), indent=2)

    # ── Sprint 4 tools ────────────────────────────────────────────────────

    def _tool_outcome_insights(self) -> str:
        apps = self._tracker.get_applications(self.profile.id)
        apps_dicts = [{"id": a.id, "job_id": a.job_id, "status": a.status.value,
                        "job_title": getattr(self._job_cache.get(a.job_id), "title", None) or
                        (self._job_cache.get(a.job_id, {}).get("job_title") if isinstance(self._job_cache.get(a.job_id), dict) else None),
                        "company": getattr(self._job_cache.get(a.job_id), "company", None) or
                        (self._job_cache.get(a.job_id, {}).get("employer_name") if isinstance(self._job_cache.get(a.job_id), dict) else None),
                        } for a in apps]
        insights = self._outcome_svc.generate_insights(apps_dicts, [])
        return insights

    def _tool_restrategize(self) -> str:
        apps = self._tracker.get_applications(self.profile.id)
        rejections = [{"id": a.id, "job_id": a.job_id, "status": a.status.value,
                        "job_title": getattr(self._job_cache.get(a.job_id), "title", "Unknown"),
                        "company": getattr(self._job_cache.get(a.job_id), "company", "Unknown"),
                        } for a in apps if a.status.value == "rejected"]
        patterns = self._restrategizer.detect_patterns(rejections)
        profile_summary = f"{self.profile.desired_roles}, {self.profile.experience_level.value} level, skills: {', '.join(self.profile.skills[:10])}"
        advice = self._restrategizer.generate_advice(patterns, profile_summary)
        return json.dumps(advice.model_dump(mode="json"), indent=2)

    def _tool_negotiate_salary(self, company: str, role: str, base_salary: int, location: str = "") -> str:
        from src.salary_service import OfferDetails
        offer = OfferDetails(company=company, role=role, base_salary=base_salary, location=location)
        market_data = self._salary_svc.get_bls_oews_data(role, location)
        script = self._salary_svc.generate_counter_offer(offer, market_data)
        return json.dumps(script.model_dump(mode="json"), indent=2)

    _TOOL_MAP: dict[str, Any] = {
        "search_jobs": _tool_search_jobs,
        "get_market_insights": _tool_market_insights,
        "get_application_tips": _tool_application_tips,
        "generate_resume": _tool_generate_resume,
        "generate_cover_letter": _tool_generate_cover_letter,
        "track_application": _tool_track_application,
        "update_application": _tool_update_application,
        "list_applications": _tool_list_applications,
        "get_analytics": _tool_get_analytics,
        "get_feedback_analysis": _tool_feedback_analysis,
        "career_dreamer": _tool_career_dreamer,
        "analyze_skill_gaps": _tool_analyze_skill_gaps,
        "score_ats_match": _tool_score_ats_match,
        "salary_calibrate": _tool_salary_calibrate,
        "save_dream": _tool_save_dream,
        "prepare_interview": _tool_prepare_interview,
        "debrief_interview": _tool_debrief_interview,
        "outcome_insights": _tool_outcome_insights,
        "restrategize": _tool_restrategize,
        "negotiate_salary": _tool_negotiate_salary,
    }
