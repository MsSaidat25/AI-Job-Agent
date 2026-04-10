# AI Job Agent -- Project Roadmap

## Current State (v1.0)
- Job seeker mobile app (React Native + Expo) -- Stone & Copper theme
- FastAPI backend with session-based auth
- Job search, resume/cover letter generation, application tracking (Kanban), chat agent
- Employer waitlist signup only
- No admin portal

---

## Employer Portal

### Phase 1: Coming Soon + Waitlist (exists in web frontend, needs mobile)
- Mobile screen: Employer landing page with value props
- Mobile screen: Waitlist signup form (email, company name, company size)
- Pricing tiers display (Free / Pro / Enterprise)

### Phase 2: Employer Dashboard
- Employer authentication (separate from job seeker auth)
- Company profile management (name, logo, description, industry, size)
- Job posting CRUD (title, description, requirements, salary range, location, remote flag)
- Candidate matching -- browse AI-matched profiles (anonymized, no PII until mutual interest)
- Application pipeline view -- see who applied to each posting
- ATS score integration -- score candidates against job requirements
- Screening tools -- bias-free skill-based ranking
- Interview scheduling integration
- Offer management workflow
- Employer analytics (views, applications, time-to-hire, diversity metrics)
- Team member management (invite colleagues, role-based access)
- Billing / Stripe subscription management (Free, Pro $99/mo, Enterprise $499/mo)
- API keys for ATS/HRIS integrations (Workday, Greenhouse, Lever)

### Phase 3: Employer Mobile Screens
- Employer tab or separate app entry point
- Job posting creation from mobile
- Push notifications for new applicants
- Quick candidate review (swipe accept/reject)

---

## Admin Portal

### Phase 1: Core Admin
- Admin authentication with role-based access (super_admin, support, moderator)
- Admin dashboard: system health, user counts, active sessions, API usage
- User management: list/search job seekers, view profiles, disable/enable accounts
- Employer management: list/search employers, approve/reject waitlist, manage subscriptions
- Waitlist management: view queue, bulk approve, export CSV

### Phase 2: Operations
- Application moderation: flag/review suspicious activity
- Content moderation: review AI-generated resumes/cover letters for quality
- Job posting moderation: approve/reject employer job posts
- Audit log viewer: track all admin actions with timestamps
- System configuration: toggle features, update rate limits, manage CORS origins
- Email template management (welcome, waitlist confirmation, status updates)
- Database health: migration status, table sizes, slow queries

### Phase 3: Analytics & Reporting
- Platform analytics: DAU/MAU, retention, funnel conversion
- Revenue dashboard: MRR, churn, subscription breakdown
- Job market analytics: trending roles, salary data, regional demand
- AI usage metrics: token consumption, model costs, response latency
- Support ticket system: user-reported issues, resolution tracking
- Export reports (CSV, PDF) for stakeholders

### Phase 4: Admin Mobile Screens
- Lightweight admin dashboard on mobile
- Push alerts for system issues, waitlist surges, flagged content
- Quick user/employer lookup and management
