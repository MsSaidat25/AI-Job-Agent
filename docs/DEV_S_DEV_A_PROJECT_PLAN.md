# Dev S + Dev A Project Plan (Non-Interference + Safe Integration)

---

# PART 1: Process & Governance

---

## 1) Goal
Enable Dev. S and Dev. A to work in parallel on the same repository with:
- clear ownership boundaries,
- minimal merge conflicts,
- predictable integration points,
- mandatory quality gates before merging.

## 2) Branching and Ownership Model

### Branch strategy
- Protected branch: main
- Dev. S branch prefix: feature/dev-s/
- Dev. A branch prefix: feature/dev-a/
- Integration branch (optional): integration/staging

### File ownership split
- Dev. A primary ownership:
  - src/agent.py
  - src/models.py
  - src/privacy.py
  - src/analytics.py
  - src/job_search.py
  - src/career_dreamer.py (new)
  - src/resume_parser.py (new)
  - src/employer.py (new)
  - config/settings.py
  - alembic/ (new)
  - tests/test_models.py
  - tests/test_privacy.py
  - tests/test_analytics.py
  - tests/test_job_search.py (new)
  - tests/test_career_dreamer.py (new)
  - tests/test_resume_parser.py (new)
  - tests/test_employer.py (new)
  - tests/test_bias.py (new)
- Dev. S primary ownership:
  - api.py
  - main.py
  - src/ui.py
  - src/document_generator.py
  - src/salary_data.py (new)
  - frontend/
  - docs/
  - tests/test_api.py (new)
  - tests/test_document_generator.py (new)
  - tests/test_salary_data.py (new)

### Shared files (change-control required)
- requirements.txt
- README.md
- render.yaml
- Any file under src/ touched by both developers in the same sprint

Rule for shared files:
- Open a short design note PR first (or issue comment) before implementation PR.
- Only one developer actively edits a shared file at a time.

## 3) Pre-Work Duplicate Check (Required Before Every New Task)
Before starting any feature or fix, each developer must complete this checklist:

1. Ticket check
- Confirm there is a unique task ID and owner (Dev. S or Dev. A).
- Ensure task status is not already In Progress or Done.

2. Open work check
- Check open PRs for overlapping scope.
- Check active branches for similar names/features.

3. Code existence check
- Search repo for existing implementation (function/class/endpoint/UI label).
- Search tests for the same behavior.

4. API/contract check
- If task touches API shape, confirm endpoint/request/response is not already implemented or pending in another PR.

5. Claim and lock
- Post a short claim note in the ticket: owner, expected files, start time.

If overlap is found:
- Stop work,
- coordinate with the other developer,
- split by sub-scope (or close duplicate task).

## 4) Parallel Delivery Lanes

### Phase 0: Baseline Stabilization (Both, Day 1)
- Dev. A:
  - Validate backend baseline and data model consistency.
  - Confirm privacy pipeline behavior and coverage.
- Dev. S:
  - Validate API layer and user interaction flow (CLI/web-facing behavior).
  - Confirm deployment entrypoints and user-facing docs.

Exit criteria:
- Lint/type/test baseline is green on current main.

### Phase 1: Contract-First Parallel Work (Days 2-5)
- Dev. A lane (backend domain + services):
  - New/updated domain logic in src/ modules.
  - Database/model updates with matching tests.
  - Tool behavior updates in agent orchestration.
- Dev. S lane (API + UX integration):
  - API route improvements and request/response validation.
  - UI flow updates (CLI and/or frontend assets).
  - Documentation and runbook updates.

Integration handshake:
- Agree on API contract before implementation.
- Dev. A provides contract examples and edge cases.
- Dev. S consumes contract and writes integration checks.

### Phase 2: Cross-Integration + Hardening (Days 6-7)
- Dev. A:
  - Performance/safety review of service layer.
  - Error handling and resilience updates.
- Dev. S:
  - End-to-end API journey validation.
  - UX polish and failure-state handling.

Exit criteria:
- All quality gates pass.
- No unresolved overlap issues.
- Deployment checklist completed.

## 5) Mandatory Quality Gates (For Every PR)
Both developers must run all required project checks before opening PR and again before merge:

1. Lint
- ruff check .

2. Type check
- pyright

3. Tests
- pytest

4. Targeted tests for touched area (recommended)
- Example: pytest tests/test_models.py::test_user_profile_deduplication -v

5. Security/privacy sanity for relevant changes
- Confirm protected attributes are not used in ranking logic.
- Confirm PII scrubbing/encryption behavior remains intact where impacted.

6. API/model guardrails
- Endpoints return Pydantic models (not raw dict-only responses in new endpoints).
- Health check endpoint remains available.

PR is blocked if any gate fails.

## 6) Merge Policy to Avoid Interference

1. PR size
- Keep PRs focused (< ~400 lines changed preferred).

2. Rebase rule
- Rebase onto latest main immediately before final checks.

3. Review rule
- Dev. A reviews Dev. S PRs touching domain/business logic.
- Dev. S reviews Dev. A PRs touching API/UI behavior.

4. Conflict rule
- If conflict occurs in shared files, resolve together in a short pairing session.

5. Merge window
- Merge at agreed windows (for example twice daily) to reduce surprise breakage.

## 7) Definition of Done (Per Task)
A task is Done only when:
- Duplicate check completed and logged.
- Implementation complete with scoped file ownership respected.
- Tests added/updated for changed behavior.
- ruff check ., pyright, and pytest all pass.
- PR reviewed and approved.
- Release notes/changelog note added (if user-visible).

## 8) Task Split Template
Use this template for each new feature:

- Feature name:
- Owner: Dev. S or Dev. A
- Scope (in/out):
- Layer: Backend / Frontend / Both
- Files expected to change:
- Duplicate-check result:
- API contract impact: Yes/No
- Tests required:
  - ruff check .
  - pyright
  - pytest
  - targeted test command(s)
- Risks:
- Rollback plan:

## 9) Daily Operating Rhythm
- 10-minute start-of-day sync:
  - What is being started,
  - what files will be touched,
  - any shared-file lock requests.
- 10-minute end-of-day sync:
  - What merged,
  - what is in PR,
  - blockers for next day.

This rhythm is required to keep both developers independent while still integrating safely.

---

# PART 2: Sprint Backlog

---

Every task below specifies the owner, which layers are affected (Backend/Frontend), and the required tests. Tasks are ordered by dependency: earlier tasks unblock later ones. The architecture targets Supabase (PostgreSQL, Frankfurt region) instead of SQLite, integrates real job data APIs, and includes EU compliance requirements.

## Sprint 0: Infrastructure Migration (Days 1-5)

### S0-01: Supabase migration
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Migrate from SQLite to Supabase PostgreSQL. Change `get_engine()` in `src/models.py` to use `DATABASE_URL` env var pointing at Supabase Postgres (Frankfurt region). Add connection pooling via Supavisor (port 6543, NullPool in SQLAlchemy). Update `config/settings.py` to replace `DB_PATH` with `DATABASE_URL`. Update all test fixtures that monkeypatch `DB_PATH`. Verify all ORM models work with Postgres (JSON columns, Boolean, DateTime). Add Alembic for schema migrations. Configure Row-Level Security policies for tenant isolation.
- **Files:** `src/models.py`, `config/settings.py`, `tests/test_models.py`, `tests/test_privacy.py`, `tests/test_analytics.py`, `alembic/` (new), `alembic.ini` (new), `requirements.txt`
- **New dependencies:** `alembic`, `psycopg2-binary`
- **Tests:** `pytest` (all existing tests must pass against Postgres), `ruff check .`, `pyright`

### S0-02: Supabase Auth integration
- **Owner:** Dev. A
- **Layer:** Backend (API)
- **Depends on:** S0-01
- **Description:** Replace in-memory session dict in `api.py` with Supabase Auth. Add JWT validation middleware. Each request extracts user_id from Supabase JWT. Add signup/login endpoints (or use Supabase client-side auth). Add `X-Auth-Token` header validation. Map Supabase user_id to UserProfileORM. Implement token refresh flow and session expiry.
- **Files:** `api.py`, `requirements.txt`
- **New dependencies:** `supabase` (Python client), `PyJWT`
- **Tests:** `pytest tests/test_api.py -v` (test auth flow, test 401 for missing token, test user isolation)

### S0-03: Environment and config update
- **Owner:** Dev. S
- **Layer:** Backend
- **Description:** Update `config/settings.py` with new env vars: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL`, `STRIPE_SECRET_KEY` (placeholder), `JSEARCH_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`. Add `.env.example` with all required vars (no actual secrets). Update `render.yaml` with new env var references.
- **Files:** `config/settings.py`, `.env.example` (new), `render.yaml`
- **Tests:** `ruff check .`, `pyright`

## Sprint 1: Real Job Data + Core Features (Days 6-12)

### S1-01: JSearch API integration
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Replace mock job data in `src/job_search.py` with real JSearch API calls. Add `_search_jsearch(query, location, remote, page)` method to `JobSearchEngine`. Parse JSearch response into `JobListing` Pydantic models. Map fields: employer_name->company, job_title->title, job_description->description, job_min_salary/job_max_salary->salary range, job_apply_link->source_url, job_posted_at->posted_date. Add rate limiting (5 req/sec on Pro plan). Cache results in Supabase for 24 hours to reduce API calls.
- **Files:** `src/job_search.py`, `config/settings.py`, `tests/test_job_search.py` (new)
- **Tests:** `pytest tests/test_job_search.py -v` (mock JSearch responses, test field mapping, test cache behavior, test error handling for API failures)

### S1-02: Adzuna API integration
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Add `_search_adzuna(query, location, country)` method to `JobSearchEngine` as fallback/supplement to JSearch. Parse Adzuna response into `JobListing` models. Adzuna provides salary data and location data that JSearch sometimes lacks. Add country parameter support for international searches. Implement automatic fallback: if JSearch fails or returns no results, try Adzuna.
- **Files:** `src/job_search.py`, `config/settings.py`, `tests/test_job_search.py`
- **Tests:** `pytest tests/test_job_search.py -v` (mock Adzuna responses, test field mapping, test multi-country, test fallback behavior)

### S1-03: ATS keyword scoring
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Add `score_ats_match(resume_text, job_description)` method to `src/document_generator.py`. Uses Claude to: extract keywords from JD, compare against resume, return match percentage + missing keywords + suggested insertions. Add `ats_score` and `missing_keywords` fields to `GeneratedDocument` Pydantic model. After resume generation, automatically run ATS scoring and include results.
- **Files:** `src/document_generator.py`, `src/models.py`, `tests/test_document_generator.py` (new)
- **Tests:** `pytest tests/test_document_generator.py -v` (mock Claude response, test score range 0-100, test keyword extraction)

### S1-04: PDF/DOCX export
- **Owner:** Dev. S
- **Layer:** Backend
- **Description:** Add `export_document(content_md, format)` to `src/document_generator.py`. Supports "pdf" (via `fpdf2`) and "docx" (via `python-docx`). Returns file bytes. Clean formatting with proper headings, bullet points, spacing.
- **Files:** `src/document_generator.py`, `requirements.txt`
- **New dependencies:** `fpdf2`, `python-docx`
- **Tests:** `pytest tests/test_document_generator.py -v` (test PDF returns non-empty bytes, test DOCX is valid, test error on unsupported format)

### S1-05: Job search and export API routes
- **Owner:** Dev. S
- **Layer:** Backend (API) + Frontend
- **Depends on:** S1-01, S1-04
- **Description:** Update `POST /chat` to use real job data. Add `POST /api/documents/export` endpoint accepting `{ content: str, format: "pdf"|"docx" }`, returns file download. Add download buttons in frontend next to generated documents.
- **Files:** `api.py`, `frontend/index.html`, `tests/test_api.py`
- **Tests:** `pytest tests/test_api.py -v` (test export returns file with correct content-type)

### S1-06: Dashboard backend endpoints
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Create `get_kpis(user_id)`, `get_pipeline(user_id)`, `get_charts(user_id)`, `get_insights(user_id)` in `src/analytics.py`. Returns structured dicts for KPI cards, pipeline counts, industry/platform breakdowns, AI insight bullets.
- **Files:** `src/analytics.py`, `tests/test_analytics.py`
- **API contract:**
  - `get_kpis` -> `{ total, submitted, response_rate, interview_rate, offer_rate, avg_days_to_reply }`
  - `get_pipeline` -> `{ by_status: { "draft": N, "submitted": N, ... } }`
  - `get_charts` -> `{ by_industry: [{name, count}], by_platform: [{name, count}], weekly_rates: [{week, rate}] }`
  - `get_insights` -> `{ bullets: [str], feedback_themes: [str] }`
- **Tests:** Each method tested with 0, 1, and 5+ applications

### S1-07: Dashboard API routes + frontend
- **Owner:** Dev. S
- **Layer:** Both
- **Depends on:** S1-06
- **Description:** Add `GET /api/dashboard/kpis`, `/pipeline`, `/charts`, `/insights` routes. Build dashboard section in frontend with KPI cards, pipeline funnel, charts (Chart.js CDN), AI insights panel.
- **Files:** `api.py`, `frontend/index.html`, `tests/test_api.py`

## Sprint 2: Career Intelligence (Days 13-19)

### S2-01: Career Dreamer backend
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Create `src/career_dreamer.py` with `CareerDreamer` class. Methods: `build_gap_report(profile, dream)` returns skills overlap, missing skills with learning time, salary comparison. `score_feasibility(gap_report)` returns 0-100. `build_timeline(gap_report, months)` returns week-by-week plan. All use Claude for synthesis. Handle edge cases: empty skill lists, unsupported locations, invalid timelines.
- **Files:** `src/career_dreamer.py` (new), `tests/test_career_dreamer.py` (new)
- **Tests:** Mock Anthropic client; test gap report structure, feasibility range, timeline output, edge cases

### S2-02: Career Dreamer data models
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Add Pydantic models: `DreamScenario`, `GapReport`, `DreamTimeline`. Add `CareerDreamORM` table. Add `preferred_currency` column to `UserProfileORM`.
- **Files:** `src/models.py`, `tests/test_models.py`

### S2-03: Career Dreamer agent tool + API + frontend
- **Owner:** Dev. A (tool), Dev. S (API routes + frontend)
- **Depends on:** S2-01, S2-02
- **Description:** Dev. A adds `career_dreamer` tool to TOOLS list in `src/agent.py`, registers in `_dispatch_tool`. Dev. S adds `POST /api/career-dreamer/explore`, `GET /api/career-dreamer/saved`, `POST /api/career-dreamer/save` routes. Dev. S builds Career Dreamer UI section in frontend.
- **Files:** `src/agent.py`, `api.py`, `frontend/index.html`

### S2-04: Salary benchmarks + BLS API
- **Owner:** Dev. S
- **Layer:** Backend
- **Description:** Add `SalaryBenchmarkORM` table. Create `src/salary_data.py` with `SalaryDataService`. Fetches from BLS OEWS API (free, 500 queries/day). Stores in salary_benchmarks table. Method: `get_benchmark(occupation, location)`.
- **Files:** `src/models.py`, `src/salary_data.py` (new), `tests/test_salary_data.py` (new), `config/settings.py`

### S2-05: Skill gap analysis
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Add `analyze_skill_gaps(profile, region)` to `src/job_search.py`. Queries live postings for user's target roles. Returns: must-have gaps (skills in 70%+ of postings that user lacks), nice-to-have gaps (30-70%), hidden strengths (user has, <20% of candidates do), upskill ROI per skill (estimated salary bump). Uses Claude to synthesize across multiple postings.
- **Files:** `src/job_search.py`, `tests/test_job_search.py`

### S2-06: Resume upload + AI parse
- **Owner:** Dev. A (parser), Dev. S (API route + frontend)
- **Description:** Dev. A creates `src/resume_parser.py` with `ResumeParser` class. `parse(file_bytes, filename)` handles PDF/DOCX/image via pdfplumber, python-docx, and Claude Vision for scans. Returns structured `UserProfile` with confidence scores per field. Dev. S adds `POST /api/profile/resume-upload` endpoint and wires frontend upload area.
- **Files:** `src/resume_parser.py` (new), `api.py`, `frontend/index.html`, `requirements.txt`
- **New dependencies:** `python-docx`, `pdfplumber`

## Sprint 3: Compliance + Employer Portal (Days 20-28)

### S3-01: GDPR compliance layer
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Add GDPR endpoints and controls:
  - `POST /api/privacy/consent` - record user consent with timestamp and scope
  - `GET /api/privacy/export` - export all user data as JSON (Art. 20 portability)
  - `DELETE /api/privacy/erase` - delete all user data and confirm (Art. 17 erasure), cascade through all tables
  - `GET /api/privacy/dashboard` - show what data exists, what was sent to LLM, encryption status
  - Add `ConsentRecordORM` table (user_id, consent_type, granted_at, withdrawn_at)
  - Add `AuditLogORM` table (user_id, action, timestamp, details) for Art. 12 logging
  - Log all AI decisions (job matches, resume generations) to audit log
  - Minimum 6-month log retention with automated cleanup
- **Files:** `src/models.py`, `src/privacy.py`, `api.py`, `tests/test_privacy.py`
- **Tests:** Test export returns all user data, test erase removes all data across all tables, test audit log records AI decisions, test consent recording and withdrawal

### S3-02: EU AI Act compliance controls
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Implement high-risk AI system requirements (Annex III, Section 4):
  - Human oversight: all AI recommendations are advisory, user approves/rejects (Art. 14)
  - Transparency: every job match includes `match_rationale` explaining why (Art. 13)
  - Bias testing: add `test_bias_detection()` to test suite that checks job matching across demographic groups (Art. 10)
  - Technical documentation template for conformity self-assessment (Art. 11)
  - Add `AI_DECISION_EXPLANATION` field to all tool responses in agent.py (Art. 12)
  - Ensure AI decisions can be overridden and interrupted at any point (Art. 14)
- **Files:** `src/agent.py`, `src/job_search.py`, `tests/test_bias.py` (new), `docs/AI_ACT_CONFORMITY.md` (new)

### S3-03: Employer portal - coming soon page + waitlist
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Description:** Add "For Employers" section to the web app. Shows: value proposition (AI-matched candidates, not resume spam), pricing tiers (Free: 3 posts/mo, Pro: $99/mo, Enterprise: $499/mo), email collection form for waitlist. Add `EmployerWaitlistORM` table. Add `POST /api/employer/waitlist` endpoint. Style consistently with main app.
- **Files:** `frontend/index.html`, `src/models.py` (add EmployerWaitlistORM), `api.py`

### S3-04: Employer job posting backend
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Add `EmployerProfileORM` and `EmployerJobListingORM` tables. Create `src/employer.py` with `EmployerService` class. Methods: `create_listing(employer_id, job_data)`, `get_listings(employer_id)`, `match_candidates(job_id)` (returns anonymized profiles with match scores using privacy pipeline). Employer listings appear in regular job search results with "Direct" badge via `source_platform` field.
- **Files:** `src/employer.py` (new), `src/models.py`, `tests/test_employer.py` (new)

### S3-05: Fix datetime.utcnow() deprecation
- **Owner:** Dev. S
- **Layer:** Backend
- **Description:** Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` across all files.
- **Files:** `src/models.py`, `src/agent.py`, `src/document_generator.py`, `tests/test_analytics.py`
- **Tests:** `pytest -W error::DeprecationWarning` (zero warnings)

### S3-06: Salary context in search results + frontend polish
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S2-04
- **Description:** Show salary context under each job card: "Market range: $X-$Y. This job pays [above/at/below] market." Add color badges (green/yellow/red). Wire interview prep section (stretch goal).
- **Files:** `frontend/index.html`, `api.py`

---

# PART 3: Tracking & Coordination

---

## 10) Task Summary Table

| Task ID | Name | Owner | Layer | Depends On | Test File(s) |
|---------|------|-------|-------|------------|--------------|
| S0-01 | Supabase migration | Dev. A | Backend | -- | `tests/test_models.py`, `tests/test_privacy.py`, `tests/test_analytics.py` |
| S0-02 | Supabase Auth integration | Dev. A | Backend (API) | S0-01 | `tests/test_api.py` |
| S0-03 | Environment and config update | Dev. S | Backend | -- | `ruff check .`, `pyright` |
| S1-01 | JSearch API integration | Dev. A | Backend | -- | `tests/test_job_search.py` |
| S1-02 | Adzuna API integration | Dev. A | Backend | -- | `tests/test_job_search.py` |
| S1-03 | ATS keyword scoring | Dev. A | Backend | -- | `tests/test_document_generator.py` |
| S1-04 | PDF/DOCX export | Dev. S | Backend | -- | `tests/test_document_generator.py` |
| S1-05 | Job search and export API routes | Dev. S | Backend (API) + Frontend | S1-01, S1-04 | `tests/test_api.py` |
| S1-06 | Dashboard backend endpoints | Dev. A | Backend | -- | `tests/test_analytics.py` |
| S1-07 | Dashboard API routes + frontend | Dev. S | Both | S1-06 | `tests/test_api.py` |
| S2-01 | Career Dreamer backend | Dev. A | Backend | -- | `tests/test_career_dreamer.py` |
| S2-02 | Career Dreamer data models | Dev. A | Backend | -- | `tests/test_models.py` |
| S2-03 | Career Dreamer tool + API + frontend | Dev. A (tool), Dev. S (API/UI) | Both | S2-01, S2-02 | `tests/test_api.py` |
| S2-04 | Salary benchmarks + BLS API | Dev. S | Backend | -- | `tests/test_salary_data.py` |
| S2-05 | Skill gap analysis | Dev. A | Backend | -- | `tests/test_job_search.py` |
| S2-06 | Resume upload + AI parse | Dev. A (parser), Dev. S (API/UI) | Both | -- | `tests/test_resume_parser.py`, `tests/test_api.py` |
| S3-01 | GDPR compliance layer | Dev. A | Backend | -- | `tests/test_privacy.py` |
| S3-02 | EU AI Act compliance controls | Dev. A | Backend | -- | `tests/test_bias.py` |
| S3-03 | Employer portal coming soon | Dev. S | Frontend + API | -- | Manual |
| S3-04 | Employer job posting backend | Dev. A | Backend | -- | `tests/test_employer.py` |
| S3-05 | Fix datetime.utcnow() deprecation | Dev. S | Backend | -- | `pytest -W error::DeprecationWarning` |
| S3-06 | Salary context + frontend polish | Dev. S | Frontend + API | S2-04 | Manual |

### Task count by owner

| Owner | Total tasks | Backend core | API/Frontend | Shared |
|-------|-------------|-------------|--------------|--------|
| Dev. A | 14 | 12 | 0 | 2 |
| Dev. S | 10 | 2 | 6 | 2 |

## 11) Parallel Lanes (Updated)

**Sprint 0 (Days 1-5) - Infrastructure:**
- Dev. A: S0-01 (Supabase migration), then S0-02 (Auth)
- Dev. S: S0-03 (config, can start Day 1)
- Integration point: Database connection string (Day 1-2)

**Sprint 1 (Days 6-12) - Core Features:**
- Dev. A: S1-01, S1-02, S1-03, S1-06 (all independent backend services)
- Dev. S: S1-04 (export), then S1-05 (API routes after S1-01 ready), then S1-07 (dashboard UI after S1-06 ready)
- Integration points: JSearch field mapping contract (Day 6), dashboard API contract (Day 7)

**Sprint 2 (Days 13-19) - Intelligence:**
- Dev. A: S2-01, S2-02 (Career Dreamer, parallel), then S2-03 tool (after both), S2-05 (skill gaps, independent)
- Dev. S: S2-04 (salary benchmarks, independent), S2-03 API/frontend (after Dev. A ships tool), S2-06 API/frontend (after Dev. A ships parser)
- Integration points: Career Dreamer API contract (Day 13), resume parser output format (Day 14)

**Sprint 3 (Days 20-28) - Compliance + Employer:**
- Dev. A: S3-01, S3-02 (compliance, parallel), S3-04 (employer backend)
- Dev. S: S3-03 (employer frontend), S3-05 (datetime fix), S3-06 (salary UI, after S2-04)
- Integration points: Employer data model contract (Day 20), GDPR endpoint shapes (Day 21)
