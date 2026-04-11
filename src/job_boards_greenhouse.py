"""Greenhouse public job-board adapter.

Greenhouse exposes a zero-auth public API for each company's careers board:

    GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

Each hit is normalized into the JSearch-compatible dict shape so the existing
``_to_listing`` / ``_score_job`` / ``_dedup_fingerprint`` pipeline in
``src/job_search.py`` handles it without further changes.

Boards are configured via ``GREENHOUSE_BOARDS`` (comma-separated list of
board slugs, e.g. ``"stripe,shopify,notion"``). Leaving it unset disables
this provider entirely.
"""
from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

GREENHOUSE_BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(s: str) -> str:
    """Strip HTML tags and collapse whitespace from a Greenhouse description."""
    if not s:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", unescape(s))).strip()


def _query_matches(query: str, title: str, description: str) -> bool:
    """Loose keyword match: every whitespace-separated token must appear.

    The Greenhouse public API doesn't accept a search query parameter, so we
    fetch the whole board and filter client-side. Tokens under 3 chars are
    skipped to avoid matching every posting on common stop-word-like input.
    """
    if not query:
        return True
    haystack = f"{title} {description}".lower()
    tokens = [t for t in query.lower().split() if len(t) >= 3]
    if not tokens:
        return True
    return all(t in haystack for t in tokens)


def _normalise(job: dict[str, Any], board_token: str) -> dict[str, Any]:
    """Convert a Greenhouse job dict into the JSearch-compatible shape.

    Preserves ``job_id`` as a provider-prefixed value so we can tell it came
    from Greenhouse and won't collide with JSearch/Adzuna IDs.
    """
    gid = str(job.get("id") or "")
    location = job.get("location") or {}
    location_name = str(location.get("name") or "")

    # Greenhouse returns a single free-text "location.name" like
    # "San Francisco, CA" or "Remote - EU". Split best-effort into
    # city / state / country, falling back to the whole string as city.
    parts = [p.strip() for p in location_name.split(",") if p.strip()]
    if len(parts) >= 3:
        city, state, country = parts[0], parts[1], parts[-1]
    elif len(parts) == 2:
        city, state, country = parts[0], parts[1], ""
    else:
        city, state, country = location_name, "", ""

    content_html = str(job.get("content") or "")
    description = _strip_html(content_html)
    is_remote = "remote" in location_name.lower() or "remote" in description[:500].lower()

    offices = job.get("offices") or []
    office_name = ""
    if offices and isinstance(offices, list):
        office_name = str(offices[0].get("name") or "") if isinstance(offices[0], dict) else ""

    return {
        "job_id": f"greenhouse-{board_token}-{gid}" if gid else f"greenhouse-{board_token}",
        "job_title": str(job.get("title") or ""),
        "employer_name": str(job.get("company_name") or office_name or board_token.title()),
        "job_description": description,
        "job_city": city,
        "job_state": state,
        "job_country": country,
        "job_is_remote": is_remote,
        "job_employment_type": "full_time",
        "job_min_salary": None,
        "job_max_salary": None,
        "job_posted_at_datetime_utc": str(job.get("updated_at") or ""),
        "job_publisher": "Greenhouse",
        "job_apply_link": str(job.get("absolute_url") or ""),
        "_source": "Greenhouse",
    }


async def fetch_board(
    board_token: str,
    query: str,
    client: Optional[httpx.AsyncClient] = None,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """Fetch and filter one Greenhouse board's jobs.

    Returns JSearch-compatible dicts. Network/parse failures are logged and
    swallowed — the caller's other providers still get their chance.
    """
    url = GREENHOUSE_BASE_URL.format(token=board_token)
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.get(url, params={"content": "true"})
                r.raise_for_status()
                payload = r.json()
        else:
            r = await client.get(url, params={"content": "true"})
            r.raise_for_status()
            payload = r.json()
    except Exception:
        logger.exception("Greenhouse fetch failed for board %s", board_token)
        return []

    jobs_raw = payload.get("jobs") or []
    if not isinstance(jobs_raw, list):
        return []

    results: list[dict[str, Any]] = []
    for job in jobs_raw:
        if not isinstance(job, dict):
            continue
        norm = _normalise(job, board_token)
        if _query_matches(query, norm["job_title"], norm["job_description"]):
            results.append(norm)
    return results


async def fetch_all(
    board_tokens: list[str],
    query: str,
    client: Optional[httpx.AsyncClient] = None,
) -> list[dict[str, Any]]:
    """Fetch every configured board in parallel and merge the results."""
    if not board_tokens:
        return []
    import asyncio as _aio

    coros = [fetch_board(tok, query, client=client) for tok in board_tokens]
    results = await _aio.gather(*coros, return_exceptions=True)

    merged: list[dict[str, Any]] = []
    for tok, res in zip(board_tokens, results):
        if isinstance(res, BaseException):
            logger.warning("Greenhouse board %s raised: %s", tok, res)
            continue
        merged.extend(res)
    return merged
