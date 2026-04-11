# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Lint:** `ruff check .` (autofix: `ruff check --fix .`)
- **Type check:** `pyright`
- **Test all:** `pytest`
- **Test single:** `pytest tests/test_models.py::test_user_profile_deduplication -v`
- **Run CLI:** `python main.py`
- **Run API:** `uvicorn api:app --reload`

## Architecture

Privacy-first AI job application agent powered by Claude's tool-use API. Local SQLite database, no external data uploads.

### Dual model layer
- **Pydantic models** (`src/models.py`) are the public API and in-memory representations.
- **SQLAlchemy ORM models** (same file) are the persistence layer. Uses sync SQLAlchemy 1.x-style `session.query()`, not async 2.0 `select()`.

### Agentic loop (`src/agent.py`)
`JobAgent.chat()` runs a tool-use loop: user message -> Claude decides which tools to call -> orchestrator executes tools -> results fed back -> loop until `stop_reason == "end_turn"`. Nine tools are exposed (search_jobs, get_market_insights, get_application_tips, generate_resume, generate_cover_letter, track_application, update_application, get_analytics, get_feedback_analysis).

### Key modules
- `src/agent.py` — Orchestrator wiring all subsystems; tool JSON schemas + dispatcher
- `src/job_search.py` — `JobSearchEngine` (mock data + LLM scoring) and `MarketIntelligenceService`
- `src/document_generator.py` — Resume/cover letter generation with tailoring notes
- `src/analytics.py` — `ApplicationTracker` CRUD + metrics + LLM-generated insights
- `src/privacy.py` — AES-256-GCM encryption, PII scrubbing, protected attribute stripping
- `src/ui.py` — Rich-based interactive CLI
- `api.py` — FastAPI layer with in-memory session store (session_id -> JobAgent)
- `config/settings.py` — All env-driven config; supports OpenRouter as alternative LLM provider

### Privacy pipeline
PII flows through three gates before reaching Claude: `strip_protected_attributes()` removes demographic fields, `sanitise_for_llm()` keeps only safe fields (skills, location, etc.), `scrub_pii()` redacts emails/phones via regex. PII at rest is AES-256-GCM encrypted.

### Test DB isolation
Tests monkeypatch `DB_PATH` in **both** `config.settings` and `src.models` (the latter imports it as a local name). Missing either patch causes cross-test DB leakage.

### Job cache serialization (`routers/_job_serializer.py`)
`agent._job_cache` holds heterogeneous values — raw JSearch/Adzuna dicts from the live API **and** Pydantic `JobListing` instances from the agent tool-use path. Every read handler in `routers/jobs.py` goes through `cached_to_job_detail(job_id, cached)` (which normalizes via `normalize_cached_job`) rather than branching on `isinstance(cached, dict)`. Do not re-introduce ad-hoc `cached.get("job_title", cached.get("title", ""))` projections — use the helper.

### Cross-provider search dedup
`src/job_search.py::search_jobs_live` dedupes in two passes: exact `job_id` then a `(normalized_apply_url, normalized_title, normalized_company)` fingerprint (`_dedup_fingerprint`). Required because JSearch and Adzuna assign different IDs to the same posting.

### Health probes
`/healthz` is the liveness probe (no DB, always 200). `/readyz` is the readiness probe (DB-gated, 503 on failure). `/api/health` remains for back-compat dashboards but new orchestrator configs should use the split pair.

### CSP inline-script hashes
`api.py` computes SHA-256 hashes of the inline `<script>` blocks in `frontend/index.html` at module load and emits them as CSP `script-src` hash sources. `'unsafe-inline'` is deliberately absent from `script-src`; if you add a new inline script, it picks up a fresh hash on restart. `'unsafe-eval'` is still required by the Tailwind Play CDN JIT (tracked as a future cleanup).

## Rules

- All LLM response text access must use `cast(TextBlock, response.content[0])` for type safety
- All endpoints return Pydantic models, not raw dicts
- Liveness / readiness probes must remain split (`/healthz` no-DB, `/readyz` DB-gated); `/api/health` is back-compat only
- Read handlers touching `agent._job_cache` must go through `routers._job_serializer.cached_to_job_detail`
- Adding a new agent tool: (1) add JSON schema to `TOOLS` in agent.py, (2) add `_tool_<name>` method, (3) register in `_dispatch_tool`
- Save-on-unique patterns (e.g. `save_job`) must use INSERT + catch `IntegrityError`, never the check-then-insert anti-pattern

## Completion Protocol

Before marking any task complete:
1. `ruff check .`
2. `pyright` (0 errors)
3. `pytest` (all pass)
4. Verify no `.env` files or secrets in changes

## Skills

Framework-specific knowledge in `.claude/skills/`:
- `@.claude/skills/fastapi/` — FastAPI patterns
- `@.claude/skills/security-api/` — API security practices
- `@.claude/skills/ai-prompts/` — AI/LLM prompt patterns
