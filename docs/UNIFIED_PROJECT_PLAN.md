# JobPath AI -- Unified Project Plan

**Version:** 1.0
**Date:** 2026-04-09
**Goal:** Transform JobPath AI into the best AI-powered job application tool on the market

---

## Strategic Position

**Current strengths (AHEAD):** Privacy/Security, Career Intelligence, API & Extensibility
**At parity (ON PAR):** Resume Generation, Job Search & Matching
**Critical gaps (BEHIND):** Application Automation, Application Tracking UX, Multi-user/Enterprise, Integrations, UI/UX

**Key competitors:** Simplify (autofill), Teal (all-in-one), Huntr (tracking), LazyApply (auto-submit), Sonara (AI agent), Careerflow (career toolkit), Rezi/Kickresume (resume builders)

**Moat:** Local-first privacy architecture + agentic conversational interface + full REST API. No competitor has all three.

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
  - src/admin.py (new)
  - src/interview_coach.py (new)
  - src/auto_apply.py (new)
  - src/linkedin_service.py (new)
  - src/job_alerts.py (new)
  - src/calendar_service.py (new)
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
  - src/template_engine.py (new)
  - frontend/
  - chrome-extension/ (new)
  - templates/resumes/ (new)
  - routers/ (new)
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

## Timeline Reconciliation

The original sprint plan (S0-S3) covers Days 1-28 (4 weeks). The product roadmap extends through Week 26. The unified timeline below maps sprints to calendar weeks:

| Sprint | Days | Calendar Weeks | Focus |
|--------|------|----------------|-------|
| S0 | Days 1-5 | Week 1 | Infrastructure Migration |
| S1 | Days 6-12 | Weeks 2-3 | Real Job Data + Core Features |
| S2 | Days 13-19 | Weeks 3-4 | Career Intelligence |
| S3 | Days 20-28 | Weeks 4-5 | Compliance + Employer Foundation |
| S4 | Days 29-42 | Weeks 5-7 | Frontend Migration + Visual Templates |
| S5 | Days 43-56 | Weeks 7-9 | Chrome Extension v1 + Kanban UX |
| S6 | Days 57-70 | Weeks 9-11 | Autofill + LinkedIn + Mock Interview |
| S7 | Days 71-84 | Weeks 11-13 | Saved Searches + Contacts CRM |
| S8 | Days 85-105 | Weeks 13-16 | Admin Portal + Employer Portal (full) |
| S9 | Days 106-126 | Weeks 16-19 | Auto-Apply + Calendar + Multi-Language |
| S10 | Days 127-140 | Weeks 19-21 | Webhooks + Auth + Notifications |
| S11 | Days 141-161 | Weeks 21-24 | Analytics v2 + Salary Intelligence |
| S12 | Days 162-182 | Weeks 24-26 | Mobile App |

---

## Sprint 0: Infrastructure Migration (Days 1-5 / Week 1)

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

---

## Sprint 1: Real Job Data + Core Features (Days 6-12 / Weeks 2-3)

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

---

## Sprint 2: Career Intelligence (Days 13-19 / Weeks 3-4)

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

### S2-03a: Career Dreamer agent tool (backend wiring)
- **Owner:** Dev. A
- **Layer:** Backend
- **Depends on:** S2-01, S2-02
- **Description:** Add `career_dreamer` tool to TOOLS list in `src/agent.py`, implement `_tool_career_dreamer` method, register in `_dispatch_tool`.
- **Files:** `src/agent.py`
- **Tests:** `pytest tests/test_career_dreamer.py -v`

### S2-03b: Career Dreamer API + frontend
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S2-03a
- **Description:** Add `POST /api/career-dreamer/explore`, `GET /api/career-dreamer/saved`, `POST /api/career-dreamer/save` routes. Build Career Dreamer UI section in frontend.
- **Files:** `api.py`, `frontend/index.html`, `tests/test_api.py`

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

### S2-06a: Resume upload + AI parse (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Description:** Create `src/resume_parser.py` with `ResumeParser` class. `parse(file_bytes, filename)` handles PDF/DOCX/image via pdfplumber, python-docx, and Claude Vision for scans. Returns structured `UserProfile` with confidence scores per field.
- **Files:** `src/resume_parser.py` (new), `tests/test_resume_parser.py` (new), `requirements.txt`
- **New dependencies:** `python-docx`, `pdfplumber`

### S2-06b: Resume upload API + frontend
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S2-06a
- **Description:** Add `POST /api/profile/resume-upload` endpoint and wire frontend upload area.
- **Files:** `api.py`, `frontend/index.html`, `tests/test_api.py`

---

## Sprint 3: Compliance + Employer Foundation (Days 20-28 / Weeks 4-5)

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

### S3-03: Employer portal -- coming soon page + waitlist
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

## Sprint 4: Frontend Migration + Visual Templates (Days 29-42 / Weeks 5-7)

### S4-01: Frontend migration to React/Next.js
- **Owner:** Dev. S
- **Layer:** Frontend
- **Priority:** P0 | **Complexity:** HIGH | **Duration:** 2 weeks
- **Description:** The monolithic `frontend/index.html` (~110KB, vanilla JS) is the #1 development bottleneck. Every UI feature in later sprints depends on a component-based architecture. Migrate to Next.js 14 with App Router.
- **Deliverables:**
  - Next.js 14 app with App Router in `frontend/` directory
  - Tailwind CSS 4 + shadcn/ui component library
  - Port all existing views: Landing, Onboarding, Chat, Dashboard, Job Search, Documents, Profile
  - Dark/light theme toggle (existing feature, preserved)
  - PWA manifest + service worker for offline access
  - API client layer with session management (replaces raw fetch calls)
  - Mobile-first responsive layout
  - Playwright E2E tests for critical flows
- **Files:** `frontend/` (full restructure)
- **Architecture:**
  ```
  frontend/
    app/
      layout.tsx              # Root layout + providers
      page.tsx                # Landing page
      (auth)/login/page.tsx, register/page.tsx
      (app)/
        layout.tsx            # App shell (sidebar + header)
        dashboard/page.tsx    # Kanban + metrics
        jobs/page.tsx         # Job search + saved jobs
        documents/page.tsx    # Resume/cover letter builder
        chat/page.tsx         # Agentic chat interface
        career/page.tsx       # Career Dreamer
        applications/page.tsx # Application tracker
        profile/page.tsx      # Profile editor
        settings/page.tsx     # App settings
    components/
      ui/                     # shadcn primitives
      layout/                 # Header, Sidebar, Footer
      dashboard/              # Dashboard-specific components
      jobs/                   # Job cards, filters, search
      documents/              # Resume builder, cover letter
      chat/                   # Chat messages, input
      applications/           # Kanban board, cards
    lib/
      api.ts                  # API client (axios/fetch wrapper)
      store.ts                # Zustand global state
      hooks/                  # Custom React hooks
      utils.ts                # Shared utilities
    public/
      manifest.json           # PWA manifest
  ```
- **New dependencies:** `next@14`, `react@18`, `tailwindcss@4`, `@shadcn/ui`, `zustand`, `@tanstack/react-query`, `framer-motion`, `next-pwa`, `playwright`

### S4-02: Visual resume templates + template engine
- **Owner:** Dev. S
- **Layer:** Frontend + Backend
- **Priority:** P0 | **Complexity:** MEDIUM | **Duration:** 1.5 weeks
- **Depends on:** S4-01
- **Description:** Current resumes are Markdown-only. Visual templates drive conversions (see Kickresume, Rezi). PDF/DOCX export infrastructure already exists from S1-04.
- **Deliverables:**
  - 10 ATS-friendly resume templates (HTML/CSS rendered to PDF):
    Classic Professional, Modern Minimal, Tech/Developer, Creative/Design, Executive, Academic/Research, Federal/Government, Career Change, Entry Level/Graduate, International/Multi-language
  - Live WYSIWYG preview in browser (React component)
  - PDF export via `weasyprint` (server-side HTML-to-PDF)
  - DOCX export via `python-docx` (already available)
  - Template selection UI with thumbnails
  - Custom color/font options per template
  - ATS compatibility score per template
  - API endpoints: `GET /api/templates`, `POST /api/documents/export`
- **Backend:**
  ```python
  # New: src/template_engine.py
  class ResumeTemplateEngine:
      def list_templates() -> list[TemplateInfo]
      def render_preview(content: str, template_id: str) -> str  # HTML
      def export_pdf(content: str, template_id: str) -> bytes
      def export_docx(content: str, template_id: str) -> bytes

  # New models in src/models.py
  class TemplateInfo(BaseModel):
      id: str
      name: str
      category: str  # professional, creative, technical, etc.
      thumbnail_url: str
      ats_score: int  # 1-100
  ```
- **Files:** `src/template_engine.py` (new), `src/models.py`, `frontend/`, `templates/resumes/` (new)
- **New dependencies:** `weasyprint`

---

## Sprint 5: Chrome Extension v1 + Kanban UX (Days 43-56 / Weeks 7-9)

### S5-01: Chrome browser extension v1 (job bookmarking)
- **Owner:** Dev. S
- **Layer:** Frontend (extension)
- **Priority:** P0 | **Complexity:** HIGH | **Duration:** 2 weeks
- **Description:** Chrome extension for bookmarking jobs from any job board into JobPath AI. This is the single largest competitive gap versus Simplify, Teal, and Huntr.
- **Deliverables:**
  - Chrome extension (Manifest V3) with popup UI
  - Job detection on major boards: LinkedIn, Indeed, Glassdoor, Dice, AngelList, ZipRecruiter, Greenhouse, Lever, Workday
  - One-click save: extracts title, company, salary, location, URL, description
  - Popup shows saved jobs count + quick status
  - Sync with JobPath AI backend via API (auth via session token)
  - Content script that highlights "already saved" jobs on boards
  - Badge counter for new job matches
- **Architecture:**
  ```
  chrome-extension/
    manifest.json               # Manifest V3
    background/service-worker.ts
    content/
      detectors/                # linkedin.ts, indeed.ts, greenhouse.ts, lever.ts, workday.ts, generic.ts
      inject.ts                 # Highlight saved jobs on page
    popup/
      Popup.tsx, SaveJob.tsx, JobList.tsx, Settings.tsx
    lib/
      api.ts, storage.ts, parser.ts
  ```
- **Backend changes:**
  ```python
  # New endpoints
  POST /api/jobs/save           # Extension saves job
  GET  /api/jobs/saved          # List saved jobs
  DELETE /api/jobs/saved/{id}
  POST /api/jobs/saved/{id}/apply  # Convert to application

  # New model: SavedJobORM
  class SavedJobORM(Base):
      id, user_id, title, company, url (unique), source_platform,
      raw_description, salary_info, location, saved_at, match_score
  ```
- **Files:** `chrome-extension/` (new), `api.py`, `src/models.py`
- **New dependencies:** `plasmo`, `react` (extension popup)

### S5-02a: Kanban application tracker backend
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P0 | **Complexity:** MEDIUM
- **Description:** Extend the application tracking data model to support kanban-style tracking with drag-and-drop, contacts, reminders, and activity logs. Add new fields to `ApplicationRecordORM` and new API-facing methods in `src/analytics.py`.
- **Backend changes:**
  ```python
  # New fields in ApplicationRecordORM
  contacts = Column(JSON)          # [{name, email, role, linkedin}]
  reminders = Column(JSON)         # [{type, date, message}]
  activity_log = Column(JSON)      # [{timestamp, action, details}]
  priority = Column(Integer)       # 1-5 for sorting within columns
  archived = Column(Boolean)
  ```
- **Files:** `src/models.py`, `src/analytics.py`, `tests/test_analytics.py`
- **Tests:** `pytest tests/test_analytics.py -v`

### S5-02b: Kanban application tracker frontend + API routes
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S5-02a, S4-01
- **Priority:** P0 | **Complexity:** MEDIUM | **Duration:** 1.5 weeks
- **Description:** Build drag-and-drop kanban board UI with React components. Columns: Saved, Applied, Screening, Interview, Offer, Rejected, Withdrawn. Wire to backend via API routes.
- **Deliverables:**
  - Kanban board with drag-and-drop cards between columns (auto-updates status via API)
  - Card details: company, role, salary, deadline, notes, contacts, documents
  - Reminder system: follow-up reminders, interview prep reminders
  - Activity timeline per application
  - Bulk actions (archive, delete, export CSV)
  - Filter/sort by date, company, status, match score
  - Contact tracker per application
- **API endpoints:**
  ```
  GET  /api/applications              # All apps with filters
  GET  /api/applications/{id}         # Single app detail
  PATCH /api/applications/{id}/move   # Drag-and-drop status change
  POST /api/applications/{id}/remind  # Create reminder
  GET  /api/applications/export       # CSV export
  ```
- **Frontend components:**
  ```
  components/applications/
    KanbanBoard.tsx, KanbanColumn.tsx, ApplicationCard.tsx,
    ApplicationDetail.tsx, ContactList.tsx, ReminderForm.tsx, ActivityTimeline.tsx
  ```
- **Files:** `frontend/`, `api.py`, `tests/test_api.py`
- **New dependencies:** `@dnd-kit/core`, `@dnd-kit/sortable`

---

## Sprint 6: Autofill + LinkedIn + Mock Interview (Days 57-70 / Weeks 9-11)

### S6-01a: Chrome extension v2 -- autofill engine (backend logic)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** HIGH | **Duration:** 2 weeks
- **Description:** Build the field mapping and form detection logic that the autofill extension consumes. Provide autofill data API endpoints that return structured profile data ready for form filling.
- **Deliverables:**
  - Field mapping configuration for top ATS platforms: Workday, Greenhouse, Lever, iCIMS, Taleo/Oracle, SmartRecruiters, BambooHR, Ashby
  - Smart form field detection logic (fallback for unknown ATS)
  - API endpoint: `GET /api/profile/autofill-data` returns structured form-fillable data
  - Resume/cover letter auto-attachment endpoint (pre-generated PDFs)
- **Files:** `src/models.py`, `api.py`, `tests/test_api.py`

### S6-01b: Chrome extension v2 -- autofill frontend
- **Owner:** Dev. S
- **Layer:** Frontend (extension)
- **Depends on:** S6-01a
- **Description:** Extend Chrome extension with autofill UI and content scripts.
- **Deliverables:**
  - Autofill content scripts for each ATS platform
  - One-click fill with review-before-submit
  - Resume/cover letter auto-attachment
  - Application auto-tracked in kanban after submission
- **Architecture:**
  ```
  content/autofill/
    engine.ts               # Core autofill logic
    field-detector.ts       # ML-based field type detection
    adapters/
      workday.ts, greenhouse.ts, lever.ts, icims.ts, generic.ts
    resume-uploader.ts      # File input automation
  ```
- **Files:** `chrome-extension/`

### S6-02a: LinkedIn profile import (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** MEDIUM
- **Description:** Build LinkedIn profile import and optimization service.
- **Deliverables:**
  - LinkedIn public profile URL parsing
  - Auto-populate UserProfile fields from LinkedIn data
  - LinkedIn headline/summary optimization suggestions via Claude
  - LinkedIn profile completeness score
  - Skills gap: "Your LinkedIn is missing these keywords that appear in your target roles"
  - Import work history, education, certifications, skills
- **Backend:**
  ```python
  # New: src/linkedin_service.py
  class LinkedInService:
      async def import_profile(url: str) -> UserProfile
      async def analyze_profile(url: str) -> LinkedInAnalysis
      async def suggest_optimizations(profile: UserProfile, target_roles: list[str]) -> list[Suggestion]
  ```
- **Files:** `src/linkedin_service.py` (new), `tests/test_linkedin.py` (new)

### S6-02b: LinkedIn import API + frontend
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S6-02a
- **Description:** Add API routes and frontend UI for LinkedIn import.
- **API endpoints:**
  ```
  POST /api/profile/import-linkedin    # Import from LinkedIn URL
  POST /api/profile/optimize-linkedin  # Get optimization suggestions
  ```
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

### S6-03a: AI mock interview (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** MEDIUM | **Duration:** 2 weeks
- **Description:** Build interview coaching backend. Only Careerflow offers this (at $44.99/month). Adding it free/base tier is a strong differentiator.
- **Deliverables:**
  - Interview modes: Behavioral (STAR), Technical, Case Study, Culture Fit
  - Real-time voice interview via WebRTC + Whisper/Deepgram STT
  - Text-based interview (fallback, always available)
  - Per-answer feedback: strength, weakness, improved version
  - Overall interview score with detailed breakdown
  - Company-specific prep: pulls from job description + company research
  - Interview history + progress tracking
  - Common question bank by role/industry
- **Backend:**
  ```python
  # New: src/interview_coach.py
  class InterviewCoach:
      async def start_session(job: JobListing, mode: str) -> InterviewSession
      async def ask_question(session_id: str) -> Question
      async def evaluate_answer(session_id: str, answer: str) -> Feedback
      async def end_session(session_id: str) -> InterviewReport

  # New models
  class InterviewSession(BaseModel):
      id, job_id, mode, questions_asked, current_score

  class InterviewReport(BaseModel):
      overall_score, strengths, improvements, question_scores, recommended_prep
  ```
- **Files:** `src/interview_coach.py` (new), `src/models.py`, `tests/test_interview.py` (new)

### S6-03b: AI mock interview (frontend)
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S6-03a
- **Description:** Build interview UI and wire API routes.
- **Frontend:**
  ```
  app/(app)/interview/
    page.tsx                    # Interview lobby (select mode, job)
    [session_id]/page.tsx       # Live interview UI
    history/page.tsx            # Past interviews + reports
  components/interview/
    InterviewChat.tsx, VoiceRecorder.tsx, FeedbackCard.tsx,
    ScoreRadar.tsx, InterviewReport.tsx
  ```
- **API endpoints:**
  ```
  POST /api/interview/start
  POST /api/interview/{id}/answer
  GET  /api/interview/{id}/report
  GET  /api/interview/history
  ```
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

---

## Sprint 7: Saved Searches + Contact CRM (Days 71-84 / Weeks 11-13)

### S7-01a: Saved searches + job alerts (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** LOW-MEDIUM
- **Description:** Build saved search and alert backend. Sonara's daily curated matches drive high engagement.
- **Deliverables:**
  - Save search criteria (keywords, location, salary, job type, remote)
  - Scheduled job scanning (cron: every 6 hours)
  - Daily/weekly email digest of new matching jobs (via Resend)
  - Match quality threshold (only alert on score > 70)
- **Backend:**
  ```python
  # New model
  class SavedSearchORM(Base):
      id, user_id, name, query, location, job_type, salary_min,
      remote_only, alert_frequency, min_match_score, last_run, created_at

  # New: src/job_alerts.py
  class JobAlertService:
      async def run_saved_searches() -> None  # Cron job
      async def send_digest(user_id: str) -> None
  ```
- **Files:** `src/job_alerts.py` (new), `src/models.py`, `tests/test_job_alerts.py` (new)
- **New dependencies:** `celery`, `redis`

### S7-01b: Saved searches + job alerts (frontend)
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S7-01a
- **Description:** Build saved search management UI and notification center for alerts.
- **Deliverables:**
  - In-app notification center for new matches
  - One-click save-to-kanban from email/notification
  - Saved search management (create, edit, delete, pause)
- **API endpoints:**
  ```
  POST /api/searches/save
  GET  /api/searches/saved
  PUT  /api/searches/saved/{id}
  DELETE /api/searches/saved/{id}
  ```
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

### S7-02a: Networking / contact tracker CRM (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** LOW
- **Description:** Build contact management backend. Only Careerflow and Huntr offer this.
- **Deliverables:**
  - Contact management: name, email, company, role, LinkedIn, notes
  - Link contacts to applications
  - Follow-up reminders with snooze
  - Contact timeline (emails sent, meetings, notes)
  - Relationship strength score (based on interaction frequency)
- **Backend:**
  ```python
  # New models
  class ContactORM(Base):
      id, user_id, name, email, company, role, linkedin_url,
      notes, last_contacted, follow_up_date, created_at

  class ApplicationContactORM(Base):  # Junction table
      application_id, contact_id
  ```
- **Files:** `src/models.py`, `src/analytics.py`, `tests/test_contacts.py` (new)

### S7-02b: Contact CRM (frontend + API)
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S7-02a
- **Description:** Build contact management UI and API routes.
- **Deliverables:**
  - Contact list with search and filters
  - Contact detail view with timeline
  - Import contacts from LinkedIn connections (via extension)
  - Follow-up reminder UI
- **API endpoints:**
  ```
  POST /api/contacts
  GET  /api/contacts
  GET  /api/contacts/{id}
  PUT  /api/contacts/{id}
  DELETE /api/contacts/{id}
  POST /api/contacts/{id}/follow-up
  ```
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

---

## Sprint 8: Admin Portal + Employer Portal (Days 85-105 / Weeks 13-16)

### S8-01a: Admin portal backend
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** HIGH | **Duration:** 3 weeks
- **Description:** Build full admin portal with RBAC for platform management.
- **Deliverables:**
  - Role-Based Access Control (RBAC) model:
    `super_admin` (full platform control), `admin` (user management, moderation), `support` (read-only user data, tickets), `analyst` (analytics only)
  - Admin service: platform metrics, user management, content moderation, feature flags, audit log, email broadcast
- **Backend:**
  ```python
  # New: src/admin.py
  class AdminService:
      def get_platform_metrics() -> PlatformMetrics
      def search_users(query: str) -> list[UserSummary]
      def suspend_user(user_id: str, reason: str) -> None
      def get_audit_log(filters: AuditFilter) -> list[AuditEntry]

  # New models
  class UserRole(str, Enum):
      USER, SUPPORT, ANALYST, ADMIN, SUPER_ADMIN

  class AdminAuditLogORM(Base):
      id, admin_id, action, target_type, target_id, details, timestamp
  ```
- **Files:** `src/admin.py` (new), `src/models.py`, `tests/test_admin.py` (new)

### S8-01b: Admin portal frontend + API routes
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S8-01a
- **Description:** Build admin portal UI and wire API routes. Requires admin role for all endpoints.
- **API endpoints:**
  ```
  GET  /api/admin/metrics
  GET  /api/admin/users
  GET  /api/admin/users/{id}
  POST /api/admin/users/{id}/suspend
  GET  /api/admin/audit-log
  POST /api/admin/feature-flags
  POST /api/admin/broadcast
  ```
- **Frontend:**
  ```
  app/admin/
    layout.tsx, page.tsx, users/page.tsx, users/[id]/page.tsx,
    audit/page.tsx, features/page.tsx, broadcast/page.tsx, analytics/page.tsx
  ```
- **Files:** `api.py` (or `routers/admin.py`), `frontend/`, `tests/test_api.py`

### S8-02a: Employer portal backend (full marketplace)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** HIGH | **Duration:** 3 weeks
- **Depends on:** S3-04
- **Description:** Extend the employer backend into a full two-sided marketplace. Employers can post jobs, manage applicants, and message candidates. Privacy-preserving: employers see anonymized profiles until candidate opts in.
- **Deliverables:**
  - Employer registration + verification flow
  - Company profile (logo, description, culture, benefits)
  - Job posting CRUD
  - Applicant pipeline view (kanban for employers)
  - Anonymized candidate matching (skills, experience, match score; no PII until candidate opts in)
  - Messaging system (employer <-> candidate)
  - Employer analytics: views, applications, response rates
  - Job posting distribution (push to JSearch, Adzuna, Google Jobs)
- **Backend:**
  ```python
  # Extended: src/employer.py
  class EmployerService:
      async def register(data: EmployerRegistration) -> Employer
      async def create_job_posting(employer_id: str, job: JobPostingCreate) -> JobPosting
      async def get_applicants(job_id: str) -> list[AnonymizedCandidate]
      async def reveal_candidate(job_id: str, candidate_id: str) -> CandidateProfile
      async def send_message(employer_id: str, candidate_id: str, msg: str) -> Message

  # New models
  class EmployerORM(Base):
      id, company_name, email, industry, company_size,
      logo_url, description, website, verified, created_at

  class JobPostingORM(Base):
      id, employer_id, title, description, requirements,
      salary_min, salary_max, location, remote_allowed, job_type,
      experience_level, posted_at, expires_at, status, views, applications

  class MessageORM(Base):
      id, sender_id, receiver_id, job_id, content, read, created_at
  ```
- **Files:** `src/employer.py`, `src/models.py`, `tests/test_employer.py`

### S8-02b: Employer portal frontend + API routes
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S8-02a
- **Description:** Build employer portal UI and wire API routes.
- **API endpoints:**
  ```
  POST /api/employer/register
  GET  /api/employer/profile
  PUT  /api/employer/profile
  POST /api/employer/jobs
  GET  /api/employer/jobs
  GET  /api/employer/jobs/{id}/applicants
  POST /api/employer/jobs/{id}/reveal/{candidate_id}
  POST /api/employer/messages
  GET  /api/employer/analytics
  ```
- **Frontend:**
  ```
  app/employer/
    layout.tsx, page.tsx, register/page.tsx, profile/page.tsx,
    jobs/page.tsx, jobs/new/page.tsx, jobs/[id]/page.tsx,
    messages/page.tsx, analytics/page.tsx
  ```
- **Files:** `api.py` (or `routers/employer.py`), `frontend/`, `tests/test_api.py`
- **Pricing tiers:** Free (1 posting), Pro ($99/mo, 10 postings), Enterprise (custom)

---

## Sprint 9: Auto-Apply + Calendar + Multi-Language (Days 106-126 / Weeks 16-19)

### S9-01a: Auto-apply agent backend
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** VERY HIGH | **Duration:** 3 weeks
- **Description:** The most requested feature. LazyApply charges $99-249 for this. Sonara charges $24/month. Build Playwright-based browser automation engine with safety-first design.
- **Deliverables:**
  - Playwright-based browser automation engine
  - Per-board application flows: LinkedIn Easy Apply, Indeed Apply, Greenhouse, Lever, Workday, direct company career pages (generic)
  - Pre-submission review: user approves each application before submit
  - Rate limiting: configurable max applications per day (prevent account flags)
  - Human-like interaction patterns (random delays, mouse movements)
  - Captcha detection + user notification (pause for manual solve)
  - Application log: screenshot of submitted form for records
  - Auto-track in kanban after submission
  - Safety: never apply to same job twice, respect cooldown periods
- **Architecture:**
  ```python
  # New: src/auto_apply.py
  class AutoApplyEngine:
      async def start_session(user_id: str) -> ApplySession
      async def queue_application(session_id: str, job_id: str) -> QueuedApp
      async def preview_application(queued_id: str) -> ApplicationPreview
      async def submit_application(queued_id: str) -> SubmissionResult
      async def get_queue_status(session_id: str) -> QueueStatus

  # New: src/auto_apply/adapters/
  class LinkedInApplyAdapter(BaseAdapter): ...
  class GreenhouseApplyAdapter(BaseAdapter): ...
  class LeverApplyAdapter(BaseAdapter): ...
  class WorkdayApplyAdapter(BaseAdapter): ...
  class GenericApplyAdapter(BaseAdapter): ...  # Heuristic-based
  ```
- **Risk mitigation:**
  - Default to review-before-submit (not spray-and-pray)
  - Configurable daily limits (default: 10/day)
  - Account health monitoring (detect ban signals)
  - Stealth mode to avoid bot detection
- **Files:** `src/auto_apply.py` (new), `src/auto_apply/adapters/` (new), `tests/test_auto_apply.py` (new)
- **New dependencies:** `playwright`, `playwright-stealth`

### S9-01b: Auto-apply frontend + API routes
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S9-01a
- **Description:** Build auto-apply queue management UI and wire API routes.
- **API endpoints:**
  ```
  POST /api/auto-apply/start
  POST /api/auto-apply/queue
  GET  /api/auto-apply/preview/{id}
  POST /api/auto-apply/submit/{id}
  GET  /api/auto-apply/status
  ```
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

### S9-02a: Email + calendar integration (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** MEDIUM | **Duration:** 2 weeks
- **Description:** Build Google Calendar OAuth integration and interview prep automation.
- **Deliverables:**
  - Google Calendar OAuth integration
  - Auto-detect interview invitations in email
  - Create calendar events for interviews with prep reminders
  - Interview prep package auto-generated 24h before: company research summary, role-specific questions, relevant experience highlights, questions to ask
  - Email tracking: detect responses to applications
- **Backend:**
  ```python
  # New: src/calendar_service.py
  class CalendarService:
      async def connect_google(oauth_token: str) -> None
      async def create_interview_event(app_id: str, datetime: str, details: str) -> Event
      async def generate_prep_package(app_id: str) -> PrepPackage
      async def sync_events() -> list[Event]
  ```
- **Files:** `src/calendar_service.py` (new), `tests/test_calendar.py` (new)
- **New dependencies:** `google-api-python-client`

### S9-02b: Calendar integration frontend + API routes
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S9-02a
- **Description:** Build calendar integration UI and wire API routes.
- **API endpoints:**
  ```
  POST /api/integrations/google/connect
  GET  /api/integrations/google/callback
  POST /api/calendar/events
  GET  /api/calendar/upcoming
  GET  /api/calendar/prep/{application_id}
  ```
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

### S9-03: Multi-language resume generation
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P2 | **Complexity:** LOW | **Duration:** 1 week
- **Description:** Kickresume supports 8 languages. Claude handles this natively.
- **Deliverables:**
  - Language selector in resume/cover letter generation
  - Supported languages: English, Spanish, French, German, Portuguese, Chinese, Japanese, Arabic, Hindi, Korean
  - Locale-aware formatting (date formats, address formats)
  - Cultural norms per language/region (e.g., photo on CV in Germany, no photo in US)
  - Translation of existing resume to new language
- **Files:** `src/document_generator.py`, `config/settings.py`, `tests/test_document_generator.py`

### S9-04: Multi-language frontend
- **Owner:** Dev. S
- **Layer:** Frontend
- **Depends on:** S9-03
- **Description:** Add language selector UI for resume and cover letter generation. Wire to backend language parameter.
- **Files:** `frontend/`

---

## Sprint 10: Webhooks + Auth + Notifications (Days 127-140 / Weeks 19-21)

### S10-01a: Webhooks + plugin system (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P2 | **Complexity:** MEDIUM | **Duration:** 1.5 weeks
- **Description:** Build webhook delivery and plugin registration system.
- **Deliverables:**
  - Webhook registration: notify on events (new_match, status_change, interview_scheduled)
  - Retry logic with exponential backoff
  - Plugin registry: third-party integrations can register
  - SDK: `jobpath-sdk` npm/pip package for building integrations
  - Event types: `job.matched`, `application.created`, `application.status_changed`, `interview.scheduled`, `document.generated`
- **Files:** `src/webhooks.py` (new), `src/models.py`, `tests/test_webhooks.py` (new)

### S10-01b: Webhooks management UI
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S10-01a
- **Description:** Build webhook management UI and API routes.
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

### S10-02: User authentication + multi-tenant
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P0 | **Complexity:** MEDIUM | **Duration:** 2 weeks
- **Depends on:** S0-02
- **Description:** Extend the Supabase Auth integration from S0-02 into full multi-tenant user management. Current design is single-session; production requires proper user accounts.
- **Deliverables:**
  - User registration (email + password, Google OAuth, GitHub OAuth)
  - JWT authentication with refresh tokens
  - Isolated user workspaces (all data scoped to user_id)
  - Account settings (change password, delete account, export data)
  - GDPR compliance: data export, right to deletion (extends S3-01)
  - Rate limiting per user (not just per IP)
  - Session management (multiple devices, revoke sessions)
- **Files:** `src/models.py`, `api.py`, `config/settings.py`, `tests/test_auth.py` (new)

### S10-03a: Notification center (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** LOW-MEDIUM | **Duration:** 1 week
- **Description:** Build notification delivery backend.
- **Deliverables:**
  - Notification types: new job matches, application updates, interview reminders, follow-up reminders, system announcements
  - WebSocket for real-time updates
  - Email notification preferences (per type: instant/daily/off)
  - Push notification support (PWA)
- **Files:** `src/notifications.py` (new), `src/models.py`, `tests/test_notifications.py` (new)
- **New dependencies:** `websockets`

### S10-03b: Notification center (frontend)
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S10-03a
- **Description:** Build notification bell UI with unread count, notification feed, and preference settings.
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

---

## Sprint 11: Analytics v2 + Salary Intelligence (Days 141-161 / Weeks 21-24)

### S11-01a: Analytics dashboard v2 (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** MEDIUM | **Duration:** 1.5 weeks
- **Description:** Extend analytics backend with richer data, benchmarks, and goal tracking.
- **Deliverables:**
  - Application funnel data (Saved -> Applied -> Interview -> Offer)
  - Response rate over time
  - Applications by platform/source
  - Salary range distribution of applied jobs
  - Skills demand heatmap
  - Comparison benchmarks: "You're in the top 20% of applicants for response rate"
  - Weekly AI-generated insights email (what worked, what to change)
  - Goal tracking: "Apply to 50 jobs this month" with progress bar
- **Files:** `src/analytics.py`, `tests/test_analytics.py`

### S11-01b: Analytics dashboard v2 (frontend)
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S11-01a
- **Description:** Build interactive analytics charts and goal tracking UI.
- **Frontend components:** Interactive charts (Recharts or Nivo), funnel visualization, benchmarks display, goal progress bars
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`
- **New dependencies:** `recharts` or `@nivo/core`

### S11-02a: Salary intelligence engine (backend)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P1 | **Complexity:** MEDIUM | **Duration:** 1.5 weeks
- **Depends on:** S2-04
- **Description:** Extend the BLS salary data from S2-04 into a full salary intelligence engine.
- **Deliverables:**
  - Real-time salary data aggregation (Glassdoor API, Levels.fyi, BLS data)
  - Location-based salary comparison: "Your skills pay $X in City A vs $Y in City B"
  - Cost-of-living adjustment: "After CoL, Berlin pays effectively more than SF"
  - Salary negotiation coach (AI-powered, role-play negotiation scenarios)
  - Compensation breakdown: base, bonus, equity, benefits comparison
  - Historical salary trends by role/location
- **Files:** `src/salary_data.py`, `tests/test_salary_data.py`

### S11-02b: Salary intelligence (frontend)
- **Owner:** Dev. S
- **Layer:** Frontend + API
- **Depends on:** S11-02a
- **Description:** Build salary comparison and negotiation UI.
- **Files:** `api.py`, `frontend/`, `tests/test_api.py`

---

## Sprint 12: Mobile App (Days 162-182 / Weeks 24-26)

### S12-01a: Mobile app (shared components + API)
- **Owner:** Dev. A
- **Layer:** Backend
- **Priority:** P2 | **Complexity:** HIGH | **Duration:** 4 weeks
- **Description:** Ensure all API endpoints support mobile-friendly responses and add mobile-specific endpoints (push notification registration, camera-based features).
- **Deliverables:**
  - Push notification registration endpoints
  - Camera: business card scanning to add contacts (Claude Vision)
  - Camera: resume scanning (extends S2-06a)
  - Mobile-optimized API responses (pagination, field selection)
- **Files:** `api.py`, `src/resume_parser.py`, `tests/test_api.py`

### S12-01b: Mobile app (React Native)
- **Owner:** Dev. S
- **Layer:** Frontend (mobile)
- **Depends on:** S12-01a
- **Priority:** P2 | **Complexity:** HIGH | **Duration:** 4 weeks
- **Description:** Build React Native app sharing components with Next.js frontend.
- **Deliverables:**
  - React Native app sharing components with Next.js frontend
  - Push notifications for job matches and application updates
  - Quick actions: swipe to save/dismiss jobs, one-tap apply
  - Offline mode: cached job listings and documents
  - Camera: scan business cards to add contacts, scan resumes
  - iOS + Android deployment
- **Files:** `mobile/` (new)

---

# PART 3: Tracking & Coordination

---

## 10) Task Summary Table

| Task ID | Name | Owner | Layer | Depends On | Test File(s) | Status |
|---------|------|-------|-------|------------|--------------|--------|
| S0-01 | Supabase migration | Dev. A | Backend | -- | `tests/test_models.py`, `tests/test_privacy.py`, `tests/test_analytics.py` | TODO |
| S0-02 | Supabase Auth integration | Dev. A | Backend (API) | S0-01 | `tests/test_api.py` | TODO |
| S0-03 | Environment and config update | Dev. S | Backend | -- | `ruff check .`, `pyright` | TODO |
| S1-01 | JSearch API integration | Dev. A | Backend | -- | `tests/test_job_search.py` | TODO |
| S1-02 | Adzuna API integration | Dev. A | Backend | -- | `tests/test_job_search.py` | TODO |
| S1-03 | ATS keyword scoring | Dev. A | Backend | -- | `tests/test_document_generator.py` | **DONE** |
| S1-04 | PDF/DOCX export | Dev. S | Backend | -- | `tests/test_document_generator.py` | TODO |
| S1-05 | Job search and export API routes | Dev. S | Backend (API) + Frontend | S1-01, S1-04 | `tests/test_api.py` | TODO |
| S1-06 | Dashboard backend endpoints | Dev. A | Backend | -- | `tests/test_analytics.py` | TODO |
| S1-07 | Dashboard API routes + frontend | Dev. S | Both | S1-06 | `tests/test_api.py` | TODO |
| S2-01 | Career Dreamer backend | Dev. A | Backend | -- | `tests/test_career_dreamer.py` | **DONE** |
| S2-02 | Career Dreamer data models | Dev. A | Backend | -- | `tests/test_models.py` | **DONE** |
| S2-03a | Career Dreamer agent tool (backend wiring) | Dev. A | Backend | S2-01, S2-02 | `tests/test_career_dreamer.py` | **DONE** |
| S2-03b | Career Dreamer API + frontend | Dev. S | Frontend + API | S2-03a | `tests/test_api.py` | TODO |
| S2-04 | Salary benchmarks + BLS API | Dev. S | Backend | -- | `tests/test_salary_data.py` | TODO |
| S2-05 | Skill gap analysis | Dev. A | Backend | -- | `tests/test_job_search.py` | **DONE** |
| S2-06a | Resume parser (AI parse) | Dev. A | Backend | -- | `tests/test_resume_parser.py` | **DONE** |
| S2-06b | Resume upload API + frontend | Dev. S | Frontend + API | S2-06a | `tests/test_api.py` | TODO |
| S3-01 | GDPR compliance layer | Dev. A | Backend | -- | `tests/test_privacy.py` | TODO |
| S3-02 | EU AI Act compliance controls | Dev. A | Backend | -- | `tests/test_bias.py` | TODO |
| S3-03 | Employer portal coming soon | Dev. S | Frontend + API | -- | Manual | TODO |
| S3-04 | Employer job posting backend | Dev. A | Backend | -- | `tests/test_employer.py` | TODO |
| S3-05 | Fix datetime.utcnow() deprecation | Dev. S | Backend | -- | `pytest -W error::DeprecationWarning` | TODO |
| S3-06 | Salary context + frontend polish | Dev. S | Frontend + API | S2-04 | Manual | TODO |
| S4-01 | Frontend migration to React/Next.js | Dev. S | Frontend | -- | Playwright E2E | TODO |
| S4-02 | Visual resume templates + template engine | Dev. S | Frontend + Backend | S4-01 | `tests/test_template_engine.py` | TODO |
| S5-01 | Chrome extension v1 (job bookmarking) | Dev. S | Frontend (ext) | -- | Extension tests | TODO |
| S5-02a | Kanban tracker backend | Dev. A | Backend | -- | `tests/test_analytics.py` | TODO |
| S5-02b | Kanban tracker frontend + API | Dev. S | Frontend + API | S5-02a, S4-01 | `tests/test_api.py` | TODO |
| S6-01a | Chrome ext v2 autofill backend | Dev. A | Backend | -- | `tests/test_api.py` | TODO |
| S6-01b | Chrome ext v2 autofill frontend | Dev. S | Frontend (ext) | S6-01a | Extension tests | TODO |
| S6-02a | LinkedIn import backend | Dev. A | Backend | -- | `tests/test_linkedin.py` | TODO |
| S6-02b | LinkedIn import frontend + API | Dev. S | Frontend + API | S6-02a | `tests/test_api.py` | TODO |
| S6-03a | AI mock interview backend | Dev. A | Backend | -- | `tests/test_interview.py` | TODO |
| S6-03b | AI mock interview frontend | Dev. S | Frontend + API | S6-03a | `tests/test_api.py` | TODO |
| S7-01a | Saved searches + alerts backend | Dev. A | Backend | -- | `tests/test_job_alerts.py` | TODO |
| S7-01b | Saved searches + alerts frontend | Dev. S | Frontend + API | S7-01a | `tests/test_api.py` | TODO |
| S7-02a | Contact CRM backend | Dev. A | Backend | -- | `tests/test_contacts.py` | TODO |
| S7-02b | Contact CRM frontend + API | Dev. S | Frontend + API | S7-02a | `tests/test_api.py` | TODO |
| S8-01a | Admin portal backend | Dev. A | Backend | -- | `tests/test_admin.py` | TODO |
| S8-01b | Admin portal frontend + API | Dev. S | Frontend + API | S8-01a | `tests/test_api.py` | TODO |
| S8-02a | Employer portal backend (full) | Dev. A | Backend | S3-04 | `tests/test_employer.py` | TODO |
| S8-02b | Employer portal frontend + API | Dev. S | Frontend + API | S8-02a | `tests/test_api.py` | TODO |
| S9-01a | Auto-apply agent backend | Dev. A | Backend | -- | `tests/test_auto_apply.py` | TODO |
| S9-01b | Auto-apply frontend + API | Dev. S | Frontend + API | S9-01a | `tests/test_api.py` | TODO |
| S9-02a | Calendar integration backend | Dev. A | Backend | -- | `tests/test_calendar.py` | TODO |
| S9-02b | Calendar integration frontend + API | Dev. S | Frontend + API | S9-02a | `tests/test_api.py` | TODO |
| S9-03 | Multi-language resume generation | Dev. A | Backend | -- | `tests/test_document_generator.py` | TODO |
| S9-04 | Multi-language frontend | Dev. S | Frontend | S9-03 | Manual | TODO |
| S10-01a | Webhooks + plugin system backend | Dev. A | Backend | -- | `tests/test_webhooks.py` | TODO |
| S10-01b | Webhooks management UI | Dev. S | Frontend + API | S10-01a | `tests/test_api.py` | TODO |
| S10-02 | Auth + multi-tenant | Dev. A | Backend | S0-02 | `tests/test_auth.py` | TODO |
| S10-03a | Notification center backend | Dev. A | Backend | -- | `tests/test_notifications.py` | TODO |
| S10-03b | Notification center frontend | Dev. S | Frontend + API | S10-03a | `tests/test_api.py` | TODO |
| S11-01a | Analytics v2 backend | Dev. A | Backend | -- | `tests/test_analytics.py` | TODO |
| S11-01b | Analytics v2 frontend | Dev. S | Frontend + API | S11-01a | `tests/test_api.py` | TODO |
| S11-02a | Salary intelligence backend | Dev. A | Backend | S2-04 | `tests/test_salary_data.py` | TODO |
| S11-02b | Salary intelligence frontend | Dev. S | Frontend + API | S11-02a | `tests/test_api.py` | TODO |
| S12-01a | Mobile API + backend | Dev. A | Backend | -- | `tests/test_api.py` | TODO |
| S12-01b | Mobile app (React Native) | Dev. S | Frontend (mobile) | S12-01a | Mobile tests | TODO |

### Task count by owner

| Owner | Total tasks | Done | Remaining | Backend core | API/Frontend | Shared |
|-------|-------------|------|-----------|-------------|--------------|--------|
| Dev. A | 30 | 6 | 24 | 28 | 0 | 2 |
| Dev. S | 30 | 0 | 30 | 3 | 25 | 2 |

## 11) Parallel Lanes (Full Timeline)

**Sprint 0 (Days 1-5 / Week 1) -- Infrastructure:**
- Dev. A: S0-01 (Supabase migration), then S0-02 (Auth)
- Dev. S: S0-03 (config, can start Day 1)
- Integration point: Database connection string (Day 1-2)

**Sprint 1 (Days 6-12 / Weeks 2-3) -- Core Features:**
- Dev. A: S1-01, S1-02, S1-03 (DONE), S1-06 (all independent backend services)
- Dev. S: S1-04 (export), then S1-05 (API routes after S1-01 ready), then S1-07 (dashboard UI after S1-06 ready)
- Integration points: JSearch field mapping contract (Day 6), dashboard API contract (Day 7)

**Sprint 2 (Days 13-19 / Weeks 3-4) -- Intelligence:**
- Dev. A: S2-01 (DONE), S2-02 (DONE), S2-03a (DONE), S2-05 (DONE), S2-06a (DONE)
- Dev. S: S2-04 (salary benchmarks, independent), S2-03b (API/frontend after Dev. A ships tool), S2-06b (API/frontend after Dev. A ships parser)
- Integration points: Career Dreamer API contract (Day 13), resume parser output format (Day 14)

**Sprint 3 (Days 20-28 / Weeks 4-5) -- Compliance + Employer Foundation:**
- Dev. A: S3-01, S3-02 (compliance, parallel), S3-04 (employer backend)
- Dev. S: S3-03 (employer frontend), S3-05 (datetime fix), S3-06 (salary UI, after S2-04)
- Integration points: Employer data model contract (Day 20), GDPR endpoint shapes (Day 21)

**Sprint 4 (Days 29-42 / Weeks 5-7) -- Frontend Migration:**
- Dev. A: Available for bug fixes, backend hardening, code review support
- Dev. S: S4-01 (React/Next.js migration -- BLOCKS all subsequent frontend work), then S4-02 (resume templates)
- Integration point: API contract stability required (no breaking changes during migration)

**Sprint 5 (Days 43-56 / Weeks 7-9) -- Extension + Kanban:**
- Dev. A: S5-02a (kanban backend)
- Dev. S: S5-01 (Chrome extension v1), S5-02b (kanban frontend after S5-02a ready)
- Integration point: Saved job data model (Day 43), kanban API contract (Day 44)

**Sprint 6 (Days 57-70 / Weeks 9-11) -- Autofill + LinkedIn + Interview:**
- Dev. A: S6-01a (autofill backend), S6-02a (LinkedIn backend), S6-03a (interview backend)
- Dev. S: S6-01b (autofill frontend after S6-01a), S6-02b (LinkedIn frontend after S6-02a), S6-03b (interview frontend after S6-03a)
- Integration points: Autofill data format (Day 57), LinkedIn data model (Day 58), interview session API (Day 59)

**Sprint 7 (Days 71-84 / Weeks 11-13) -- Saved Searches + CRM:**
- Dev. A: S7-01a (alerts backend), S7-02a (contact CRM backend)
- Dev. S: S7-01b (alerts frontend after S7-01a), S7-02b (CRM frontend after S7-02a)
- Integration points: Alert data model (Day 71), contact data model (Day 72)

**Sprint 8 (Days 85-105 / Weeks 13-16) -- Admin + Employer:**
- Dev. A: S8-01a (admin backend), S8-02a (employer backend, full marketplace)
- Dev. S: S8-01b (admin frontend after S8-01a), S8-02b (employer frontend after S8-02a)
- Integration points: RBAC model (Day 85), employer full API contract (Day 90)

**Sprint 9 (Days 106-126 / Weeks 16-19) -- Automation + Integrations:**
- Dev. A: S9-01a (auto-apply backend), S9-02a (calendar backend), S9-03 (multi-language)
- Dev. S: S9-01b (auto-apply frontend after S9-01a), S9-02b (calendar frontend after S9-02a), S9-04 (multi-language frontend after S9-03)
- Integration points: Auto-apply queue API (Day 106), calendar OAuth flow (Day 110)

**Sprint 10 (Days 127-140 / Weeks 19-21) -- Platform Infrastructure:**
- Dev. A: S10-01a (webhooks backend), S10-02 (auth/multi-tenant), S10-03a (notifications backend)
- Dev. S: S10-01b (webhooks UI after S10-01a), S10-03b (notifications frontend after S10-03a)
- Integration points: Webhook event format (Day 127), notification WebSocket protocol (Day 130)

**Sprint 11 (Days 141-161 / Weeks 21-24) -- Analytics + Salary:**
- Dev. A: S11-01a (analytics v2 backend), S11-02a (salary intelligence backend)
- Dev. S: S11-01b (analytics v2 frontend after S11-01a), S11-02b (salary frontend after S11-02a)
- Integration points: Analytics data shape (Day 141), salary API contract (Day 145)

**Sprint 12 (Days 162-182 / Weeks 24-26) -- Mobile:**
- Dev. A: S12-01a (mobile API + backend)
- Dev. S: S12-01b (React Native app after S12-01a)
- Integration points: Mobile API contract (Day 162)

---

# PART 4: Revenue Model

---

Based on competitor pricing analysis:

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 5 job searches/day, 2 resumes/month, basic tracking, chat |
| **Pro** | $19/month | Unlimited search, unlimited resumes, all templates, autofill, saved searches, mock interviews, daily alerts |
| **Premium** | $39/month | Everything in Pro + auto-apply (50/day), salary intelligence, priority support, calendar integration |
| **Enterprise** | Custom | Admin portal, team management, employer portal, API access, SSO, dedicated support |

**Comparison:**
- Cheaper than Teal ($29/mo), Huntr ($40/mo), Careerflow ($45/mo)
- More features than all of them
- Privacy-first (unique selling point)
- Full API access at Enterprise (no competitor offers this)

**Employer-side pricing:**

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 1 job posting |
| **Pro** | $99/month | 10 job postings, candidate matching, analytics |
| **Enterprise** | $499/month | Unlimited postings, priority matching, API access, dedicated support |

---

# PART 5: Non-Functional Requirements

---

### Performance
- API response time: < 200ms (p95) for non-LLM endpoints
- LLM endpoints: < 5s (p95) with streaming
- Frontend: Lighthouse score > 90 (performance, accessibility, SEO)
- Database queries: < 50ms (p95) with proper indexing

### Security
- OWASP Top 10 compliance
- Rate limiting on all endpoints (existing, extend to user-based)
- CSP headers (existing)
- Input validation on all user-facing endpoints (existing via Pydantic)
- Dependency scanning (Snyk/Dependabot)
- Pen testing before public launch

### Observability
- Structured logging (JSON) with correlation IDs
- Error tracking (Sentry)
- APM (Application Performance Monitoring)
- LLM cost tracking per user/request
- Uptime monitoring with PagerDuty/OpsGenie

### Testing
- Unit tests for all new services (pytest)
- Integration tests for API endpoints
- E2E tests for critical user flows (Playwright)
- Chrome extension tests (Puppeteer)
- Load testing (Locust) before launch
- Target: 80%+ code coverage

---

# PART 6: Technology Additions Summary

---

### Backend (Python)

| Package | Purpose | Sprint |
|---------|---------|--------|
| `alembic` | Database migrations | S0 |
| `psycopg2-binary` | PostgreSQL driver | S0 |
| `supabase` | Supabase Python client | S0 |
| `PyJWT` | JWT validation | S0 |
| `fpdf2` | PDF generation | S1 |
| `python-docx` | DOCX generation | S1 |
| `pdfplumber` | PDF parsing for resume upload | S2 |
| `weasyprint` | HTML-to-PDF rendering for resume templates | S4 |
| `celery` + `redis` | Background job queue (alerts, auto-apply) | S7 |
| `playwright` | Browser automation for auto-apply | S9 |
| `playwright-stealth` | Anti-bot-detection for auto-apply | S9 |
| `google-api-python-client` | Google Calendar/Gmail integration | S9 |
| `websockets` | Real-time notifications | S10 |
| `sentry-sdk` | Error tracking | S10 |

### Frontend (JavaScript/TypeScript)

| Package | Purpose | Sprint |
|---------|---------|--------|
| `next@14` | React framework | S4 |
| `react@18` | UI library | S4 |
| `tailwindcss@4` | CSS framework | S4 |
| `@shadcn/ui` | Component library | S4 |
| `zustand` | State management | S4 |
| `@tanstack/react-query` | Data fetching + caching | S4 |
| `framer-motion` | Animations | S4 |
| `next-pwa` | PWA support | S4 |
| `playwright` | E2E testing | S4 |
| `@dnd-kit/core` | Drag-and-drop for kanban | S5 |
| `@dnd-kit/sortable` | Sortable lists | S5 |
| `recharts` | Charts for analytics | S11 |

### Chrome Extension

| Package | Purpose | Sprint |
|---------|---------|--------|
| `plasmo` | Chrome extension framework | S5 |
| `react` | Extension popup UI | S5 |

---

# PART 7: Success Metrics

---

| Metric | Target | Measurement |
|--------|--------|-------------|
| User interview callback rate | 3x improvement (match Teal's claim) | A/B test with/without AI tailoring |
| Application completion time | < 2 min per app (with autofill) | Extension telemetry |
| Daily active users | 10K within 6 months of launch | Analytics |
| Chrome extension installs | 50K within 6 months | Chrome Web Store |
| User NPS | > 50 | In-app survey |
| API uptime | 99.9% | Monitoring |
| LLM cost per user | < $0.50/month | Cost tracking |
