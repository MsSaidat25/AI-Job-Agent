"""Tool schemas and system prompt for the AI Job Agent.

Separated from agent.py to keep the orchestrator under 300 lines.
"""
from __future__ import annotations

from typing import Any

from src.models import ApplicationStatus


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
    # ── Sprint 2: Salary Calibration ────────────────────────────────────────
    {
        "name": "salary_calibrate",
        "description": (
            "Get salary calibration data for a role across locations. "
            "Combines BLS OEWS, H-1B LCA, and job posting data to show market rates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "description": "Target job title, e.g. 'Senior Software Engineer'"},
                "locations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of locations to compare, e.g. ['San Francisco', 'Austin', 'Remote']",
                },
            },
            "required": ["role"],
        },
    },
    {
        "name": "save_dream",
        "description": "Save a career dream scenario for future tracking and comparison.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dream_role": {"type": "string", "description": "The dream role title"},
                "dream_industry": {"type": "string", "description": "Target industry", "default": ""},
                "dream_location": {"type": "string", "description": "Target location", "default": ""},
            },
            "required": ["dream_role"],
        },
    },
    # ── Sprint 3: Interview Prep ─────────────────────────────────────────
    {
        "name": "prepare_interview",
        "description": (
            "Generate a complete interview preparation package for a specific job application. "
            "Includes company research, practice Q&A, and questions to ask."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "ID of the job to prepare for."},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "debrief_interview",
        "description": "Analyze a post-interview debrief to identify strengths, improvements, and next steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "ID of the job interviewed for."},
                "how_it_went": {"type": "string", "description": "User's description of how the interview went."},
                "questions_asked": {"type": "string", "description": "Questions they remember being asked."},
                "concerns": {"type": "string", "description": "Any concerns or things they felt went poorly.", "default": ""},
            },
            "required": ["job_id", "how_it_went"],
        },
    },
    # ── Sprint 4: Outcome Learning & Negotiation ─────────────────────────
    {
        "name": "outcome_insights",
        "description": "Get AI-powered insights from application outcomes -- what's working and what to change.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "restrategize",
        "description": "Analyze rejection patterns and get actionable advice to improve your application strategy.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "negotiate_salary",
        "description": "Generate a salary negotiation counter-offer script with market data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name"},
                "role": {"type": "string", "description": "Job title"},
                "base_salary": {"type": "integer", "description": "Offered base salary in USD"},
                "location": {"type": "string", "description": "Job location", "default": ""},
            },
            "required": ["company", "role", "base_salary"],
        },
    },
]


# ── Agent System Prompt ────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert AI Job Application Agent helping a job seeker
navigate the global job market.

Your capabilities:
- Search and rank job listings based on the user's skills and preferences
- Provide region-specific market intelligence and application tips
- Generate tailored resumes and cover letters for specific roles
- Score resumes for ATS (Applicant Tracking System) compatibility
- Analyse skill gaps against live job postings
- Explore dream career transitions with gap analysis and timelines
- Track application progress and analyse success patterns
- Calibrate salary expectations across locations using market data
- Prepare for interviews with company research and practice Q&A
- Learn from outcomes to improve future applications
- Analyze rejection patterns and restrategize
- Generate salary negotiation scripts with market data
- Offer unbiased, skill-based recommendations

Principles you ALWAYS follow:
1. Never discriminate or make recommendations based on protected attributes.
2. Be honest about fit: if a role is a stretch, say so constructively.
3. Respect user privacy: never repeat PII unnecessarily in conversation.
4. Be concise and actionable in your responses.
5. When you call a tool, explain to the user what you're doing and why.

After tool results arrive, synthesise them into clear, human-readable advice.
"""
