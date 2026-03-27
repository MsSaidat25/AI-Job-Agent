# Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com). All Rights Reserved.
# avien@aviensolutions.com
"""
Email Service -- Transactional emails via Resend.

Provides a thin wrapper around the Resend API for sending application
status notifications, interview reminders, and other transactional emails.

Usage:
    from src.email_service import send_email, send_application_update

    # Generic email
    send_email(to="user@example.com", subject="Hello", html="<p>Hi</p>")

    # Application status update
    send_application_update(
        to="user@example.com",
        job_title="Senior Engineer",
        company="Acme Corp",
        new_status="interview_scheduled",
    )
"""
from __future__ import annotations

import html as html_mod
import logging
from typing import Any

from config.settings import EMAIL_FROM, RESEND_API_KEY

logger = logging.getLogger(__name__)


_resend_mod = None


def _get_resend():
    """Lazy-import resend and set API key once."""
    global _resend_mod
    if _resend_mod is None:
        import resend
        resend.api_key = RESEND_API_KEY
        _resend_mod = resend
    return _resend_mod


def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    text: str = "",
) -> Any | None:
    """Send a transactional email via Resend.

    Returns the Resend response on success, or None on failure.
    Silently returns None when RESEND_API_KEY is not configured (dev mode).
    """
    if not RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set, skipping email to %s", to)
        return None

    try:
        resend = _get_resend()
        to_list = [to] if isinstance(to, str) else to
        params: Any = {
            "from": EMAIL_FROM,
            "to": to_list,
            "subject": subject,
            "html": html,
        }
        if text:
            params["text"] = text
        response = resend.Emails.send(params)
        logger.info("Email sent successfully: %s", subject)
        return response
    except Exception:
        logger.exception("Failed to send email")
        return None


def send_application_update(
    to: str,
    job_title: str,
    company: str,
    new_status: str,
) -> Any | None:
    """Send an application status update notification."""
    status_labels = {
        "submitted": "Application Submitted",
        "under_review": "Under Review",
        "interview_scheduled": "Interview Scheduled",
        "offer_received": "Offer Received!",
        "rejected": "Application Update",
        "withdrawn": "Application Withdrawn",
    }
    label = status_labels.get(new_status, new_status.replace("_", " ").title())

    safe_label = html_mod.escape(label)
    safe_job_title = html_mod.escape(job_title)
    safe_company = html_mod.escape(company)

    body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a1a2e;">{safe_label}</h2>
        <p>Your application for <strong>{safe_job_title}</strong> at
        <strong>{safe_company}</strong> has been updated.</p>
        <p style="padding: 12px; background: #f0f0f5; border-radius: 6px;">
            Status: <strong>{safe_label}</strong>
        </p>
        <p style="color: #666; font-size: 14px;">
            Log in to your AI Job Agent dashboard for more details.
        </p>
    </div>
    """

    return send_email(
        to=to,
        subject=f"{label} - {job_title} at {company}",
        html=body,
    )


def send_interview_reminder(
    to: str,
    job_title: str,
    company: str,
    interview_date: str,
) -> Any | None:
    """Send an interview reminder email."""
    safe_job_title = html_mod.escape(job_title)
    safe_company = html_mod.escape(company)
    safe_interview_date = html_mod.escape(interview_date)

    body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a1a2e;">Interview Reminder</h2>
        <p>You have an upcoming interview for <strong>{safe_job_title}</strong>
        at <strong>{safe_company}</strong>.</p>
        <p style="padding: 12px; background: #e8f5e9; border-radius: 6px;">
            Date: <strong>{safe_interview_date}</strong>
        </p>
        <p style="color: #666; font-size: 14px;">
            Good luck! Check your AI Job Agent dashboard for preparation tips.
        </p>
    </div>
    """

    return send_email(
        to=to,
        subject=f"Interview Reminder - {job_title} at {company}",
        html=body,
    )
