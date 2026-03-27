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

## Rules

- All LLM response text access must use `cast(TextBlock, response.content[0])` for type safety
- All endpoints return Pydantic models, not raw dicts
- Health check endpoint must always be available
- Adding a new agent tool: (1) add JSON schema to `TOOLS` in agent.py, (2) add `_tool_<name>` method, (3) register in `_dispatch_tool`

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
