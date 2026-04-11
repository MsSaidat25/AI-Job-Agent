"""Shared helpers for serializing cached jobs into API responses.

The in-memory ``agent._job_cache`` stores heterogeneous values: raw JSearch /
Adzuna dicts from the live API *and* Pydantic ``JobListing`` models emitted by
the agent's tool-use layer. Every handler in routers/jobs.py used to branch
on ``isinstance(cached, dict)`` and repeat the same 15-line projection into a
``JobDetailResponse``; the duplication drifted (different handlers extracted
different fields) and hid a couple of ``None``-coercion bugs.

This module exposes two functions:

* ``normalize_cached_job`` - coerce a cached value (dict or Pydantic) into a
  single canonical dict with the keys the API contract needs.
* ``cached_to_job_detail`` - normalize + project into a ``JobDetailResponse``.
"""
from __future__ import annotations

from typing import Any, Optional

from routers.schemas import JobDetailResponse


def _build_location_from_cached(cached: dict[str, Any]) -> str:
    """Build a location string from a cached JSearch dict.

    JSearch frequently returns ``None`` for individual city/state/country
    fields, so we defensively coerce each component to str before joining.
    """
    parts = [str(cached.get(k) or "") for k in ("job_city", "job_state", "job_country")]
    built = ", ".join(p for p in parts if p)
    return built or str(cached.get("location") or "")


def normalize_cached_job(cached: Any) -> dict[str, Any]:
    """Return a canonical dict for a cached job value.

    Accepts either a raw provider dict (JSearch/Adzuna/import) or a Pydantic
    ``JobListing`` instance. The returned dict uses the following keys, all
    of which may be empty strings / None but are guaranteed to be present:

        title, company, location, remote_allowed, job_type, description,
        requirements, nice_to_have, salary_min, salary_max, currency,
        posted_date, source_url, source_platform, match_score,
        match_rationale
    """
    if cached is None:
        return {}

    # Raw provider dict path
    if isinstance(cached, dict):
        return {
            "title": str(cached.get("job_title") or cached.get("title") or ""),
            "company": str(cached.get("employer_name") or cached.get("company") or ""),
            "location": _build_location_from_cached(cached),
            "remote_allowed": bool(cached.get("job_is_remote", False)),
            "job_type": str(cached.get("job_employment_type") or "full_time"),
            "description": str(cached.get("job_description") or "")[:3000],
            "requirements": cached.get("requirements") or [],
            "nice_to_have": cached.get("nice_to_have") or [],
            "salary_min": cached.get("job_min_salary"),
            "salary_max": cached.get("job_max_salary"),
            "currency": str(cached.get("currency") or "USD"),
            "posted_date": cached.get("job_posted_at_datetime_utc")
            or cached.get("posted_date"),
            "source_url": str(
                cached.get("job_apply_link")
                or cached.get("redirect_url")
                or cached.get("source_url")
                or ""
            ),
            "source_platform": str(cached.get("_source") or cached.get("source_platform") or ""),
            "match_score": cached.get("_match_score") or cached.get("match_score"),
            "match_rationale": cached.get("_match_rationale") or cached.get("match_rationale"),
        }

    # Pydantic JobListing path
    job_type_raw = getattr(cached, "job_type", None)
    if job_type_raw is None:
        job_type = "full_time"
    elif hasattr(job_type_raw, "value"):
        job_type = job_type_raw.value  # type: ignore[union-attr]
    else:
        job_type = str(job_type_raw)
    posted = getattr(cached, "posted_date", None)
    return {
        "title": getattr(cached, "title", "") or "",
        "company": getattr(cached, "company", "") or "",
        "location": getattr(cached, "location", "") or "",
        "remote_allowed": bool(getattr(cached, "remote_allowed", False)),
        "job_type": job_type,
        "description": (getattr(cached, "description", "") or "")[:3000],
        "requirements": getattr(cached, "requirements", None) or [],
        "nice_to_have": getattr(cached, "nice_to_have", None) or [],
        "salary_min": getattr(cached, "salary_min", None),
        "salary_max": getattr(cached, "salary_max", None),
        "currency": getattr(cached, "currency", "USD") or "USD",
        "posted_date": str(posted) if posted else None,
        "source_url": getattr(cached, "source_url", "") or "",
        "source_platform": getattr(cached, "source_platform", "") or "",
        "match_score": getattr(cached, "match_score", None),
        "match_rationale": getattr(cached, "match_rationale", None),
    }


def cached_to_job_detail(
    job_id: str,
    cached: Any,
    *,
    is_saved: Optional[bool] = None,
) -> JobDetailResponse:
    """Project a cached job value into a ``JobDetailResponse``.

    Returns the canonical DTO used by every read endpoint. ``is_saved`` is
    optional because only a few endpoints know whether the caller has saved
    this job yet.
    """
    n = normalize_cached_job(cached)
    kwargs: dict[str, Any] = {
        "id": job_id,
        "title": n.get("title", ""),
        "company": n.get("company", ""),
        "location": n.get("location", ""),
        "remote_allowed": bool(n.get("remote_allowed", False)),
        "job_type": n.get("job_type", "full_time"),
        "description": n.get("description", ""),
        "requirements": n.get("requirements", []),
        "nice_to_have": n.get("nice_to_have", []),
        "salary_min": n.get("salary_min"),
        "salary_max": n.get("salary_max"),
        "currency": n.get("currency", "USD"),
        "posted_date": str(n["posted_date"]) if n.get("posted_date") else None,
        "source_url": n.get("source_url", ""),
        "source_platform": n.get("source_platform", ""),
        "match_score": n.get("match_score"),
        "match_rationale": n.get("match_rationale"),
    }
    if is_saved is not None:
        kwargs["is_saved"] = is_saved
    return JobDetailResponse(**kwargs)
