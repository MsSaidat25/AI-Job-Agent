---
name: Security (API)
description: API security best practices
---

# API Security

## Authentication & Authorization
- Use JWT tokens with short expiration (15-30 min)
- Implement refresh token rotation
- Hash passwords with bcrypt (passlib)
- Use `Depends(get_current_user)` on all protected endpoints
- Implement role-based access control (RBAC)

## Input Validation
- Validate all input with Pydantic models
- Set max lengths on string fields
- Validate email formats, URLs, phone numbers
- Reject unexpected fields (Pydantic does this by default)
- Validate file uploads (size, type, extension)

## SQL Injection Prevention
- Use SQLAlchemy ORM — never raw SQL strings
- If raw SQL needed, use `text()` with bound parameters
- Never interpolate user input into queries

## Rate Limiting
- Implement per-IP rate limiting on auth endpoints
- Use sliding window or token bucket algorithms
- Return `429 Too Many Requests` with `Retry-After` header

## CORS
- Whitelist specific origins, never use `*` in production
- Restrict allowed methods and headers
- Set `allow_credentials=True` only when needed

## Error Handling
- Never expose stack traces to clients
- Use generic error messages for auth failures
- Log detailed errors server-side only
- Return structured error responses: `{ error: { code, message } }`

## Secrets Management
- Store secrets in environment variables, never in code
- Use `.env.example` for documentation (no real values)
- Rotate secrets regularly
- Never log secrets or include in error responses
