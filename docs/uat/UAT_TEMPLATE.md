# UAT Test Scenarios - AI Job Agent

> Generated from codebase analysis on 2026-04-11.
> Total scenarios: 112 across 5 sprints + cross-cutting concerns.

---

## Sprint 1: Foundation

### 1.1 Health & Session

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S1-01 | Health Check | Verify health endpoint returns system status | GET /api/health | 200 with status, sessions count, db status, llm_configured boolean | P0 | api.py:180 |
| S1-02 | Health Check | DB down returns degraded status | GET /api/health when DB is unreachable | 503 with status="degraded", db="error" | P1 | api.py:198-200 |
| S1-03 | Session Create | Create new session | POST /api/session | 201 with session_id (UUID format) | P0 | api.py:204-209 |
| S1-04 | Session Create | Rate limit enforced at 30/hour | POST /api/session 31 times in 1 hour | 429 "Rate limit exceeded. Try again later." on 31st request | P1 | api.py:205 |
| S1-05 | Session Create | Session cleanup evicts expired sessions (TTL 3600s) | Create session, wait >3600s, then attempt to use it | 404 "Session not found or profile not set up." | P1 | session_store.py:21-22 |
| S1-06 | Session Create | Max 500 concurrent sessions enforced | Create 501 sessions | Oldest session evicted, 501st created successfully | P2 | session_store.py:20 |
| S1-07 | Profile Set | Create profile and initialize agent | POST /api/profile with valid body + X-Session-ID | 201 with profile_id, message, currency | P0 | api.py:212-255 |
| S1-08 | Profile Set | Profile validation -- name max 200 chars | POST /api/profile with name >200 chars | 422 validation error | P1 | schemas.py:16 |
| S1-09 | Profile Set | Profile validation -- invalid email | POST /api/profile with email="notanemail" | 422 validation error | P1 | schemas.py:17 |
| S1-10 | Profile Set | Profile validation -- years_of_experience range 0-70 | POST /api/profile with years_of_experience=71 | 422 validation error | P1 | schemas.py:22 |
| S1-11 | Profile Set | URL validation -- portfolio_url must start with http(s):// | POST /api/profile with portfolio_url="example.com" | 422 "URL must start with https:// or http://" | P1 | schemas.py:35-42 |
| S1-12 | Profile Set | Skills deduplication on create | POST /api/profile with skills=["Python","Python","Java"] | Profile created with skills=["Python","Java"] | P1 | models.py:78-81 |
| S1-13 | Profile Set | Rate limit 10/minute | POST /api/profile 11 times in 1 minute | 429 on 11th request | P2 | api.py:213 |
| S1-14 | Profile Get | Retrieve saved profile | GET /api/profile with valid session | 200 with profile fields | P0 | api.py:258-262 |
| S1-15 | Profile Get | No profile returns 404 | GET /api/profile with session but no profile | 404 "No profile found for this session." | P1 | session_store.py:155-156 |
| S1-16 | Session Missing | Endpoint without session header | GET /api/profile without X-Session-ID when AUTH_ENABLED=false | 400 "X-Session-ID header is required." | P1 | auth.py:157-161 |

### 1.2 Authentication

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S1-17 | Signup | Create new account via GCP Identity Platform | POST /api/auth/signup with email, password (min 6 chars), name | 201 with id_token, refresh_token, user_id, expires_in | P0 | routers/auth.py:36-66 |
| S1-18 | Signup | Auth service not configured | POST /api/auth/signup when GCP_IDENTITY_PLATFORM_API_KEY is empty | 503 "Authentication service not configured." | P1 | routers/auth.py:40-44 |
| S1-19 | Signup | Password too short (<6 chars) | POST /api/auth/signup with password="12345" | 422 validation error (min_length=6) | P1 | schemas.py:152 |
| S1-20 | Signup | Rate limit 10/hour | POST /api/auth/signup 11 times in 1 hour | 429 on 11th request | P2 | routers/auth.py:37 |
| S1-21 | Login | Sign in with email and password | POST /api/auth/login with valid credentials | 200 with id_token, refresh_token, user_id, expires_in | P0 | routers/auth.py:68-97 |
| S1-22 | Login | Wrong password | POST /api/auth/login with wrong password | 401 with IDP error message | P1 | routers/auth.py:88-89 |
| S1-23 | Login | Rate limit 20/hour | 21 login attempts in 1 hour | 429 on 21st request | P2 | routers/auth.py:69 |
| S1-24 | Google OAuth | Exchange Google ID token for credentials | POST /api/auth/google with valid id_token | 200 with id_token, refresh_token, user_id | P0 | routers/auth.py:99-129 |
| S1-25 | Token Refresh | Exchange refresh token for new ID token | POST /api/auth/refresh with valid refresh_token | 200 with new id_token, refresh_token | P0 | routers/auth.py:131-157 |
| S1-26 | Sign Out | Delete server-side session | DELETE /api/auth/session with valid session | 204 No Content | P0 | routers/auth.py:159-163 |
| S1-27 | Auth Guard | Bearer token required when AUTH_ENABLED=true | Any request without Authorization header when AUTH_ENABLED=true | 401 "Authorization header required (Bearer <token>)" | P0 | src/auth.py:139-145 |
| S1-28 | Auth Guard | Expired token rejected | Request with expired JWT when AUTH_ENABLED=true | 401 "Token expired" | P1 | src/auth.py:117-120 |

### 1.3 Onboarding

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S1-29 | Generate Tasks | Generate tasks for a role | POST /api/onboarding/generate-tasks with role="Software Engineer" | 200 with tasks list and role echoed back | P0 | routers/onboarding.py:38-43 |
| S1-30 | Generate Tasks | Role max length 200 | POST /api/onboarding/generate-tasks with role >200 chars | 422 validation error | P1 | schemas.py:179 |
| S1-31 | Generate Skills | Generate skills from role + tasks | POST /api/onboarding/generate-skills with role and selected_tasks | 200 with skills list | P0 | routers/onboarding.py:45-51 |
| S1-32 | Identity Statement | Generate career identity statement | POST /api/onboarding/generate-identity-statement with name, skills, desired_roles, experience_level | 200 with statement and label="STARTER DRAFT" | P0 | routers/onboarding.py:53-65 |
| S1-33 | Confirm Profile | Finalize profile after onboarding wizard | POST /api/onboarding/confirm-profile with full profile + career_identity_statement, non_compete_companies, interests | 201 with profile_id, message, currency | P0 | routers/onboarding.py:68-120 |
| S1-34 | Confirm Profile | Non-compete companies stored | POST /api/onboarding/confirm-profile with non_compete_companies=["Google","Meta"] | Profile persisted with non_compete list | P1 | routers/onboarding.py:98 |

### 1.4 Job Search

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S1-35 | Search V1 | Basic job search | POST /api/jobs/search with location_filter and include_remote | 200 with response text, job_ids list, job_cache_size | P0 | routers/jobs.py:37-61 |
| S1-36 | Search V1 | Max results capped at 50 | POST /api/jobs/search with max_results=51 | 422 validation error (le=50) | P1 | schemas.py:48 |
| S1-37 | Search V1 | Job cache max 200 -- oldest evicted | Search until cache has 200 jobs, then search again | Oldest cache entry evicted, new jobs added | P1 | routers/jobs.py:53-55, agent.py:57 |
| S1-38 | Search V2 | Enhanced search with filters and pagination | POST /api/jobs/search/v2 with job_type, salary_min, sort_by="salary", page=2 | 200 with jobs list, total, page, has_more | P0 | routers/jobs.py:63-153 |
| S1-39 | Search V2 | Sort by date | POST /api/jobs/search/v2 with sort_by="date" | Jobs sorted by posted_date descending | P1 | routers/jobs.py:139-140 |
| S1-40 | Search V2 | Invalid sort_by value | POST /api/jobs/search/v2 with sort_by="random" | 422 validation error (pattern mismatch) | P1 | schemas.py:230 |
| S1-41 | Job Detail | Get specific job by ID | GET /api/jobs/{job_id} with valid session | 200 with full JobDetailResponse | P0 | routers/jobs.py:155-222 |
| S1-42 | Job Detail | Job not found | GET /api/jobs/{unknown_id} | 404 "Job not found." | P1 | routers/jobs.py:190 |
| S1-43 | Save Job | Save a job to user's list | POST /api/jobs/{job_id}/save | 200 with message="Job saved.", saved=true | P0 | routers/jobs.py:224-292 |
| S1-44 | Save Job | Duplicate save returns already saved | POST /api/jobs/{job_id}/save for already saved job | 200 with message="Job already saved." | P1 | routers/jobs.py:280 |
| S1-45 | Unsave Job | Remove job from saved list | DELETE /api/jobs/{job_id}/save | 200 with saved=false | P0 | routers/jobs.py:294-316 |
| S1-46 | Saved Jobs | List all saved jobs | GET /api/jobs/saved | 200 with jobs list, total count, is_saved=true | P0 | routers/jobs.py:318-355 |
| S1-47 | Job Import | Import job from Chrome extension | POST /api/jobs/import with title, company, source_url | 200 with job_id, title, company | P0 | routers/jobs.py:357-410 |
| S1-48 | Job Import | Duplicate URL returns is_duplicate=true | POST /api/jobs/import with existing source_url | 200 with is_duplicate=true | P1 | routers/jobs.py:371-376 |

---

## Sprint 2: The Experience

### 2.1 Career Dreamer

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S2-01 | Dream Analysis | Run career dream analysis | POST /api/career/dream with dream_role, timeline_months | 200 with dream_id, analysis text, timeline_months echoed | P0 | routers/career.py:69-97 |
| S2-02 | Dream Analysis | Timeline range 1-120 months | POST /api/career/dream with timeline_months=121 | 422 validation error (le=120) | P1 | routers/career.py:22 |
| S2-03 | Dream Detail | Get saved dream by ID | GET /api/career/dream/{dream_id}/detail | 200 with full CareerDreamResponse | P0 | routers/career.py:99-126 |
| S2-04 | Dream Detail | Dream not found | GET /api/career/dream/{invalid_id}/detail | 404 "Dream not found." | P1 | routers/career.py:113 |
| S2-05 | Find Jobs | Get search terms from dream | POST /api/career/dream/{dream_id}/find-jobs | 200 with search_terms (max 10), dream_role | P0 | routers/career.py:128-157 |
| S2-06 | Save Dream | Save dream to database | POST /api/career/dream/{dream_id}/save | 200 with "Dream saved successfully." | P0 | routers/career.py:159-191 |
| S2-07 | Save Dream | Duplicate save returns already saved | POST /api/career/dream/{dream_id}/save for existing dream | 200 with "Dream already saved." | P1 | routers/career.py:176 |
| S2-08 | List Dreams | List all saved career dreams | GET /api/career/dreams | 200 with dreams list, total count | P0 | routers/career.py:193-224 |
| S2-09 | Career Report | Generate comparison report across dreams | GET /api/career/report | 200 with agent response text | P1 | routers/career.py:226-240 |

### 2.2 Salary Calibration

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S2-10 | Calibrate | Calibrate salary for role across locations | POST /api/salary/calibrate with role, locations, skills | 200 with data_points, market_summary, arbitrage_analysis | P0 | routers/salary.py:54-77 |
| S2-11 | Calibrate | Role max length 500 | POST /api/salary/calibrate with role >500 chars | 422 validation error | P1 | routers/salary.py:19 |
| S2-12 | Negotiate | Generate counter-offer strategy | POST /api/salary/negotiate with current_offer, role, company | 200 with agent response including counter-offer amount | P0 | routers/salary.py:79-103 |
| S2-13 | Negotiate | Competing offer included in prompt | POST /api/salary/negotiate with competing_offer set | Response references competing offer in strategy | P1 | routers/salary.py:95-96 |
| S2-14 | Compare | Compare multiple offers | POST /api/salary/compare-offers with offers list (max 10) | 200 with comparison analysis | P0 | routers/salary.py:105-123 |

### 2.3 Document Generation

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S2-15 | Resume | Generate tailored resume | POST /api/documents/resume with valid job_id, tone="professional" | 200 with generated resume text | P0 | routers/jobs.py:446-468 |
| S2-16 | Resume | Invalid tone rejected | POST /api/documents/resume with tone="casual" | 422 "tone must be one of: academic, creative, executive, professional, technical" | P1 | schemas.py:64-69 |
| S2-17 | Resume | Job ID not in cache | POST /api/documents/resume with invalid job_id | 400 "Job ID not found in session cache." | P1 | routers/jobs.py:455-456 |
| S2-18 | Cover Letter | Generate tailored cover letter | POST /api/documents/cover-letter with valid job_id | 200 with generated cover letter text | P0 | routers/jobs.py:470-494 |
| S2-19 | Templates | List available resume templates | GET /api/documents/templates | 200 with templates list (id, name, description, tags, header_style, columns) | P0 | routers/documents.py:52-59 |
| S2-20 | Template Detail | Get specific template | GET /api/documents/templates/{template_id} | 200 with template info | P0 | routers/documents.py:61-76 |
| S2-21 | Template Detail | Template not found | GET /api/documents/templates/nonexistent | 404 "Template 'nonexistent' not found." | P1 | routers/documents.py:68 |
| S2-22 | Export | Export resume as PDF with template | POST /api/documents/export with job_id, template_id, format="pdf" | Binary PDF response with Content-Disposition header | P0 | routers/documents.py:78-135 |
| S2-23 | Export | Export as DOCX | POST /api/documents/export with format="docx" | Binary DOCX response | P1 | routers/documents.py:123-124 |
| S2-24 | Export | Invalid format rejected | POST /api/documents/export with format="txt" | 422 validation error (pattern mismatch for ^(pdf|docx)$) | P1 | routers/documents.py:33 |
| S2-25 | Export Content | Export raw markdown content | POST /api/documents/export-content with content, template_id | Binary file response | P0 | routers/documents.py:137-165 |

---

## Sprint 3: Agent Autonomy

### 3.1 Daily Feed

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S3-01 | Daily Feed | Get curated daily job feed | GET /api/feed/daily | 200 with items, new_count, high_match_count, summary | P0 | routers/feed.py:35-56 |
| S3-02 | Refresh Feed | Force regenerate feed | POST /api/feed/refresh | 200 with updated feed items | P0 | routers/feed.py:58-79 |
| S3-03 | Refresh Feed | Rate limit 3/minute | POST /api/feed/refresh 4 times in 1 minute | 429 on 4th request | P1 | routers/feed.py:59 |

### 3.2 Follow-up Nudges

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S3-04 | Pending Nudges | Get active nudges | GET /api/nudges/pending | 200 with nudges list (active status), total count | P0 | routers/nudges.py:66-101 |
| S3-05 | Respond | User responds "heard_back" | POST /api/nudges/{nudge_id}/respond with response_type="heard_back" | 200, nudge status set to "completed" | P0 | routers/nudges.py:103-132 |
| S3-06 | Respond | User responds "no_response" | POST /api/nudges/{nudge_id}/respond with response_type="no_response" | 200, nudge count incremented, status remains "active" | P1 | routers/nudges.py:122 |
| S3-07 | Respond | Nudge not found | POST /api/nudges/{invalid_id}/respond | 404 "Nudge not found." | P1 | routers/nudges.py:118 |
| S3-08 | Draft Email | AI-draft follow-up email | GET /api/nudges/{nudge_id}/draft-email | 200 with nudge_id, subject, body | P0 | routers/nudges.py:134-167 |
| S3-09 | Pause | Pause a nudge schedule | PUT /api/nudges/{nudge_id}/pause | 200 with "Nudge paused.", status becomes "paused" | P0 | routers/nudges.py:169-194 |
| S3-10 | Settings | Update nudge settings | PUT /api/nudges/settings with default_interval_days=14, max_nudges=5 | 200 with settings echoed back | P0 | routers/nudges.py:196-210 |
| S3-11 | Settings | Interval range 1-60 days | PUT /api/nudges/settings with default_interval_days=61 | 422 validation error (le=60) | P1 | routers/nudges.py:41 |
| S3-12 | Settings | Max nudges range 1-10 | PUT /api/nudges/settings with max_nudges=11 | 422 validation error (le=10) | P1 | routers/nudges.py:42 |

### 3.3 Auto Apply

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S3-13 | Get Settings | Get auto-apply settings | GET /api/auto-apply/settings | 200 with user_id, enabled, confidence_threshold=0.85, max_daily=5 | P0 | routers/auto_apply.py:59-84 |
| S3-14 | Get Settings | Default settings when none saved | GET /api/auto-apply/settings for new user | 200 with defaults: enabled=false, confidence_threshold=0.85, max_daily=5 | P1 | routers/auto_apply.py:74 |
| S3-15 | Update Settings | Enable auto-apply with custom threshold | PUT /api/auto-apply/settings with enabled=true, confidence_threshold=0.9 | 200 with updated settings | P0 | routers/auto_apply.py:86-125 |
| S3-16 | Update Settings | Threshold range 0.0-1.0 | PUT /api/auto-apply/settings with confidence_threshold=1.5 | 422 validation error (le=1.0) | P1 | routers/auto_apply.py:28 |
| S3-17 | Update Settings | Max daily range 1-50 | PUT /api/auto-apply/settings with max_daily=51 | 422 validation error (le=50) | P1 | routers/auto_apply.py:30 |
| S3-18 | Queue | View queued applications | GET /api/auto-apply/queue | 200 with items list, total | P0 | routers/auto_apply.py:127-162 |
| S3-19 | Approve | Approve queued application | POST /api/auto-apply/queue/{item_id}/approve | 200, item status changed to "approved" | P0 | routers/auto_apply.py:164-189 |
| S3-20 | Approve | Item not found | POST /api/auto-apply/queue/{invalid_id}/approve | 404 "Queue item not found." | P1 | routers/auto_apply.py:178 |
| S3-21 | Reject | Reject queued application | POST /api/auto-apply/queue/{item_id}/reject | 200, item status changed to "rejected" | P0 | routers/auto_apply.py:191-216 |
| S3-22 | Briefing | Morning briefing | GET /api/auto-apply/briefing | 200 with summary text | P1 | routers/auto_apply.py:218-231 |

### 3.4 Interview Prep

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S3-23 | Full Prep | Generate interview prep package | GET /api/interview/{application_id}/prep | 200 with company_brief, practice_questions, talking_points | P0 | routers/interview.py:55-77 |
| S3-24 | Company Brief | Get company research brief | GET /api/interview/{application_id}/company-brief | 200 with brief text | P0 | routers/interview.py:79-98 |
| S3-25 | Questions | Generate practice questions | GET /api/interview/{application_id}/questions | 200 with questions list (question + suggested_answer pairs) | P0 | routers/interview.py:100-138 |
| S3-26 | Debrief | Post-interview analysis | POST /api/interview/{application_id}/debrief with went_well, could_improve, overall_feeling | 200 with improvement suggestions | P0 | routers/interview.py:140-168 |
| S3-27 | Debrief | Max 30 questions_asked | POST /api/interview/{application_id}/debrief with >30 questions_asked | 422 validation error (max_length=30) | P1 | routers/interview.py:41 |

### 3.5 Email OAuth

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S3-28 | Gmail Auth | Get OAuth redirect URL | GET /api/email/auth/gmail | 200 with redirect_url | P0 | routers/email_oauth.py:72-83 |
| S3-29 | Gmail Callback | Handle OAuth callback | GET /api/email/auth/gmail/callback with code and state | 200 with status="connected" | P0 | routers/email_oauth.py:85-106 |
| S3-30 | Gmail Callback | Missing authorization code | GET /api/email/auth/gmail/callback without code | 400 "Missing authorization code." | P1 | routers/email_oauth.py:98 |
| S3-31 | Auth Status | Check email connection status | GET /api/email/auth/status | 200 with connected=true/false, provider, email | P0 | routers/email_oauth.py:108-131 |
| S3-32 | Disconnect | Disconnect Gmail | DELETE /api/email/auth/gmail | 200 "Gmail disconnected." | P0 | routers/email_oauth.py:133-155 |
| S3-33 | Compose | Compose application email | POST /api/email/compose with to, subject, tone | 200 with subject, body, to, ready_to_send=false | P0 | routers/email_oauth.py:157-184 |
| S3-34 | Inbox | Check inbox for replies | GET /api/email/inbox | 200 with messages list (possibly empty), total | P1 | routers/email_oauth.py:186-199 |

### 3.6 Contextual AI Chat

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S3-35 | Chat | Send free-form message | POST /api/chat with message | 200 with agent response text | P0 | routers/chat.py:33-44 |
| S3-36 | Chat | Message max length 5000 | POST /api/chat with message >5000 chars | 422 validation error | P1 | schemas.py:88 |
| S3-37 | Chat | Rate limit 15/minute | 16 chat messages in 1 minute | 429 on 16th request | P2 | routers/chat.py:34 |
| S3-38 | Chat Reset | Clear conversation history | DELETE /api/chat/reset | 204 No Content, subsequent chat starts fresh | P0 | routers/chat.py:46-51 |
| S3-39 | Resume Parse | Parse PDF resume via Claude | POST /api/parse-resume with PDF file (<5 MB) | 200 with name, email, skills, experience_level, desired_roles, etc. | P0 | routers/chat.py:53-119 |
| S3-40 | Resume Parse | File too large (>5 MB) | POST /api/parse-resume with 6 MB file | 400 "File too large (max 5 MB)." | P1 | routers/chat.py:78-79 |
| S3-41 | Resume Parse | Unsupported file type | POST /api/parse-resume with .xlsx file | 400 "Unsupported file type. Allowed: application/pdf, text/plain, text/csv, text/markdown" | P1 | routers/chat.py:64-68 |

---

## Sprint 4: Intelligence & Growth

### 4.1 Outcome Learning

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S4-01 | Outcome Learning | Get variant correlation data | GET /api/insights/outcome-learning | 200 with correlations, winning_patterns, analysis | P0 | routers/insights.py:39-56 |
| S4-02 | Rejection Patterns | Analyse rejection patterns | GET /api/insights/rejection-patterns | 200 with patterns list, common_reasons | P0 | routers/insights.py:58-75 |
| S4-03 | Restrategize | Get actionable improvement advice | GET /api/insights/restrategize | 200 with strategy text | P0 | routers/insights.py:77-92 |
| S4-04 | Weekly Report | Generate weekly advisor report | GET /api/insights/weekly-report | 200 with report covering apps, rates, interviews, market, actions | P0 | routers/insights.py:94-112 |
| S4-05 | Weekly Report | Rate limit 3/minute | GET /api/insights/weekly-report 4 times in 1 minute | 429 on 4th request | P2 | routers/insights.py:95 |

### 4.2 Applications & Analytics

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S4-06 | Track App | Log new application | POST /api/applications with job_id, notes | 201 with agent confirmation | P0 | routers/applications.py:25-47 |
| S4-07 | Update App | Update application status | PUT /api/applications/{application_id} with new_status, feedback | 200 with agent response | P0 | routers/applications.py:49-66 |
| S4-08 | Update App | Valid ApplicationStatus values only | PUT /api/applications/{id} with new_status="invalid" | 422 validation error | P1 | schemas.py:82 |
| S4-09 | Analytics | Get application metrics and insights | GET /api/analytics | 200 with response rates, interview conversions, career insights | P0 | routers/applications.py:68-79 |
| S4-10 | Feedback | Get employer feedback analysis | GET /api/feedback | 200 with pattern analysis | P1 | routers/applications.py:81-92 |

### 4.3 Market Intelligence

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S4-11 | Market Insights | Get market report for region/industry | POST /api/market-insights with region, industry | 200 with salary ranges, in-demand skills, top employers | P0 | routers/jobs.py:412-427 |
| S4-12 | Application Tips | Get culturally-aware tips | POST /api/application-tips with region | 200 with cultural tips, CV norms, interview etiquette | P1 | routers/jobs.py:429-444 |

### 4.4 Account Lifecycle

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S4-13 | Export Data | Export all user data as JSON | GET /api/account/export | 200 with profile, applications, documents, career_dreams | P0 | routers/account.py:35-101 |
| S4-14 | Export Data | No user data found | GET /api/account/export for user with no DB record | 200 with message="No user data found." | P1 | routers/account.py:57 |
| S4-15 | Delete Account | Cascading delete of all user data | DELETE /api/account/ | 200 with deleted=true | P0 | routers/account.py:105-128 |
| S4-16 | Delete Account | No data to delete | DELETE /api/account/ for nonexistent user | 200 with deleted=false, "No user data found." | P1 | routers/account.py:120 |
| S4-17 | Delete Account | Rate limit 1/minute | DELETE /api/account/ 2 times in 1 minute | 429 on 2nd request | P2 | routers/account.py:107 |

### 4.5 Dashboard (Structured JSON)

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S4-18 | Summary | Get dashboard summary metrics | GET /api/dashboard/summary | 200 with total_applications, response_rate, interview_rate, offer_rate, by_status, cached_jobs | P0 | routers/dashboard.py:91-111 |
| S4-19 | Applications | Get dashboard applications list | GET /api/dashboard/applications | 200 with applications list including job details, total | P0 | routers/dashboard.py:113-149 |
| S4-20 | Activity | Get activity timeline | GET /api/dashboard/activity | 200 with activity events (max 50), sorted by timestamp desc | P0 | routers/dashboard.py:151-182 |
| S4-21 | Skills | Get skills gap analysis | GET /api/dashboard/skills | 200 with user_skills, in_demand_skills, matching_skills, gap_skills (max 15), match_pct | P0 | routers/dashboard.py:184-215 |

### 4.6 Kanban Board

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S4-22 | Board | Get full Kanban board | GET /api/kanban/board | 200 with 7 columns (draft, submitted, under_review, interview_scheduled, offer_received, rejected, withdrawn), total_cards | P0 | routers/kanban.py:75-116 |
| S4-23 | Move Card | Move card to new column | PUT /api/kanban/cards/{card_id}/move with new_status | 200 with old_status, new_status, message | P0 | routers/kanban.py:118-150 |
| S4-24 | Move Card | Card not found | PUT /api/kanban/cards/{invalid_id}/move | 404 "Application not found." | P1 | routers/kanban.py:133 |
| S4-25 | Card Detail | Get single Kanban card | GET /api/kanban/cards/{card_id} | 200 with card details including match_score, source_url | P0 | routers/kanban.py:152-178 |

### 4.7 Salary Negotiation

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S4-26 | Negotiate | Salary negotiation with leverage points | POST /api/salary/negotiate with current_offer, leverage_points=["5 years experience"] | 200 with counter-offer strategy referencing leverage | P0 | routers/salary.py:79-103 |
| S4-27 | Negotiate | Current offer must be >= 0 | POST /api/salary/negotiate with current_offer=-1 | 422 validation error (ge=0) | P1 | routers/salary.py:34 |

---

## Sprint 5: Backlog

### 5.1 Offers

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S5-01 | Add Offer | Create new job offer | POST /api/offers/ with company, role, base_salary | 201 with offer details, status="pending" | P0 | routers/offers.py:61-117 |
| S5-02 | Add Offer | Base salary >= 0 | POST /api/offers/ with base_salary=-1 | 422 validation error (ge=0) | P1 | routers/offers.py:23 |
| S5-03 | Add Offer | Deadline date format | POST /api/offers/ with deadline="2026-06-15" | Offer created with deadline stored | P1 | routers/offers.py:89-95 |
| S5-04 | Add Offer | Invalid deadline ignored | POST /api/offers/ with deadline="not-a-date" | Offer created, deadline is null (ValueError caught) | P2 | routers/offers.py:94 |
| S5-05 | List Offers | List all user offers | GET /api/offers/ | 200 with offers list sorted by created_at desc, total | P0 | routers/offers.py:119-155 |
| S5-06 | Compare Offers | Side-by-side comparison | GET /api/offers/compare | 200 with comparison analysis text | P0 | routers/offers.py:159-202 |
| S5-07 | Compare Offers | No offers to compare | GET /api/offers/compare with empty offers | 200 "No offers to compare." | P1 | routers/offers.py:179 |

### 5.2 Employer Portal

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| S5-08 | Waitlist | Join employer waitlist | POST /api/employer/waitlist with email, company_name | 201 with message and position | P0 | routers/employer.py:14-45 |
| S5-09 | Waitlist | Duplicate email returns existing | POST /api/employer/waitlist with already-registered email | 200 with "You're already on the waitlist!" | P1 | routers/employer.py:33 |
| S5-10 | Waitlist | Rate limit 5/hour | 6 waitlist signups in 1 hour | 429 on 6th request | P2 | routers/employer.py:19 |

---

## Cross-Cutting Concerns

### CC.1 Security & Middleware

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| CC-01 | Security Headers | All responses include security headers | Any API request | X-Frame-Options=DENY, X-Content-Type-Options=nosniff, Referrer-Policy=strict-origin-when-cross-origin, CSP present | P0 | api.py:139-161 |
| CC-02 | HSTS | HSTS header on HTTPS | Request over HTTPS (or X-Forwarded-Proto=https with TRUST_PROXY=true) | Strict-Transport-Security: max-age=31536000; includeSubDomains | P1 | api.py:158-159 |
| CC-03 | Request ID | X-Request-ID propagated | Send request with X-Request-ID header | Same value returned in response; auto-generated if absent | P1 | api.py:142,145 |
| CC-04 | CORS | Only allowed origins accepted | Request from unlisted origin | CORS headers not present in response | P1 | api.py:117-136 |
| CC-05 | Global Error | Unhandled exceptions return 500 | Trigger internal error | 500 {"detail": "Internal server error."} (no stack trace leaked) | P0 | api.py:112-114 |
| CC-06 | Rate Limit | 429 format consistent | Exceed any rate limit | 429 with {"detail": "Rate limit exceeded. Try again later."} | P1 | api.py:107-108 |
| CC-07 | Prod Auth | AUTH_ENABLED must be true in production | Set ENV=production, AUTH_ENABLED=false | SystemExit with fatal message | P0 | config/settings.py:198-204 |
| CC-08 | Docs Hidden | Swagger/ReDoc hidden when AUTH_ENABLED=true | Set AUTH_ENABLED=true, visit /docs | 404 (docs_url is None) | P1 | api.py:81-82 |

### CC.2 Privacy Pipeline

| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |
|---|---|---|---|---|---|---|
| CC-09 | PII Stripping | Protected attributes stripped before LLM | Inspect agent system prompt during chat | No gender, age, ethnicity, religion, nationality fields | P0 | config/settings.py:192, agent.py:64-66 |
| CC-10 | Sanitisation | Only safe fields sent to LLM | Check sanitised profile dict | Contains skills, location, experience_level; no email, phone, name | P0 | agent.py:64-66 |
| CC-11 | Encryption | AES-256-GCM encryption at rest | Store and retrieve encrypted PII | Data encrypted with PBKDF2 derived key, 390k iterations, 12-byte nonce | P1 | src/privacy.py:39-60 |
