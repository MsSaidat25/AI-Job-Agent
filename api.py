# Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com). All Rights Reserved.
# avien@aviensolutions.com
"""AI Job Agent -- FastAPI REST Server.

Thin orchestration layer: app setup, middleware, and router mounting.
Session management lives in src/session_store.py.
All domain endpoints live in routers/*.
"""

from contextlib import asynccontextmanager
import base64
import hashlib
import logging
import os
import re
from typing import Optional
import uuid

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()  # Must run before src.* imports which read env via config.settings

from fastapi import FastAPI, Request, status  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sqlalchemy import text as sa_text  # noqa: E402
from slowapi import Limiter  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

from config.settings import (  # noqa: E402
    AUTH_ENABLED,
    LLM_API_KEY,
    USE_VERTEX_PRIMARY,
    VERTEX_PROJECT,
    validate_production_config,
)
from src.agent import JobAgent  # noqa: E402
from src.models import UserProfile  # noqa: E402
from src.session_store import (  # noqa: E402
    SessionId,
    cleanup_sessions,
    close_all_sessions,
    create_session,
    get_agent,
    get_session_lock,
    get_session_profile,
    get_sessions,
    set_session_agent,
)
from routers.schemas import (  # noqa: E402
    HealthResponse,
    ProfileRequest,
    ProfileResponse,
    SessionResponse,
)


# ── App setup ────────────────────────────────────────────────────────────────

_TRUST_PROXY: bool = os.environ.get("TRUST_PROXY", "false").lower() == "true"


def _get_real_client_ip(request: Request) -> str:
    if _TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Trust the rightmost IP (last proxy-appended) to prevent
            # client-side spoofing of the first entry.
            ips = [ip.strip() for ip in forwarded.split(",")]
            return ips[-1] if ips else get_remote_address(request)
    return get_remote_address(request)


limiter = Limiter(key_func=_get_real_client_ip)


# ── CSP inline-script hashes ────────────────────────────────────────────────
#
# The frontend still contains two small inline <script> blocks (theme flash
# prevention + Tailwind config) that must run before first paint, so we can't
# simply externalise them. Instead we compute their SHA-256 at module load
# time and emit them as `'sha256-…'` hash sources, which lets us drop
# `'unsafe-inline'` from `script-src` entirely. If the inline bodies change,
# hashes are re-derived on next restart — no manual sync.
#
# We still allow `'unsafe-eval'` because the Tailwind Play CDN's JIT requires
# it. That is tracked as P2-scope follow-up (ship pre-compiled CSS).

_INLINE_SCRIPT_RE = re.compile(
    r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


def _compute_inline_script_hashes(html_path: str) -> list[str]:
    """Return `'sha256-…'` hash sources for every inline <script> in *html_path*."""
    try:
        with open(html_path, "rb") as f:
            html_bytes = f.read()
    except OSError:
        logger.warning("CSP hash: cannot read %s; falling back to permissive policy", html_path)
        return []
    hashes: list[str] = []
    for match in _INLINE_SCRIPT_RE.finditer(html_bytes.decode("utf-8", errors="replace")):
        body = match.group(1).encode("utf-8")
        digest = hashlib.sha256(body).digest()
        hashes.append(f"'sha256-{base64.b64encode(digest).decode('ascii')}'")
    return hashes


_INLINE_SCRIPT_HASHES: list[str] = _compute_inline_script_hashes("frontend/index.html")
if _INLINE_SCRIPT_HASHES:
    _SCRIPT_INLINE_POLICY = " ".join(_INLINE_SCRIPT_HASHES)
else:
    # Degraded mode: if we couldn't read the HTML, keep 'unsafe-inline' so
    # inline scripts still work. This should never happen in prod.
    _SCRIPT_INLINE_POLICY = "'unsafe-inline'"

_docs_url: Optional[str] = "/docs" if not AUTH_ENABLED else None
_redoc_url: Optional[str] = "/redoc" if not AUTH_ENABLED else None


validate_production_config()


@asynccontextmanager
async def _lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    yield
    close_all_sessions()


app = FastAPI(
    title="AI Job Agent API",
    description="REST interface for the AI-powered job application assistant.",
    version="2.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=_lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
_ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in _raw_origins.split(",")
    if o.strip()
] if _raw_origins else [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://10.0.2.2:8000",       # Android emulator -> host
    "http://localhost:8081",       # Expo Metro dev server
    "http://localhost:19006",      # Expo web dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-ID"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    await cleanup_sessions()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    logger.info("%s %s [rid=%s]", request.method, request.url.path, request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        # 'unsafe-eval' is retained solely for the Tailwind Play CDN JIT.
        # 'unsafe-inline' is intentionally dropped in favour of SHA-256
        # hashes computed from the two inline bootstrap scripts.
        f"script-src 'self' {_SCRIPT_INLINE_POLICY} 'unsafe-eval' "
        "https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data:; "
        "font-src 'self' https://fonts.gstatic.com https://fonts.googleapis.com; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )
    scheme = request.url.scheme
    if _TRUST_PROXY:
        scheme = request.headers.get("X-Forwarded-Proto", scheme)
    if scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


# ── Core endpoints (session, profile, health) ───────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse("frontend/index.html")


@app.head("/", include_in_schema=False)
async def head_root():
    return Response()


def _check_db_health() -> str:
    """Return "ok" if the DB accepts a trivial query, else "error"."""
    try:
        from src.models import get_active_engine, get_engine
        engine = get_active_engine()
        if engine is None:
            engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Liveness probe -- always 200 if the process is alive.

    Kubernetes/Cloud Run should hit this for liveness. Does NOT touch the
    DB so a stalled database never triggers a pod restart loop.
    """
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.get("/readyz", include_in_schema=False)
async def readyz():
    """Readiness probe -- 200 only when the DB is reachable.

    This is the gate for routing traffic: a degraded DB drops the pod from
    the load balancer rotation without killing it.
    """
    db_status = _check_db_health()
    if db_status != "ok":
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": db_status},
        )
    return JSONResponse(status_code=200, content={"status": "ok", "db": db_status})


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Back-compat full health report (sessions + LLM config + DB).

    Prefer `/healthz` (liveness) and `/readyz` (readiness) for orchestrator
    probes; this endpoint is kept for existing dashboards and tests.
    """
    db_status = _check_db_health()
    resp = HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        sessions=len(get_sessions()),
        db=db_status,
        llm_configured=bool(LLM_API_KEY) or (USE_VERTEX_PRIMARY and bool(VERTEX_PROJECT)),
    )
    if db_status != "ok":
        return JSONResponse(status_code=503, content=resp.model_dump())
    return resp


@app.post("/api/session", status_code=status.HTTP_201_CREATED, response_model=SessionResponse)
@limiter.limit("30/hour")
async def new_session(request: Request):
    await cleanup_sessions()
    session_id = create_session()
    return SessionResponse(session_id=session_id)


@app.post("/api/profile", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
@limiter.limit("10/minute")
async def set_profile(request: Request, body: ProfileRequest, session_id: str = SessionId):
    profile = UserProfile(
        name=body.name,
        email=body.email,
        phone=body.phone,
        location=body.location,
        skills=body.skills,
        experience_level=body.experience_level,
        years_of_experience=body.years_of_experience,
        education=body.education,
        work_history=body.work_history,
        desired_roles=body.desired_roles,
        desired_job_types=body.desired_job_types,
        desired_salary_min=body.desired_salary_min,
        desired_salary_max=body.desired_salary_max,
        languages=body.languages,
        certifications=body.certifications,
        portfolio_url=body.portfolio_url,
        linkedin_url=body.linkedin_url,
        preferred_currency=body.preferred_currency,
    )

    # Persist profile to DB
    from src.models import init_db, profile_to_orm
    db = init_db()
    try:
        orm_obj = profile_to_orm(profile)
        db.merge(orm_obj)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Failed to persist profile to DB", exc_info=True)
    finally:
        db.close()

    agent = JobAgent(profile=profile)
    set_session_agent(session_id, agent, profile)
    return ProfileResponse(
        profile_id=profile.id,
        message="Profile saved and agent initialised.",
        currency=body.preferred_currency,
    )


@app.get("/api/profile", response_model=ProfileRequest)
@limiter.limit("30/minute")
async def get_profile_endpoint(request: Request, session_id: str = SessionId):
    profile: UserProfile = get_session_profile(session_id)
    return profile.model_dump(mode="json")


# ── Mount domain routers ────────────────────────────────────────────────────

from routers.auth import router as auth_router, _setup_routes as _setup_auth  # noqa: E402
from routers.onboarding import router as onboard_router, _setup_routes as _setup_onboard  # noqa: E402
from routers.jobs import router as jobs_router, _setup_routes as _setup_jobs  # noqa: E402
from routers.applications import router as apps_router, _setup_routes as _setup_apps  # noqa: E402
from routers.chat import router as chat_router, _setup_routes as _setup_chat  # noqa: E402
from routers.employer import router as employer_router, _setup_routes as _setup_employer  # noqa: E402
from routers.documents import router as docs_router, _setup_routes as _setup_docs  # noqa: E402
from routers.kanban import router as kanban_router, _setup_routes as _setup_kanban  # noqa: E402
from routers.dashboard import router as dash_router, _setup_routes as _setup_dash  # noqa: E402
from routers.career import router as career_router, _setup_routes as _setup_career  # noqa: E402
from routers.salary import router as salary_router, _setup_routes as _setup_salary  # noqa: E402
from routers.feed import router as feed_router, _setup_routes as _setup_feed  # noqa: E402
from routers.nudges import router as nudges_router, _setup_routes as _setup_nudges  # noqa: E402
from routers.auto_apply import router as auto_apply_router, _setup_routes as _setup_auto_apply  # noqa: E402
from routers.interview import router as interview_router, _setup_routes as _setup_interview  # noqa: E402
from routers.email_oauth import router as email_router, _setup_routes as _setup_email  # noqa: E402
from routers.insights import router as insights_router, _setup_routes as _setup_insights  # noqa: E402
from routers.account import router as account_router, _setup_routes as _setup_account  # noqa: E402
from routers.offers import router as offers_router, _setup_routes as _setup_offers  # noqa: E402
from routers.privacy import router as privacy_router, _setup_routes as _setup_privacy  # noqa: E402

_setup_auth(limiter=limiter, session_dep=SessionId)
_setup_onboard(limiter=limiter, get_agent_fn=get_agent, session_dep=SessionId)
_setup_jobs(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_apps(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_chat(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_employer(limiter=limiter)
_setup_docs(limiter=limiter, get_agent_fn=get_agent, session_dep=SessionId)
_setup_kanban(limiter=limiter, get_agent_fn=get_agent, session_dep=SessionId)
_setup_dash(limiter=limiter, get_agent_fn=get_agent, session_dep=SessionId)
_setup_career(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_salary(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_feed(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_nudges(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_auto_apply(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_interview(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_email(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_insights(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_account(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_offers(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)
_setup_privacy(limiter=limiter, get_agent_fn=get_agent, get_lock_fn=get_session_lock, session_dep=SessionId)

_all_routers = [
    auth_router, onboard_router, jobs_router, apps_router, chat_router,
    employer_router, docs_router, kanban_router, dash_router,
    career_router, salary_router, feed_router, nudges_router,
    auto_apply_router, interview_router, email_router, insights_router,
    account_router, offers_router, privacy_router,
]
for r in _all_routers:
    app.include_router(r)


# ── Dev entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
