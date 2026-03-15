---
name: FastAPI
description: FastAPI + SQLAlchemy 2.0 + Pydantic v2 patterns
---

# FastAPI Backend

## Endpoint Patterns
- Use `APIRouter` for route grouping
- Type all parameters: path params, query params, request bodies
- Return Pydantic models, not dicts
- Use `Depends()` for dependency injection (DB sessions, auth, config)
- Use `status_code` parameter for non-200 responses

## Pydantic v2
- Use `model_config = ConfigDict(...)` not `class Config`
- Use `model_validator` not `root_validator`
- Use `field_validator` not `validator`
- `from_attributes=True` replaces `orm_mode=True`

## SQLAlchemy 2.0 Async
- Use `select()` statement style, not `session.query()`
- Use `async with async_session() as session` for scoped sessions
- Use `session.execute(select(Model))` then `.scalars().all()`
- Use `session.get(Model, id)` for single lookups
- Never use synchronous session methods

## Error Handling
- Raise `AppError` subclasses, never `HTTPException` with raw strings
- Global exception handler catches unhandled errors
- Never expose stack traces or internal details to clients
- Use structured error format: `{ error: { code, message } }`

## Testing
- Use `httpx.AsyncClient` with `ASGITransport` for async tests
- Use `conftest.py` fixtures for test client and DB setup
- Test both success and error paths
- Use `pytest.mark.asyncio` for async tests
