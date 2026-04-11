"""Documents API router -- template listing & file export."""


import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from slowapi import Limiter

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ── Response schemas ─────────────────────────────────────────────────────────

class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str]
    header_style: str
    columns: int


class TemplateListResponse(BaseModel):
    templates: list[TemplateInfo]


class ExportRequest(BaseModel):
    job_id: str = Field(..., max_length=200)
    template_id: str = Field(default="classic", max_length=50)
    format: str = Field(default="pdf", pattern="^(pdf|docx)$")
    tone: str = Field(default="professional", max_length=30)


class ExportContentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100_000)
    template_id: str = Field(default="classic", max_length=50)
    format: str = Field(default="pdf", pattern="^(pdf|docx)$")


class GeneratedDocumentInfo(BaseModel):
    id: str
    job_id: str
    doc_type: str
    created_at: str | None = None
    ats_score: float | None = None


# ── Route wiring ─────────────────────────────────────────────────────────────

def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    session_dep: Any,
) -> None:
    """Wire endpoints using the app's shared dependencies."""

    @router.get("/templates", response_model=TemplateListResponse)
    @limiter.limit("30/minute")
    async def list_templates(request: Request):
        """Return all available resume templates."""
        from src.resume_templates import list_templates as _list
        return TemplateListResponse(
            templates=[TemplateInfo(**t) for t in _list()]
        )

    @router.get("/templates/{template_id}")
    @limiter.limit("30/minute")
    async def get_template(request: Request, template_id: str):
        """Return details for a single template."""
        from src.resume_templates import TEMPLATES
        tpl = TEMPLATES.get(template_id)
        if not tpl:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")
        return TemplateInfo(
            id=tpl.id,
            name=tpl.name,
            description=tpl.description,
            tags=tpl.tags,
            header_style=tpl.header_style,
            columns=tpl.columns,
        )

    @router.post("/export")
    @limiter.limit("5/minute")
    async def export_document(
        request: Request,
        body: ExportRequest,
        session_id: str = session_dep,
    ):
        """Generate a resume and export it as PDF or DOCX with the chosen template.

        1. Generates resume markdown via the agent's document generator.
        2. Renders it through the chosen template.
        3. Returns binary file for download.
        """
        agent = get_agent_fn(session_id)

        if body.job_id not in agent._job_cache:
            raise HTTPException(
                status_code=400,
                detail="Job ID not found in session cache. Run a job search first.",
            )

        from src.models import JobListing
        raw = agent._job_cache[body.job_id]
        job = JobListing(
            title=raw.get("job_title", "Unknown"),
            company=raw.get("employer_name", "Unknown"),
            location=raw.get("job_city", "") or raw.get("job_country", ""),
            description=(raw.get("job_description") or "")[:3000],
            requirements=raw.get("job_required_skills") or [],
            source_url=raw.get("job_apply_link", ""),
            remote_allowed=raw.get("job_is_remote", False),
        )

        # Generate resume markdown
        doc = await asyncio.to_thread(
            agent._doc_gen.generate_resume,
            agent.profile, job, body.tone,
        )

        # Export with template
        from src.resume_export import export_pdf, export_docx
        if body.format == "pdf":
            file_bytes = await asyncio.to_thread(export_pdf, doc.content, body.template_id)
            media_type = "application/pdf"
            ext = "pdf"
        else:
            file_bytes = await asyncio.to_thread(export_docx, doc.content, body.template_id)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"

        safe_company = "".join(c for c in job.company if c.isalnum() or c in " -_")[:30]
        filename = f"resume_{safe_company}_{body.template_id}.{ext}"

        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/stored/{document_id}/download")
    @limiter.limit("10/minute")
    async def download_stored_document(
        request: Request,
        document_id: str,
        format: str = "pdf",
        template_id: str = "classic",
        session_id: str = session_dep,
    ):
        """Stream a persisted ``GeneratedDocumentORM`` as PDF or DOCX (P3.4).

        The endpoint checks ownership against the current session's user
        profile before serving the bytes so one user can't exfiltrate
        another user's generated documents via a guessed id.
        """
        if format not in ("pdf", "docx"):
            raise HTTPException(status_code=422, detail="format must be pdf or docx")

        from src.models import GeneratedDocumentORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            row = (
                db.query(GeneratedDocumentORM)
                .filter_by(id=document_id, user_id=profile.id)
                .first()
            )
            if row is None:
                raise HTTPException(status_code=404, detail="Document not found.")
            content = str(row.content or "")
            doc_type = str(row.doc_type or "document")
        finally:
            db.close()

        from src.resume_export import export_docx, export_pdf
        if format == "pdf":
            file_bytes = await asyncio.to_thread(export_pdf, content, template_id)
            media_type = "application/pdf"
        else:
            file_bytes = await asyncio.to_thread(export_docx, content, template_id)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        safe_type = "".join(c for c in doc_type if c.isalnum() or c in "-_")[:20] or "document"
        filename = f"{safe_type}_{document_id[:8]}.{format}"
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.post("/export-content")
    @limiter.limit("10/minute")
    async def export_content(
        request: Request,
        body: ExportContentRequest,
        session_id: str = session_dep,
    ):
        """Export raw markdown content to PDF or DOCX with a template.

        Useful when the user already has generated content and wants to
        re-export with a different template or format.
        """
        content = body.content
        template_id = body.template_id
        fmt = body.format

        from src.resume_export import export_pdf, export_docx
        if fmt == "pdf":
            file_bytes = await asyncio.to_thread(export_pdf, content, template_id)
            media_type = "application/pdf"
        else:
            file_bytes = await asyncio.to_thread(export_docx, content, template_id)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="resume.{fmt}"'},
        )
