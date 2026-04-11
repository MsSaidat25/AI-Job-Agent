# Business Rules - AI Job Agent

> Extracted from codebase on 2026-04-11.
> Each rule includes source location, logic description, and testable cases.

---

## BR-01: Session TTL (1 Hour)

**Source:** `src/session_store.py:21-22`
```
_MAX_SESSIONS = 500
_SESSION_TTL_SECONDS = 3600
```

**Logic:** Sessions expire after 3600 seconds (1 hour) of inactivity. The cleanup runs every 60 seconds (`_CLEANUP_INTERVAL = 60`). Expired sessions are removed and their agents closed.

| Test Case | Input | Expected Output |
|---|---|---|
| Session within TTL | Access session at T+3599s | Session found, returns agent |
| Session expired | Access session at T+3601s | 404 "Session not found or profile not set up." |
| TTL reset on access | Touch session at T+3000s, access at T+5000s | Session still valid (last_access updated) |

---

## BR-02: Max Concurrent Sessions (500)

**Source:** `src/session_store.py:20`
```
_MAX_SESSIONS = 500
```

**Logic:** When session count exceeds 500, the oldest session (by `last_access` timestamp) is evicted. This runs during cleanup, not on creation.

| Test Case | Input | Expected Output |
|---|---|---|
| Under limit | 499 sessions, create 1 more | All 500 sessions valid |
| Over limit | 501 sessions exist | Oldest session evicted, count drops to 500 |
| Eviction targets oldest | 501 sessions, oldest is session X | Session X is evicted, all others remain |

---

## BR-03: Authenticated User Session Reuse

**Source:** `src/session_store.py:124-127`

**Logic:** When a user_id is supplied (authenticated flow), if that user already has an active session, the existing session is returned instead of creating a new one. The session is touched (TTL reset).

| Test Case | Input | Expected Output |
|---|---|---|
| First login | create_session(user_id="uid1") | New session created, mapped to uid1 |
| Re-login same user | create_session(user_id="uid1") again | Same session_id returned, TTL reset |
| Different user | create_session(user_id="uid2") | New separate session created |

---

## BR-04: Rate Limits Per Endpoint

**Source:** Various router files (decorator `@limiter.limit()`)

| Endpoint | Limit | Source |
|---|---|---|
| POST /api/session | 30/hour | api.py:205 |
| POST /api/profile | 10/minute | api.py:213 |
| GET /api/profile | 30/minute | api.py:259 |
| POST /api/auth/signup | 10/hour | routers/auth.py:37 |
| POST /api/auth/login | 20/hour | routers/auth.py:69 |
| POST /api/auth/google | 20/hour | routers/auth.py:100 |
| POST /api/auth/refresh | 30/hour | routers/auth.py:132 |
| DELETE /api/auth/session | 30/hour | routers/auth.py:160 |
| POST /api/onboarding/generate-tasks | 15/minute | routers/onboarding.py:39 |
| POST /api/onboarding/generate-skills | 15/minute | routers/onboarding.py:45 |
| POST /api/onboarding/generate-identity-statement | 10/minute | routers/onboarding.py:54 |
| POST /api/onboarding/confirm-profile | 10/minute | routers/onboarding.py:69 |
| POST /api/jobs/search | 10/minute | routers/jobs.py:38 |
| POST /api/jobs/search/v2 | 10/minute | routers/jobs.py:64 |
| GET /api/jobs/{id} | 30/minute | routers/jobs.py:156 |
| POST /api/jobs/{id}/save | 30/minute | routers/jobs.py:225 |
| DELETE /api/jobs/{id}/save | 30/minute | routers/jobs.py:295 |
| GET /api/jobs/saved | 30/minute | routers/jobs.py:319 |
| POST /api/jobs/import | 30/minute | routers/jobs.py:358 |
| POST /api/market-insights | 10/minute | routers/jobs.py:413 |
| POST /api/application-tips | 10/minute | routers/jobs.py:430 |
| POST /api/documents/resume | 5/minute | routers/jobs.py:447 |
| POST /api/documents/cover-letter | 5/minute | routers/jobs.py:471 |
| POST /api/chat | 15/minute | routers/chat.py:34 |
| DELETE /api/chat/reset | 10/minute | routers/chat.py:47 |
| POST /api/parse-resume | 5/minute | routers/chat.py:54 |
| POST /api/applications | 10/minute | routers/applications.py:26 |
| PUT /api/applications/{id} | 10/minute | routers/applications.py:50 |
| GET /api/analytics | 5/minute | routers/applications.py:69 |
| GET /api/feedback | 5/minute | routers/applications.py:82 |
| POST /api/employer/waitlist | 5/hour | routers/employer.py:19 |
| GET /api/documents/templates | 30/minute | routers/documents.py:53 |
| GET /api/documents/templates/{id} | 30/minute | routers/documents.py:62 |
| POST /api/documents/export | 5/minute | routers/documents.py:79 |
| POST /api/documents/export-content | 10/minute | routers/documents.py:138 |
| GET /api/kanban/board | 30/minute | routers/kanban.py:76 |
| PUT /api/kanban/cards/{id}/move | 30/minute | routers/kanban.py:119 |
| GET /api/kanban/cards/{id} | 30/minute | routers/kanban.py:153 |
| GET /api/dashboard/summary | 30/minute | routers/dashboard.py:92 |
| GET /api/dashboard/applications | 30/minute | routers/dashboard.py:114 |
| GET /api/dashboard/activity | 30/minute | routers/dashboard.py:152 |
| GET /api/dashboard/skills | 15/minute | routers/dashboard.py:185 |
| POST /api/career/dream | 5/minute | routers/career.py:70 |
| GET /api/career/dream/{id}/detail | 30/minute | routers/career.py:100 |
| POST /api/career/dream/{id}/find-jobs | 10/minute | routers/career.py:129 |
| POST /api/career/dream/{id}/save | 10/minute | routers/career.py:160 |
| GET /api/career/dreams | 30/minute | routers/career.py:194 |
| GET /api/career/report | 5/minute | routers/career.py:227 |
| POST /api/salary/calibrate | 10/minute | routers/salary.py:55 |
| POST /api/salary/negotiate | 5/minute | routers/salary.py:80 |
| POST /api/salary/compare-offers | 5/minute | routers/salary.py:106 |
| GET /api/feed/daily | 10/minute | routers/feed.py:36 |
| POST /api/feed/refresh | 3/minute | routers/feed.py:59 |
| GET /api/nudges/pending | 30/minute | routers/nudges.py:67 |
| POST /api/nudges/{id}/respond | 10/minute | routers/nudges.py:104 |
| GET /api/nudges/{id}/draft-email | 5/minute | routers/nudges.py:135 |
| PUT /api/nudges/{id}/pause | 10/minute | routers/nudges.py:170 |
| PUT /api/nudges/settings | 10/minute | routers/nudges.py:197 |
| GET /api/auto-apply/settings | 30/minute | routers/auto_apply.py:60 |
| PUT /api/auto-apply/settings | 10/minute | routers/auto_apply.py:87 |
| GET /api/auto-apply/queue | 30/minute | routers/auto_apply.py:128 |
| POST /api/auto-apply/queue/{id}/approve | 10/minute | routers/auto_apply.py:165 |
| POST /api/auto-apply/queue/{id}/reject | 10/minute | routers/auto_apply.py:192 |
| GET /api/auto-apply/briefing | 5/minute | routers/auto_apply.py:219 |
| GET /api/interview/{id}/prep | 5/minute | routers/interview.py:56 |
| GET /api/interview/{id}/company-brief | 10/minute | routers/interview.py:80 |
| GET /api/interview/{id}/questions | 10/minute | routers/interview.py:101 |
| POST /api/interview/{id}/debrief | 5/minute | routers/interview.py:141 |
| GET /api/email/auth/gmail | 5/minute | routers/email_oauth.py:73 |
| GET /api/email/auth/gmail/callback | 10/minute | routers/email_oauth.py:86 |
| GET /api/email/auth/status | 30/minute | routers/email_oauth.py:109 |
| DELETE /api/email/auth/gmail | 5/minute | routers/email_oauth.py:134 |
| POST /api/email/compose | 5/minute | routers/email_oauth.py:158 |
| GET /api/email/inbox | 10/minute | routers/email_oauth.py:187 |
| GET /api/insights/outcome-learning | 5/minute | routers/insights.py:40 |
| GET /api/insights/rejection-patterns | 5/minute | routers/insights.py:59 |
| GET /api/insights/restrategize | 5/minute | routers/insights.py:78 |
| GET /api/insights/weekly-report | 3/minute | routers/insights.py:95 |
| GET /api/account/export | 3/minute | routers/account.py:37 |
| DELETE /api/account/ | 1/minute | routers/account.py:107 |
| POST /api/offers/ | 10/minute | routers/offers.py:62 |
| GET /api/offers/ | 30/minute | routers/offers.py:120 |
| GET /api/offers/compare | 5/minute | routers/offers.py:160 |

---

## BR-05: Auto-Apply Confidence Threshold (Default 85%)

**Source:** `src/auto_apply_service.py:15`
```
confidence_threshold: float = 0.85
```

**Logic:** Jobs are only auto-applied when the match confidence score meets or exceeds the user's threshold (default 0.85 = 85%). The scoring starts at 50 and adds up to 30 for skills overlap, 15 for role match, and more for location match.

| Test Case | Input | Expected Output |
|---|---|---|
| Below threshold | Job scores 0.80, threshold is 0.85 | Job NOT auto-applied, queued for review |
| At threshold | Job scores 0.85, threshold is 0.85 | Job auto-applied |
| Above threshold | Job scores 0.95, threshold is 0.85 | Job auto-applied |
| Custom threshold | User sets threshold to 0.70, job scores 0.72 | Job auto-applied |

---

## BR-06: Auto-Apply Max Daily (Default 5)

**Source:** `src/auto_apply_service.py:18`
```
max_daily: int = 5
```

**Logic:** Maximum number of auto-applied jobs per day. User-configurable between 1 and 50.

| Test Case | Input | Expected Output |
|---|---|---|
| Under limit | 4 auto-applies today, 1 new match | Auto-apply proceeds |
| At limit | 5 auto-applies today, 1 new match | Queued for next day |
| Custom limit | User sets max_daily=10, 6 auto-applies today | Auto-apply proceeds |

---

## BR-07: Auto-Apply Safe Channels

**Source:** `src/auto_apply_service.py:17`
```
safe_channels: list[str] = Field(default_factory=lambda: ["email", "career_page"])
```

**Logic:** Only applications through channels listed in safe_channels are auto-applied. Default channels are "email" and "career_page".

| Test Case | Input | Expected Output |
|---|---|---|
| Email channel | Channel="email", safe_channels=["email","career_page"] | Allowed |
| LinkedIn channel | Channel="linkedin", safe_channels=["email","career_page"] | Blocked, needs manual review |
| Custom channels | User adds "linkedin" to safe_channels | LinkedIn applications allowed |

---

## BR-08: Nudge Schedule (Day 3/7/14/21/30)

**Source:** `src/nudge_service.py:18-24`
```python
_NUDGE_SCHEDULE = [
    (3, "silent", "Application recently submitted. No action needed yet."),
    (7, "check_in", "Have you heard back from {company}?"),
    (14, "reminder", "Still no word after 2 weeks from {company}."),
    (21, "follow_up", "Time to send a follow-up email to {company}."),
    (30, "stale", "No response after a month from {company}. Consider moving on."),
]
```

**Logic:** After submission, nudges escalate: Day 3 is silent (no user action), Day 7 is a check-in, Day 14 a reminder, Day 21 prompts a follow-up email, and Day 30 suggests moving on.

| Test Case | Input | Expected Output |
|---|---|---|
| Day 3 | 3 days since submission | nudge_type="silent", no user notification |
| Day 7 | 7 days since submission | nudge_type="check_in", message asks if heard back |
| Day 14 | 14 days since submission | nudge_type="reminder" |
| Day 21 | 21 days since submission | nudge_type="follow_up", prompts email |
| Day 30 | 30 days since submission | nudge_type="stale", suggests moving on |
| User responds "heard_back" | respond with heard_back at any point | Nudge status changes to "completed" |
| User responds "rejected" | respond with rejected | Nudge status changes to "completed" |

---

## BR-09: Nudge Settings Validation

**Source:** `routers/nudges.py:40-43`
```python
default_interval_days: int = Field(default=7, ge=1, le=60)
max_nudges: int = Field(default=3, ge=1, le=10)
auto_pause_after: int = Field(default=3, ge=1, le=10)
```

| Test Case | Input | Expected Output |
|---|---|---|
| Valid interval | default_interval_days=14 | Accepted |
| Interval too low | default_interval_days=0 | 422 (ge=1) |
| Interval too high | default_interval_days=61 | 422 (le=60) |
| Max nudges valid | max_nudges=5 | Accepted |
| Max nudges too high | max_nudges=11 | 422 (le=10) |

---

## BR-10: Job Cache Max Size (200)

**Source:** `src/agent.py:57`
```
self._job_cache_max = 200
```

**Logic:** The in-memory job cache per agent is capped at 200 entries. When full, the oldest entry (first key via `next(iter(...))`) is evicted before adding a new one.

| Test Case | Input | Expected Output |
|---|---|---|
| Under limit | Cache has 199 jobs, add 1 | All 200 jobs in cache |
| At limit | Cache has 200 jobs, add 1 new | Oldest job evicted, new job added, cache still 200 |
| Multiple evictions | Cache has 200 jobs, search returns 10 new | 10 oldest evicted, 10 new added |

---

## BR-11: Conversation History Max (50 Messages)

**Source:** `src/agent.py:60`
```
self._max_history = 50
```

**Logic:** Conversation history is truncated to 50 messages. When exceeded, the first message is kept and the rest are trimmed from the middle (keeps first + last 49).

| Test Case | Input | Expected Output |
|---|---|---|
| Under limit | 49 messages, send 1 more | All 50 messages retained |
| Over limit | 50 messages, send 1 more | First message + last 49 kept (message #2 dropped) |

---

## BR-12: Profile Field Validation

**Source:** `routers/schemas.py:15-33`

| Field | Constraint | Source |
|---|---|---|
| name | max_length=200, required | schemas.py:16 |
| email | EmailStr (valid email format), required | schemas.py:17 |
| phone | max_length=30, optional | schemas.py:18 |
| location | max_length=200, required | schemas.py:19 |
| skills | max_length=100 items | schemas.py:20 |
| experience_level | ExperienceLevel enum (entry/mid/senior/lead/executive) | schemas.py:21 |
| years_of_experience | ge=0, le=70 | schemas.py:22 |
| education | max_length=20 items | schemas.py:23 |
| work_history | max_length=50 items | schemas.py:24 |
| desired_roles | max_length=20 items | schemas.py:25 |
| desired_job_types | max_length=10 items, JobType enum | schemas.py:26 |
| preferred_currency | max_length=5 | schemas.py:27 |
| desired_salary_min | ge=0, optional | schemas.py:28 |
| desired_salary_max | ge=0, optional | schemas.py:29 |
| languages | max_length=30 items | schemas.py:30 |
| certifications | max_length=50 items | schemas.py:31 |
| portfolio_url | max_length=500, must start with http(s):// | schemas.py:32,35-42 |
| linkedin_url | max_length=500, must start with http(s):// | schemas.py:33,35-42 |

---

## BR-13: Skills and Desired Roles Deduplication

**Source:** `src/models.py:78-81`
```python
@field_validator("skills", "desired_roles", mode="before")
@classmethod
def deduplicate(cls, v: list) -> list:
    return list(dict.fromkeys(v))
```

**Logic:** Duplicate entries in skills and desired_roles are automatically removed while preserving order.

| Test Case | Input | Expected Output |
|---|---|---|
| No duplicates | skills=["Python","Java"] | ["Python","Java"] |
| With duplicates | skills=["Python","Python","Java"] | ["Python","Java"] |
| Order preserved | skills=["Java","Python","Java"] | ["Java","Python"] |

---

## BR-14: Resume Tone Validation

**Source:** `routers/schemas.py:9,63-69`
```python
_ALLOWED_TONES = {"professional", "creative", "technical", "executive", "academic"}
```

**Logic:** Resume generation only accepts one of the five allowed tones.

| Test Case | Input | Expected Output |
|---|---|---|
| Valid tone | tone="professional" | Accepted |
| Valid tone (case) | tone="PROFESSIONAL" | Accepted (lowered) |
| Invalid tone | tone="casual" | 422 "tone must be one of: academic, creative, executive, professional, technical" |

---

## BR-15: Resume File Upload Limits

**Source:** `routers/chat.py:61-79`
```python
_ALLOWED_MIME = {"application/pdf", "text/plain", "text/csv", "text/markdown"}
_MAX_UPLOAD = 5_000_000  # 5 MB
```

| Test Case | Input | Expected Output |
|---|---|---|
| Valid PDF | 2 MB PDF | Accepted, parsed |
| Valid text | 100 KB .txt file | Accepted, parsed |
| Too large | 6 MB PDF | 400 "File too large (max 5 MB)." |
| Invalid type | .xlsx file | 400 "Unsupported file type." |
| No content type | File with no MIME | 400 "File type not detected." |

---

## BR-16: Auth Required in Production

**Source:** `config/settings.py:198-204`
```python
def validate_production_config() -> None:
    if ENV == "production" and not AUTH_ENABLED:
        raise SystemExit(
            "FATAL: AUTH_ENABLED must be true when ENV=production."
        )
```

**Logic:** The application refuses to start if ENV=production and AUTH_ENABLED=false.

| Test Case | Input | Expected Output |
|---|---|---|
| Production + auth | ENV=production, AUTH_ENABLED=true | App starts normally |
| Production + no auth | ENV=production, AUTH_ENABLED=false | SystemExit with fatal message |
| Development + no auth | ENV=development, AUTH_ENABLED=false | App starts normally |

---

## BR-17: Auth Token Verification

**Source:** `src/auth.py:130-162`

**Logic:** When AUTH_ENABLED=true, requests require `Authorization: Bearer <token>`. Token is verified against Google's public signing keys. When AUTH_ENABLED=false, `X-Session-ID` header is used instead.

| Test Case | Input | Expected Output |
|---|---|---|
| AUTH=true, valid token | Bearer <valid_jwt> | user_id extracted from sub claim |
| AUTH=true, no header | No Authorization header | 401 "Authorization header required" |
| AUTH=true, expired | Bearer <expired_jwt> | 401 "Token expired" |
| AUTH=true, invalid | Bearer <garbage> | 401 "Invalid authentication credentials" |
| AUTH=false, session set | X-Session-ID: abc123 | Returns "abc123" as user_id |
| AUTH=false, no session | No X-Session-ID | 400 "X-Session-ID header is required." |

---

## BR-18: Protected Attributes (Bias Mitigation)

**Source:** `config/settings.py:192`
```python
PROTECTED_ATTRIBUTES = {"gender", "age", "ethnicity", "religion", "nationality"}
```

**Logic:** These attributes are stripped from profile data before it reaches the LLM. The `strip_protected_attributes()` function in `src/privacy.py` removes any keys matching these names. This prevents the AI from using demographic information in its decisions.

| Test Case | Input | Expected Output |
|---|---|---|
| Profile with gender | Profile includes gender="female" | LLM context has no gender field |
| Profile with age | Profile includes age=30 | LLM context has no age field |
| Safe fields pass | Profile includes skills=["Python"] | LLM context includes skills |

---

## BR-19: Encryption at Rest

**Source:** `src/privacy.py:39-60`, `config/settings.py:172`
```python
ENCRYPT_USER_DATA: bool = get_secret("ENCRYPT_USER_DATA", "true").lower() == "true"
```

**Logic:** AES-256-GCM encryption for PII at rest. Key derived via PBKDF2-HMAC-SHA256 with 390,000 iterations (OWASP 2023 recommendation). 12-byte random nonce per encryption. Enabled by default.

| Test Case | Input | Expected Output |
|---|---|---|
| Encrypt + decrypt | encrypt("hello@test.com", key) then decrypt | Returns "hello@test.com" |
| Different nonce | encrypt same text twice | Different ciphertext each time |
| Wrong key | Decrypt with different key | Decryption fails (AESGCM raises) |

---

## BR-20: Swagger/ReDoc Visibility

**Source:** `api.py:81-82`
```python
_docs_url: str | None = "/docs" if not AUTH_ENABLED else None
_redoc_url: str | None = "/redoc" if not AUTH_ENABLED else None
```

**Logic:** API documentation endpoints are only exposed when AUTH_ENABLED is false (development mode).

| Test Case | Input | Expected Output |
|---|---|---|
| AUTH=false | GET /docs | Swagger UI rendered |
| AUTH=true | GET /docs | 404 Not Found |

---

## BR-21: Job Import Deduplication

**Source:** `routers/jobs.py:370-376`

**Logic:** When importing a job, if the source_url already exists in the database, the existing job is returned with `is_duplicate=true` instead of creating a duplicate.

| Test Case | Input | Expected Output |
|---|---|---|
| New URL | source_url="https://example.com/job/123" | New job created, is_duplicate=false |
| Duplicate URL | Same source_url submitted again | Existing job returned, is_duplicate=true |
| Empty URL | source_url="" | New job created (empty string not deduplicated) |

---

## BR-22: Job Description Truncation

**Source:** Various locations

**Logic:** Job descriptions are truncated at different lengths depending on context:
- Job cache/search results: 3000 chars (`routers/jobs.py:98, 200`)
- DB storage: 5000 chars (`routers/jobs.py:253, 263`)
- Saved jobs list: 500 chars (`routers/jobs.py:349`)
- LLM prompts: 1500 chars (`routers/jobs.py:460, 484`)

| Test Case | Input | Expected Output |
|---|---|---|
| Short description | 500 char description | Full text everywhere |
| Long description | 6000 char description | 5000 in DB, 3000 in API, 1500 to LLM, 500 in saved list |

---

## BR-23: ApplicationStatus Enum Values

**Source:** `src/models.py:28-35`
```python
class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    OFFER_RECEIVED = "offer_received"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
```

**Logic:** Only these 7 status values are valid for application status updates and Kanban board columns.

---

## BR-24: Adzuna Country Validation

**Source:** `config/settings.py:182-189`
```python
_ADZUNA_VALID_COUNTRIES = {
    "at", "au", "be", "br", "ca", "ch", "de", "es", "fr", "gb",
    "in", "it", "mx", "nl", "nz", "pl", "ru", "sg", "us", "za",
}
```

**Logic:** Invalid ADZUNA_COUNTRY values default to "us" with a warning log.

| Test Case | Input | Expected Output |
|---|---|---|
| Valid country | ADZUNA_COUNTRY=gb | Uses "gb" |
| Invalid country | ADZUNA_COUNTRY=xx | Defaults to "us", logs warning |
| Empty string | ADZUNA_COUNTRY="" | Defaults to "us" |

---

## BR-25: Document Export Format Validation

**Source:** `routers/documents.py:33`
```python
format: str = Field(default="pdf", pattern="^(pdf|docx)$")
```

**Logic:** Only "pdf" and "docx" formats are accepted for document export.

| Test Case | Input | Expected Output |
|---|---|---|
| PDF | format="pdf" | PDF binary response |
| DOCX | format="docx" | DOCX binary response |
| Invalid | format="txt" | 422 validation error |

---

## BR-26: Career Dream Timeline Range

**Source:** `routers/career.py:22`
```python
timeline_months: int = Field(default=12, ge=1, le=120)
```

**Logic:** Career dream timeline must be between 1 and 120 months (10 years).

| Test Case | Input | Expected Output |
|---|---|---|
| Default | No timeline specified | 12 months |
| Min | timeline_months=1 | Accepted |
| Max | timeline_months=120 | Accepted |
| Over max | timeline_months=121 | 422 validation error |

---

## BR-27: Security Headers

**Source:** `api.py:139-161`

**Logic:** Every HTTP response includes these security headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` (restricts script/style/img/font sources)
- `Strict-Transport-Security` (only when request is HTTPS)

---

## BR-28: CORS Allowed Origins

**Source:** `api.py:117-128`

**Logic:** When ALLOWED_ORIGINS env var is set, only those origins are accepted. When unset, defaults to localhost:8000, 127.0.0.1:8000, 10.0.2.2:8000 (Android emulator), localhost:8081 (Expo Metro), and localhost:19006 (Expo web).

---

## BR-29: Offer Deadline Handling

**Source:** `routers/offers.py:89-95`

**Logic:** Offer deadline is parsed as ISO date format. If parsing fails (ValueError), the deadline is silently set to null rather than rejecting the request.

| Test Case | Input | Expected Output |
|---|---|---|
| Valid date | deadline="2026-06-15" | Deadline stored as 2026-06-15 |
| Invalid date | deadline="next-friday" | Deadline stored as null |
| No deadline | deadline omitted | Deadline is null |

---

## BR-30: Saved Job Duplicate Prevention

**Source:** `routers/jobs.py:276-280`

**Logic:** A user cannot save the same job twice. If already saved, the endpoint returns success with message "Job already saved." instead of creating a duplicate.

| Test Case | Input | Expected Output |
|---|---|---|
| First save | Save job_id=X for user_id=Y | Job saved, saved=true |
| Duplicate save | Save job_id=X for user_id=Y again | "Job already saved.", saved=true |
| Different user | Save job_id=X for user_id=Z | Job saved (different user) |
