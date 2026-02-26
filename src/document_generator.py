"""
Document Generator — Resume & Cover Letter.

Design
──────
• Claude is used to produce a first draft tailored to each job listing.
• The output is plain Markdown (easy to convert to PDF/DOCX downstream).
• PII is passed to the generator because the *user* controls what goes in
  their own documents; it is never sent to third-party job boards.
• A tailoring_notes field explains every significant edit so the user
  understands why choices were made.

Customisation hooks
───────────────────
• RESUME_TONE  — "professional" (default) | "creative" | "technical"
• Extend DocumentGenerator with a custom template by subclassing and
  overriding _resume_system_prompt() / _cover_letter_system_prompt().
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

import anthropic

from config.settings import AGENT_MODEL, MAX_TOKENS
from src.models import GeneratedDocument, JobListing, UserProfile


_RESUME_SYSTEM = """You are an expert resume writer with 15+ years of experience
across tech, finance, marketing, and creative industries worldwide.

Rules:
1. Write in Markdown. Use ## for section headers, bold for company/role names.
2. Tailor bullet points to mirror the job listing's keywords and requirements.
3. Quantify achievements wherever possible (e.g. "reduced latency by 40%").
4. Keep to 1–2 pages of content (roughly 500–800 words of body text).
5. Never invent credentials or experiences not supplied by the user.
6. Do NOT include any protected-attribute language (age, gender, etc.).
7. End with a JSON block between ```json ``` tags containing "tailoring_notes".
"""

_COVER_LETTER_SYSTEM = """You are a professional career coach who writes compelling,
personalised cover letters that stand out without being gimmicky.

Rules:
1. Write in plain prose (no bullet lists in the body).
2. Opening: hook with a specific reason why you're excited about THIS company.
3. Middle: bridge 2–3 key skills/experiences to the job's core requirements.
4. Closing: confident call to action, no desperate begging.
5. Tone: enthusiastic but professional. Adapt to regional/industry norms.
6. Length: 3–4 paragraphs (~300–400 words).
7. End with a JSON block between ```json ``` tags containing "tailoring_notes".
"""


class DocumentGenerator:
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic()

    # ── Public API ─────────────────────────────────────────────────────────

    def generate_resume(
        self,
        profile: UserProfile,
        job: JobListing,
        tone: str = "professional",
    ) -> GeneratedDocument:
        """Generate a tailored resume for *job* based on *profile*."""
        user_prompt = self._build_resume_prompt(profile, job, tone)
        raw = self._call_model(_RESUME_SYSTEM, user_prompt)
        content, notes = self._split_notes(raw)
        return GeneratedDocument(
            id=str(uuid.uuid4()),
            user_id=profile.id,
            job_id=job.id,
            doc_type="resume",
            content=content,
            created_at=datetime.utcnow(),
            model_used=AGENT_MODEL,
            tailoring_notes=notes,
        )

    def generate_cover_letter(
        self,
        profile: UserProfile,
        job: JobListing,
    ) -> GeneratedDocument:
        """Generate a tailored cover letter for *job*."""
        user_prompt = self._build_cover_letter_prompt(profile, job)
        raw = self._call_model(_COVER_LETTER_SYSTEM, user_prompt)
        content, notes = self._split_notes(raw)
        return GeneratedDocument(
            id=str(uuid.uuid4()),
            user_id=profile.id,
            job_id=job.id,
            doc_type="cover_letter",
            content=content,
            created_at=datetime.utcnow(),
            model_used=AGENT_MODEL,
            tailoring_notes=notes,
        )

    def suggest_improvements(
        self,
        document: GeneratedDocument,
        job: JobListing,
    ) -> str:
        """Return a bullet-list of specific improvement suggestions."""
        prompt = f"""Review the following {document.doc_type} for a {job.title} role
at {job.company}.

--- DOCUMENT ---
{document.content}

--- JOB REQUIREMENTS ---
{json.dumps(job.requirements)}

Provide 5–7 specific, actionable improvement suggestions as a numbered list.
Focus on: keyword optimisation, impact quantification, relevance, and structure.
"""
        response = self._client.messages.create(
            model=AGENT_MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    # ── Private helpers ────────────────────────────────────────────────────

    def _call_model(self, system: str, user_content: str) -> str:
        response = self._client.messages.create(
            model=AGENT_MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text.strip()

    def _split_notes(self, raw: str) -> tuple[str, str]:
        """Separate document body from trailing ```json ... ``` tailoring notes."""
        if "```json" in raw:
            body, _, rest = raw.partition("```json")
            notes_raw = rest.partition("```")[0].strip()
            try:
                notes_data = json.loads(notes_raw)
                notes = notes_data.get("tailoring_notes", notes_raw)
            except json.JSONDecodeError:
                notes = notes_raw
            return body.strip(), notes
        return raw, ""

    def _build_resume_prompt(
        self, profile: UserProfile, job: JobListing, tone: str
    ) -> str:
        edu_text = json.dumps(profile.education, indent=2) if profile.education else "Not provided"
        work_text = json.dumps(profile.work_history, indent=2) if profile.work_history else "Not provided"
        return f"""Create a {tone} resume for the following candidate applying to the job below.

=== CANDIDATE PROFILE ===
Name: {profile.name}
Location: {profile.location}
Email: {profile.email}
Skills: {", ".join(profile.skills)}
Experience Level: {profile.experience_level.value} ({profile.years_of_experience} years)
Languages: {", ".join(profile.languages)}
Certifications: {", ".join(profile.certifications) or "None"}
Portfolio: {profile.portfolio_url or "N/A"}
LinkedIn: {profile.linkedin_url or "N/A"}

Education:
{edu_text}

Work History:
{work_text}

=== TARGET JOB ===
Title: {job.title}
Company: {job.company}
Location: {job.location}  |  Remote: {job.remote_allowed}
Industry: {job.industry}
Required Skills: {", ".join(job.requirements)}
Nice-to-Have: {", ".join(job.nice_to_have)}
Description:
{job.description}

Generate the full resume now. After the resume, add a ```json block with:
{{"tailoring_notes": "<explanation of specific tailoring choices made>"}}
"""

    def _build_cover_letter_prompt(
        self, profile: UserProfile, job: JobListing
    ) -> str:
        return f"""Write a cover letter for the following candidate and job.

=== CANDIDATE ===
Name: {profile.name}
Location: {profile.location}
Key Skills: {", ".join(profile.skills[:10])}
Experience: {profile.years_of_experience} years as {", ".join(profile.desired_roles[:3])}
Notable:
- Education: {profile.education[0].get("degree","") if profile.education else "Not specified"}
- Recent role: {profile.work_history[0].get("title","") if profile.work_history else "Not specified"}
  at {profile.work_history[0].get("company","") if profile.work_history else ""}

=== JOB ===
Title: {job.title}
Company: {job.company}
Location: {job.location}
Industry: {job.industry}
Must-have skills: {", ".join(job.requirements)}
Description: {job.description}

Write the cover letter now. After the letter, add a ```json block with:
{{"tailoring_notes": "<why specific paragraphs/phrases were chosen>"}}
"""
