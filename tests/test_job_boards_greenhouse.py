"""Tests for the Greenhouse public job-board adapter."""
from __future__ import annotations

import pytest
import httpx

from src.job_boards_greenhouse import (
    _normalise,
    _query_matches,
    _strip_html,
    fetch_all,
    fetch_board,
)


# ── Fixture: a fake Greenhouse payload close enough to the live shape. ────

_GREENHOUSE_PAYLOAD = {
    "jobs": [
        {
            "id": 4012345,
            "title": "Senior Backend Engineer - Billing",
            "updated_at": "2026-04-01T12:00:00-07:00",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/4012345",
            "location": {"name": "San Francisco, CA, USA"},
            "offices": [{"id": 42, "name": "SF HQ"}],
            "content": (
                "&lt;p&gt;We're looking for a strong <em>Python</em> engineer "
                "to work on payments infrastructure. You will own services "
                "end-to-end.&lt;/p&gt;"
            ),
            "company_name": "Acme Labs",
        },
        {
            "id": 4012346,
            "title": "Product Designer",
            "updated_at": "2026-04-02T09:00:00-07:00",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/4012346",
            "location": {"name": "Remote - Americas"},
            "content": "<p>Design roles for our onboarding surfaces.</p>",
            "company_name": "Acme Labs",
        },
        {
            "id": 4012347,
            "title": "Senior Python Engineer",
            "updated_at": "2026-04-03T10:00:00-07:00",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/4012347",
            "location": {"name": "Berlin"},
            "content": "<p>Join our backend team in Berlin.</p>",
            "company_name": "Acme Labs",
        },
    ]
}


def _make_mock_client(payload: dict) -> httpx.AsyncClient:
    """Return an httpx.AsyncClient wired to a MockTransport that always
    responds with *payload*. Used by fetch_board tests so we never hit
    the real Greenhouse API."""
    def _handler(request: httpx.Request) -> httpx.Response:
        assert "boards-api.greenhouse.io" in str(request.url)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(_handler)
    return httpx.AsyncClient(transport=transport, timeout=5.0)


# ── Pure-function tests (no network) ──────────────────────────────────────

class TestStripHtml:
    def test_removes_tags_and_entities(self):
        raw = "<p>Hello &amp; welcome<br/><strong>Python</strong> role</p>"
        assert _strip_html(raw) == "Hello & welcome Python role"

    def test_empty_input(self):
        assert _strip_html("") == ""
        assert _strip_html(None) == ""  # type: ignore[arg-type]


class TestQueryMatches:
    def test_all_tokens_must_hit(self):
        assert _query_matches("python backend", "Senior Backend Engineer", "We use Python daily")
        assert not _query_matches("python backend", "Product Designer", "Figma and UX")

    def test_short_tokens_skipped(self):
        # "in" is under 3 chars → ignored, so the match depends only on "python"
        assert _query_matches("python in sf", "Python Engineer", "Remote")

    def test_empty_query_allows_all(self):
        assert _query_matches("", "Anything", "Anything")


class TestNormalise:
    def test_happy_path_sf(self):
        job = _GREENHOUSE_PAYLOAD["jobs"][0]
        norm = _normalise(job, "acme")
        assert norm["job_id"] == "greenhouse-acme-4012345"
        assert norm["job_title"] == "Senior Backend Engineer - Billing"
        assert norm["employer_name"] == "Acme Labs"
        assert norm["job_city"] == "San Francisco"
        assert norm["job_state"] == "CA"
        assert norm["job_country"] == "USA"
        assert norm["job_is_remote"] is False
        # HTML stripped and entities unescaped
        assert "Python" in norm["job_description"]
        assert "<" not in norm["job_description"]
        assert norm["_source"] == "Greenhouse"
        assert norm["job_apply_link"].endswith("/4012345")
        assert norm["job_publisher"] == "Greenhouse"

    def test_remote_detection(self):
        job = _GREENHOUSE_PAYLOAD["jobs"][1]
        norm = _normalise(job, "acme")
        assert norm["job_is_remote"] is True
        assert norm["job_city"] == "Remote - Americas" or "Remote" in norm["job_city"]

    def test_missing_id_still_yields_stable_prefix(self):
        job = {"title": "x", "location": {"name": "Berlin"}, "content": ""}
        norm = _normalise(job, "mystery")
        assert norm["job_id"].startswith("greenhouse-mystery")


# ── Network-mocked tests for fetch_board / fetch_all ──────────────────────

class TestFetchBoard:
    @pytest.mark.asyncio
    async def test_fetch_filters_by_query(self):
        async with _make_mock_client(_GREENHOUSE_PAYLOAD) as c:
            results = await fetch_board("acme", "python backend", client=c)
        titles = [r["job_title"] for r in results]
        # Both "Senior Backend Engineer - Billing" and
        # "Senior Python Engineer" should match; "Product Designer" must not.
        assert "Product Designer" not in titles
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_fetch_empty_query_returns_all(self):
        async with _make_mock_client(_GREENHOUSE_PAYLOAD) as c:
            results = await fetch_board("acme", "", client=c)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_fetch_handles_bad_payload(self):
        async with _make_mock_client({"jobs": "not-a-list"}) as c:
            results = await fetch_board("acme", "python", client=c)
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_swallows_http_errors(self):
        def _handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")
        transport = httpx.MockTransport(_handler)
        async with httpx.AsyncClient(transport=transport, timeout=5.0) as c:
            results = await fetch_board("acme", "python", client=c)
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_board_hits_correct_url(self):
        captured: dict[str, httpx.URL] = {}

        def _handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = request.url
            return httpx.Response(200, json={"jobs": []})

        transport = httpx.MockTransport(_handler)
        async with httpx.AsyncClient(transport=transport, timeout=5.0) as c:
            await fetch_board("stripe", "", client=c)
        assert "boards-api.greenhouse.io" in str(captured["url"])
        assert "/boards/stripe/jobs" in str(captured["url"])
        assert "content=true" in str(captured["url"])


class TestFetchAll:
    @pytest.mark.asyncio
    async def test_fetch_all_merges_boards(self):
        # Each board returns the same payload, merged into one list.
        async with _make_mock_client(_GREENHOUSE_PAYLOAD) as c:
            results = await fetch_all(["acme", "beta"], "python", client=c)
        # 2 boards × 2 matching jobs = 4 (dedup happens downstream in search_jobs_live)
        assert len(results) == 4

    @pytest.mark.asyncio
    async def test_fetch_all_empty_tokens(self):
        results = await fetch_all([], "python")
        assert results == []
