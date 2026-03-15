# AIJobAgent

## WHAT
- FastAPI + Python + SQLAlchemy 2.0 + PostgreSQL + Alembic
- backend/app/ — FastAPI application
- backend/app/api/ — API route handlers
- backend/app/core/ — Config, security, error handling
- backend/app/db/ — Database session and models
- backend/app/models/ — SQLAlchemy models
- backend/app/schemas/ — Pydantic schemas
- backend/tests/ — Pytest tests
- backend/alembic/ — Database migrations

## HOW
- Lint: `ruff check .`
- Type check: `pyright`
- Test: `pytest`
- Build: `docker build -t app .`
- Dev: `uvicorn app.main:app --reload`

## RULES
- Never commit `.env` files or secrets
- Never modify migration files directly — generate new migrations instead
- All API responses use structured error format: `{ error: { code, message } }`
- Never leak stack traces to clients
- Health check endpoints must always be available
- Write tests for new features before marking them complete

## FastAPI Conventions
- Pydantic v2 for all request/response schemas (use model_config, not class Config)
- SQLAlchemy 2.0 async style — use `select()` not `query()`, `async with session` not `session.query`
- Dependency injection via `Depends()` for DB sessions, auth, etc.
- All endpoints return Pydantic models — never return raw dicts
- Use `@asynccontextmanager` lifespan for startup/shutdown
- Database session via `get_db()` dependency (backend/app/db/session.py)
- Error responses use `AppError` classes (backend/app/core/errors.py)
- Use `with_retry` decorator for external service calls
- Alembic for migrations: `alembic revision --autogenerate -m "description"`
- Environment config via Pydantic Settings (backend/app/core/config.py)
- Ruff for linting, pyright for type checking


## Skills
Framework-specific knowledge is in `.claude/skills/` — reference these for deep patterns:
- `@.claude/skills/fastapi/` — FastAPI patterns and conventions
- `@.claude/skills/security-api/` — API security practices
- `@.claude/skills/ai-prompts/` — AI/LLM prompt patterns

## Completion Protocol
Before marking any task complete:
1. Run lint: `ruff check .`
2. Run type check: `pyright`
3. Run tests: `pytest`
4. Verify no `.env` files or secrets in changes
