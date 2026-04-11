# JobPath AI - Project Roadmap

**Version:** 2.0
**Last Updated:** 2026-04-11
**Goal:** Transform JobPath AI into an autonomous career agent that finds jobs, prepares applications, applies, tracks outcomes, and learns - while the user just approves.

**Design standard:** Every interaction follows the Google Career Dreamer pattern. The AI proposes, the user confirms. No blank forms. No manual data entry.

---

## Current State (what exists today)

**Backend (functional):**
- Agentic loop with 13 tools (search, resume, cover letter, ATS scoring, career dreamer, skill gaps, tracking, analytics)
- Dual job APIs (JSearch + Adzuna) with scoring
- Document generation with PDF/DOCX export
- Privacy pipeline (PII sanitization, AES-256-GCM encryption, protected attribute stripping)
- FastAPI with 25+ endpoints, rate limiting, security headers
- JWT auth module (built, disabled - needs wiring)
- Session-based in-memory storage (profiles not persisted to DB)

**Mobile (structural, not usable):**
- React Native + Expo with 5-tab navigation
- Screens exist (Dashboard, Search, Chat, Kanban, Profile) but most are empty shells
- Job search shows only job IDs, no details
- No application flow, no document export UI, no career dreamer UI
- Zustand stores + API client wired

**Web (static):**
- Single HTML landing page with 3-step profile setup modal
- Ephemeral sessions (1-hour TTL)

**Critical gaps:**
- No real auth / persistent accounts
- Profiles not saved to database (in-memory only, lost on restart)
- profile_to_orm() / orm_to_profile() defined but never called
- Job search results show raw IDs, not rich cards
- No application prep workflow UI
- No career dreamer UI (backend tools exist, no frontend)
- No document customization / variant system
- No follow-up nudge system
- No autonomous apply
- "Reset Session" instead of real logout/delete account

---

## Sprint 1: Foundation (make it real)

**Goal:** User can sign up, create a profile through the Career Dreamer scaffold flow, see real job results, and save jobs.

### Auth & Persistence
- [ ] Enable GCP Identity Platform (src/auth.py is 60% built)
- [ ] Add signup/login screens (email + Google OAuth)
- [ ] Fix session_store.py user_id mapping (line 155 bug - sessions keyed by UUID, not user_id)
- [ ] Wire profile_to_orm() / orm_to_profile() so profiles persist to DB
- [ ] Add DB migration for any schema changes
- [ ] Replace "Reset Session" with real Sign Out

### Scaffold Onboarding (Career Dreamer pattern)
- [ ] Path A: Resume upload -> AI extracts -> present roles/tasks/skills for confirmation
- [ ] Path B: Conversational onboarding (one question per screen)
  - Screen 1: "Share a current or previous role" (single text field)
  - Screen 2: AI generates tasks for that role - user selects which apply (Re-generate option)
  - Screen 3: AI generates skills - user selects (More skills... to add custom)
  - Screen 4: Education / certifications (optional tags)
  - Screen 5: Interests (for career exploration)
- [ ] Path C: LinkedIn OAuth import (future - defer to Sprint 2 if complex)
- [ ] Career Identity Statement generation (AI-written, editable, re-generable, STARTER DRAFT label)
- [ ] Location & preferences screen (multi-select cities, remote options, work arrangements)
- [ ] Non-compete company input

### Rich Job Search
- [ ] New endpoint: GET /api/jobs/{job_id} returning full cached job details
- [ ] Expand JobSearchRequest with all filter fields (type, salary, experience, recency)
- [ ] Pass filters to JSearch (employment_type, salary_range, remote) and Adzuna (salary_min/max, contract_type, category)
- [ ] Return structured job objects in response (not just IDs + markdown)
- [ ] Job card UI: title, company, location, salary, match score, work arrangement tag, source
- [ ] Job detail screen: full description, requirements, match breakdown
- [ ] Save job action (POST /api/jobs/{id}/save -> adds to Kanban "Saved")
- [ ] Persist saved jobs to DB (not just in-memory cache)
- [ ] Pagination support

### Quality gates
- [ ] ruff, pyright, pytest all pass
- [ ] Auth flow works end-to-end: signup -> login -> profile persists -> logout -> login again
- [ ] Job search returns rich cards with details
- [ ] Saved jobs survive server restart

---

## Sprint 2: The Experience (the money features)

**Goal:** User can explore career possibilities, prepare tailored applications with premium document export, and track them.

### Career Dreamer
- [ ] Career web visualization (constellation of career dots)
- [ ] Two dot types: data-backed (BLS/O*NET data) and AI-inspired (creative pivots)
- [ ] Role detail cards with 5 sections:
  - Role overview (salary per target location, education, growth outlook)
  - Sweet spots (skill overlap with personalized explanations)
  - A day in the life (AI-generated daily tasks)
  - Areas for growth (gap skills with bridge explanations)
  - Upskilling resources (carousel of courses/certs with links)
- [ ] "Find jobs for this role" action (filters job feed for selected career)
- [ ] "Save this dream" action (persists for ongoing tracking)
- [ ] Previous/Next role navigation + sidebar dots
- [ ] Career Dreamer report: side-by-side comparison, skill overlap visual, feasibility score, upskill timeline

### Application Prep Flow
- [ ] "Prepare Application" button on job cards and detail screens
- [ ] Step 1: Tailored resume generation (humanized, passes AI detection)
  - Diff highlights showing what was changed from base resume
  - Career Identity Statement as header
  - Inline editing
  - Tone selection (professional / creative / technical / executive)
- [ ] Step 2: Tailored cover letter (company-specific hook, humanized)
  - Inline editing
- [ ] Step 3: ATS score check with visual gauge
  - One-tap fix for low scores
  - Auto-revise and re-score
- [ ] Step 4: Document Studio (premium export)
  - Template selection with live preview
  - Font, color accent, section ordering, spacing controls
  - Full-page rendered preview (exactly as printed)
  - Export: PDF, DOCX, plain text, "send to my email"

### Document Variant System
- [ ] DB table: document_variants (linked to application_id, job_id, user_id)
- [ ] Each application saves its resume variant + cover letter variant + ATS score + tailoring notes
- [ ] Variants accessible from pipeline cards ("What did I send to this company?")
- [ ] Lifecycle: active while application is live, archived on rejection, analyzed on acceptance
- [ ] "Winning version" analysis when application reaches Accepted

### Salary Calibration
- [ ] BLS OEWS API integration (occupation wages by metro area)
- [ ] H-1B LCA data integration (company-specific salaries)
- [ ] Job posting salary range extraction (from JSearch/Adzuna results)
- [ ] Salary comparison cards per target location
- [ ] Level check ("You qualify for Senior, aim higher")
- [ ] Opportunity spotlight (best markets for user's skills)

### Advanced Search Filters
- [ ] Wire all unused JSearch/Adzuna API parameters
- [ ] Filter UI: role, location, work arrangement, experience, salary range, date posted, industry
- [ ] Role expansion suggestions ("Your profile also fits Analytics Engineer")
- [ ] Sort options: match score, salary, date, relevance

### Quality gates
- [ ] Career Dreamer web loads with real data (BLS/O*NET)
- [ ] Application prep flow works end-to-end: generate -> customize -> export -> track
- [ ] Document variants persist and are viewable from pipeline
- [ ] Salary calibration shows real numbers with cited sources

---

## Sprint 3: Agent Autonomy

**Goal:** The agent works proactively. It finds jobs overnight, follows up on stale applications, and can apply on behalf of the user.

### Daily Curated Feed
- [ ] Scheduled job search based on user's profile + preferences
- [ ] Agent-curated home screen: "7 new matches since yesterday. 3 above 90%."
- [ ] AI annotations on each card ("Strong match - your X experience is exactly what they need")
- [ ] Pre-prepared applications for top matches (user just reviews and approves)

### Follow-up Nudge System
- [ ] DB table: follow_up_schedule (application_id, next_nudge_date, nudge_count, status)
- [ ] Day 3: Quiet. No nudge. Too early.
- [ ] Day 7: "Have you heard from [Company]?" (Yes got response / No nothing / Skip)
  - If "Yes" -> ask for details, update pipeline status
  - If "No" -> offer to draft follow-up email
  - If "Skip" -> wait another week
- [ ] Day 14: "Still no word after 2 weeks. Want me to follow up?"
- [ ] Day 21: "I've drafted a warm but direct follow-up. Want to review?"
- [ ] Day 30+: "No response after a month. Archive or one more try?"
- [ ] Post-interview check-in: "How did it go? Any feedback?" (logs for pattern analysis)
- [ ] Accepted state: celebration moment + winning variant analysis + "Switch to Career Growth mode?"
- [ ] Push notification support (opt-in per type)
- [ ] Per-application disable option
- [ ] Global nudge frequency settings

### Autonomous Apply
- [ ] Confidence scoring per job match
- [ ] Threshold config in settings (default 85%)
- [ ] Auto-apply on safe channels (email, career pages) above threshold
- [ ] Pre-fill + queue for review on risky channels (LinkedIn, Indeed)
- [ ] Morning briefing notification: "4 sent, 2 queued, 1 interview invite"
- [ ] Non-compete exclusion enforcement
- [ ] Never apply to same company twice (unless different role)
- [ ] All documents humanized before send

### Skill Gap Intelligence Dashboard
- [ ] Skills radar visualization (green/yellow/red zones)
- [ ] Upskill ROI cards with salary impact per location
- [ ] "Add to my plan" button per skill
- [ ] Recommended resources with links

### Guided Journey for New Users
- [ ] Visual checklist on dashboard for new users (not empty state)
  - Tell us about yourself (profile)
  - Discover your market value (salary calibration)
  - Explore career possibilities (career dreamer)
  - Review your skill gaps
  - Apply to your first opportunity
- [ ] Each step links directly to the relevant screen
- [ ] Progress bar showing completion
- [ ] Transitions to active dashboard once first application is submitted

### Contextual AI (replace dedicated chat page)
- [ ] Floating AI button component on every screen
- [ ] Context injection: button knows which screen, which job, which application
- [ ] Inline AI suggestions per screen (feed, detail, pipeline, dashboard)
- [ ] Full open-ended chat available via the floating button
- [ ] Remove dedicated Chat tab from bottom navigation

### Quality gates
- [ ] Daily feed populates with real jobs without user action
- [ ] Nudge system fires on schedule (testable with accelerated time)
- [ ] Autonomous apply sends real applications (tested with safe channel mock)
- [ ] Contextual AI responds differently per screen context

---

## Sprint 4: Intelligence & Growth

**Goal:** The agent learns from outcomes, coaches salary negotiations, helps with networking, and handles account lifecycle.

### Outcome Learning
- [ ] Correlate resume variant styles with callback rates
- [ ] Track: which tones, keywords, and formats get responses
- [ ] Agent applies winning patterns to future applications proactively
- [ ] "Your technical-tone resumes get 2x more callbacks for backend roles"

### Rejection Analysis
- [ ] Pattern detection across all rejections
- [ ] "3 rejections from roles requiring system design - add a prep module?"
- [ ] Resume variant comparison: what did rejected versions lack?
- [ ] Automatic base resume adjustment suggestions

### Weekly Advisor Report
- [ ] Performance card: applications, callbacks, trend chart
- [ ] Pattern card: best sectors, best tones, best keywords
- [ ] Recommendation card: where to focus this week
- [ ] Push notification with summary

### Cold Outreach
- [ ] Alumni/network matching (from profile data)
- [ ] Agent drafts introduction messages
- [ ] User approval required before any send
- [ ] Sent from user's connected email
- [ ] Templates customizable

### Salary Negotiation
- [ ] Counter-offer scripts with sourced market data
- [ ] Offer comparison across active applications
- [ ] "This offer is 12% below market for your level"

### Career Dreamer Tracking
- [ ] Saved dream goals re-scored over time
- [ ] "Your ML Engineer feasibility went from 58 to 71 after completing PyTorch cert"
- [ ] Connected to rejection patterns: "Your Finance applications have 35% callback - considered FinTech?"

### Email Integration (if feasible this sprint)
- [ ] Gmail/Outlook OAuth connection (minimal scopes)
- [ ] Agent composes application emails FROM user's account
- [ ] Reply monitoring: classify responses (rejection / interview / offer / follow-up)
- [ ] Auto-update pipeline status from email classification
- [ ] Calendar: detect interview invites, propose adding to user's calendar

### Account Lifecycle
- [ ] GET /api/account/export (ZIP of all user data)
- [ ] DELETE /api/account (cascading delete)
- [ ] DELETE /api/employer/waitlist/{email} (unsubscribe)
- [ ] Proper sign-out (clear tokens, not "reset session")
- [ ] GDPR-compliant data retention documentation

### Quality gates
- [ ] Outcome learning produces actionable insights after 10+ applications
- [ ] Weekly report generates with real data
- [ ] Account export includes all user data
- [ ] Account delete removes everything from DB (verified with query)

---

## Sprint 5+ (Backlog - User-Critical Features)

These are features a paying user would expect but don't fit cleanly into Sprints 1-4:

- [ ] Offer comparison dashboard (side-by-side: salary, benefits, equity, growth, location for 2+ active offers)
- [ ] Job alerts / saved searches ("Notify me when new Senior PM roles post in Berlin paying 90K+")
- [ ] Application deadline warnings ("This role closes in 2 days. Prepare application now?")
- [ ] Interview prep depth: format hints (panel/whiteboard/take-home), culture cues, post-interview debrief template
- [ ] Multi-language document generation (resume/cover letter in target country's language)
- [ ] Referral tracking per application ("Were you referred? By whom?" - changes follow-up strategy)
- [ ] Accessibility: screen reader support, high contrast mode, full keyboard navigation
- [ ] Application analytics breakdown by company type/size/industry (not just overall rates)
- [ ] Portfolio/project showcase section (for creative roles, developers, designers)

---

## Not In Scope (separate timelines)

- Employer portal (separate product)
- Admin portal (not until multi-tenant)
- Stripe payments (not until product-market fit)
- Email OAuth send/receive integration (complex, Sprint 3+ at earliest)
- LinkedIn full API integration (defer - OAuth profile import first)
- Chrome extension job scraping (defer)
- Interview mock sessions with voice (defer)

---

## Data Sources

| Source | Data | Cost | Status |
|--------|------|------|--------|
| BLS OEWS API | Occupation wages by metro area | Free (500/day) | Not yet integrated |
| H-1B LCA data | Company-specific salaries | Free (bulk download) | Not yet integrated |
| O*NET | Occupation descriptions, skills, education, growth | Free | Not yet integrated |
| JSearch API | Indeed/LinkedIn/Glassdoor listings | Free tier + paid | Integrated |
| Adzuna API | Job listings across 20 countries | Free tier + paid | Integrated |
| Job posting salary extraction | Salary ranges from listings | Free | Partially integrated |

---

## Architecture Notes

**Backend:** Python/FastAPI, SQLAlchemy ORM, SQLite (dev) / PostgreSQL (prod), Alembic migrations
**Mobile:** React Native + Expo, Zustand stores, NativeWind styling
**Web:** Static HTML SPA (to be replaced by mobile Expo web target)
**LLM:** OpenRouter (Claude Sonnet primary, Gemini Flash for bulk ops)
**Auth:** GCP Identity Platform (JWT, already partially built in src/auth.py)
**Privacy:** AES-256-GCM at rest, PII sanitization before LLM, protected attribute stripping
