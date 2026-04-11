"""Chat and resume parsing endpoints."""

import asyncio
import base64
import io
import json as _json
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from slowapi import Limiter

from config.settings import AGENT_MODEL
from routers.schemas import AgentResponse, ChatRequest, ResumeParseResponse
from src.llm_client import create_message_with_failover, get_llm_client
from src.utils import strip_json_fences

router = APIRouter(prefix="/api", tags=["chat"])

_RESUME_PARSE_PROMPT = (
    "Extract information from this resume. Return ONLY valid JSON, no markdown "
    'fences, no explanation:\n{"name":"","email":"","phone":"","location":"",'
    '"experience_level":"entry|mid|senior|lead|executive",'
    '"years_of_experience":0,"skills":[],"desired_roles":[],'
    '"certifications":[],"languages":[],"linkedin_url":"","portfolio_url":""}'
)


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.post("/chat", response_model=AgentResponse)
    @limiter.limit("15/minute")
    async def chat(
        request: Request,
        body: ChatRequest,
        session_id: str = session_dep,
    ):
        """Free-form conversation with the job agent."""
        agent = get_agent_fn(session_id)
        async with get_lock_fn(session_id):
            response = await asyncio.to_thread(agent.chat, body.message)
        return AgentResponse(response=response)

    @router.delete("/chat/reset", status_code=status.HTTP_204_NO_CONTENT)
    @limiter.limit("10/minute")
    async def reset_chat(request: Request, session_id: str = session_dep):
        """Clear conversation history (profile and job cache persist)."""
        agent = get_agent_fn(session_id)
        agent.reset_conversation()

    @router.post("/parse-resume", response_model=ResumeParseResponse)
    @limiter.limit("5/minute")
    async def parse_resume(
        request: Request,
        file: UploadFile,
        session_id: str = session_dep,
    ):
        """Parse a resume file (PDF or text) via Claude."""
        _ALLOWED_MIME = {
            "application/pdf", "text/plain", "text/csv", "text/markdown",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        }
        if not file.content_type:
            raise HTTPException(status_code=400, detail="File type not detected.")
        if file.content_type not in _ALLOWED_MIME:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: PDF, DOCX, DOC, TXT",
            )

        _MAX_UPLOAD = 5_000_000
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_UPLOAD:
                raise HTTPException(status_code=400, detail="File too large (max 5 MB).")
            chunks.append(chunk)
        raw = b"".join(chunks)

        client = get_llm_client()

        _DOCX_MIMES = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        }

        if file.content_type == "application/pdf":
            b64 = base64.b64encode(raw).decode()
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
                        },
                        {"type": "text", "text": _RESUME_PARSE_PROMPT},
                    ],
                }
            ]
        elif file.content_type in _DOCX_MIMES:
            import docx
            doc = docx.Document(io.BytesIO(raw))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())[:4000]
            if not text.strip():
                raise HTTPException(status_code=400, detail="Could not extract text from document.")
            messages = [{"role": "user", "content": _RESUME_PARSE_PROMPT + "\n\nResume:\n" + text}]
        else:
            text = raw.decode("utf-8", errors="replace")[:4000]
            messages = [{"role": "user", "content": _RESUME_PARSE_PROMPT + "\n\nResume:\n" + text}]

        resp = create_message_with_failover(
            client, model=AGENT_MODEL, max_tokens=1000, messages=cast(Any, messages)
        )
        result_text = next((b.text for b in resp.content if b.type == "text"), "")
        if not result_text:
            raise HTTPException(status_code=502, detail="AI returned no text response.")
        clean = strip_json_fences(result_text)
        try:
            parsed = _json.loads(clean)
        except _json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="Failed to parse AI response.") from exc
        try:
            return ResumeParseResponse(**parsed)
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail="AI response did not match expected resume schema."
            ) from exc
