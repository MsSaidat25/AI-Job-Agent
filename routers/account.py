"""Account lifecycle endpoints (Sprint 4)."""

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

router = APIRouter(prefix="/api/account", tags=["account"])


# ── Response schemas ─────────────────────────────────────────────────────────


class ExportResponse(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    format: str = "json"
    message: str = ""


class DeleteResponse(BaseModel):
    deleted: bool = False
    message: str = ""


# ── Routes ───────────────────────────────────────────────────────────────────


def _setup_routes(
    limiter: Limiter,
    get_agent_fn: Any,
    get_lock_fn: Any,
    session_dep: Any,
) -> None:
    @router.get("/export", response_model=ExportResponse)
    @limiter.limit("3/minute")
    async def export_user_data(
        request: Request,
        session_id: str = session_dep,
    ):
        """Export all user data as JSON."""
        from src.models import (
            ApplicationRecordORM,
            CareerDreamORM,
            GeneratedDocumentORM,
            UserProfileORM,
            init_db,
        )
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            user = db.query(UserProfileORM).filter_by(id=profile.id).first()
            if not user:
                return ExportResponse(message="No user data found.")

            # Decrypt profile via orm_to_profile for safe field access
            from src.models_db import orm_to_profile
            decrypted_profile = orm_to_profile(user)
            export: dict[str, Any] = {
                "profile": {
                    "id": decrypted_profile.id,
                    "name": decrypted_profile.name,
                    "email": decrypted_profile.email,
                    "location": decrypted_profile.location,
                    "skills": decrypted_profile.skills,
                    "experience_level": decrypted_profile.experience_level.value,
                },
                "applications": [],
                "documents": [],
                "career_dreams": [],
            }

            apps = db.query(ApplicationRecordORM).filter_by(user_id=profile.id).all()
            for app in apps:
                a: Any = app
                export["applications"].append({
                    "id": a.id,
                    "job_id": a.job_id,
                    "status": a.status,
                    "applied_at": str(a.applied_at) if a.applied_at else None,
                })

            docs = db.query(GeneratedDocumentORM).filter_by(user_id=profile.id).all()
            for doc in docs:
                dd: Any = doc
                export["documents"].append({
                    "id": dd.id,
                    "doc_type": dd.doc_type,
                    "created_at": str(dd.created_at) if dd.created_at else None,
                })

            dreams = db.query(CareerDreamORM).filter_by(user_id=profile.id).all()
            for dream in dreams:
                dr: Any = dream
                export["career_dreams"].append({
                    "id": dr.id,
                    "dream_role": dr.dream_role,
                    "feasibility_score": dr.feasibility_score,
                })

            return ExportResponse(data=export, format="json", message="Export complete.")
        finally:
            db.close()

    @router.delete("/", response_model=DeleteResponse)
    @limiter.limit("1/minute")
    async def delete_user_data(
        request: Request,
        session_id: str = session_dep,
    ):
        """Cascading delete of all user data."""
        from src.models import UserProfileORM, init_db
        from src.session_store import get_session_profile

        profile = get_session_profile(session_id)
        db = init_db()
        try:
            user = db.query(UserProfileORM).filter_by(id=profile.id).first()
            if not user:
                return DeleteResponse(deleted=False, message="No user data found.")
            db.delete(user)
            db.commit()
            return DeleteResponse(deleted=True, message="All user data deleted.")
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
