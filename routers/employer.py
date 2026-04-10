"""Employer portal endpoints."""
from __future__ import annotations


from fastapi import APIRouter, Request, status
from slowapi import Limiter

from routers.schemas import EmployerWaitlistRequest, EmployerWaitlistResponse

router = APIRouter(prefix="/api/employer", tags=["employer"])


def _setup_routes(limiter: Limiter) -> None:
    @router.post(
        "/waitlist",
        status_code=status.HTTP_201_CREATED,
        response_model=EmployerWaitlistResponse,
    )
    @limiter.limit("5/hour")
    async def employer_waitlist(request: Request, body: EmployerWaitlistRequest):
        """Add an employer email to the early-access waitlist."""
        from sqlalchemy.orm import sessionmaker as _sessionmaker

        from src.models import EmployerWaitlistORM, get_engine

        engine = get_engine()
        Session = _sessionmaker(bind=engine)
        with Session() as db:
            existing = db.query(EmployerWaitlistORM).filter_by(email=body.email).first()
            if existing:
                position = db.query(EmployerWaitlistORM).count()
                return EmployerWaitlistResponse(
                    message="You're already on the waitlist!", position=position
                )
            entry = EmployerWaitlistORM(
                email=body.email,
                company_name=body.company_name,
                company_size=body.company_size,
            )
            db.add(entry)
            db.commit()
            position = db.query(EmployerWaitlistORM).count()
        return EmployerWaitlistResponse(
            message="You're on the list! We'll be in touch soon.", position=position
        )
