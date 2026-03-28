Run a comprehensive live UAT by interacting with the running application in a real browser or via API calls.

This is NOT a code review or automated test run. You will physically navigate the app, click buttons, fill forms, test every feature, and verify outputs against ground truth.

## Step 1: Detect Testing Mode

Determine what kind of application this is by reading the project structure:

- **Has frontend** (Next.js, React, Vue, etc.) → Browser-based testing. Requires a browser automation tool.
- **API only** (FastAPI, Express, etc.) → Endpoint testing via curl, httpie, or API client MCP.
- **Full-stack** → Both browser AND API testing.

### Browser Testing Setup (frontend projects only)
Check which browser tool is available:
- `mcp__Claude_in_Chrome__*` tools (Claude in Chrome extension) — preferred
- Playwright MCP or similar browser automation MCP
- Any other browser MCP tool

If none are available, tell the user: "Install a browser automation tool (Claude in Chrome extension, Playwright MCP, etc.) to run live UI testing. Alternatively, I can test API endpoints only."

## Step 2: Gather Test Parameters

Ask the user these questions before starting. Skip questions that don't apply to the detected stack.

1. **App URL**: What URL should I test against? (e.g., `http://localhost:3000`, a staging URL)
2. **Login**: What account(s) should I use? (You will type passwords yourself)
3. **Multiple roles?**: Are there different user roles to test? (admin, user, viewer, etc.)
4. **Existing UAT document**: Check if `docs/uat/UAT_TEMPLATE.md` exists. If it does, ask: "I found your UAT scenarios. Should I test against these, or do a full exploratory pass?"
5. **Ground truth documents**: Do you have source documents that the app's outputs should be evaluated against? (e.g., a dataset the app should parse correctly, a document it should analyze accurately)
6. **Scope**: Test ALL pages/endpoints, or specific ones?
7. **Server logs**: How do I check server logs when errors occur? (e.g., terminal output, `docker logs`, cloud logging command)

## Step 3: Testing Rules

### Rule 1: Test Every Interactive Element
For every page or endpoint:
- Every button, link, tab, toggle, dropdown, filter
- Every form (fill, submit, check validation and error states)
- Every export/download (verify correct file format for the content type)
- Every AI/ML feature (verify output quality, not just that it runs)
- Every modal/dialog (open, interact, close)
- Every navigation path (sidebar, breadcrumbs, back button)

For API-only projects:
- Every endpoint (all HTTP methods)
- Every query parameter and request body variation
- Authentication and authorization on each endpoint
- Error responses (400, 401, 403, 404, 422, 500)
- Response schema validation

### Rule 2: Verify Output Quality
Do NOT just check if features respond. Verify the CONTENT:
- Compare outputs against ground truth documents (if provided)
- Compare against existing UAT scenarios in `docs/uat/UAT_TEMPLATE.md` (if they exist)
- Flag hallucinated data, missing findings, incorrect results
- If a feature says "0 results" for input that clearly has results, that is CRITICAL
- Check that outputs reference actual data, not generic boilerplate

### Rule 3: Fix Bugs in Parallel
When a bug is found:
- Log it immediately in the results file with severity (Critical / High / Medium / Low)
- If the bug is in the codebase and fixable: spawn a background agent to fix it while you continue testing
- Do NOT stop testing to fix bugs unless they completely block further testing — except when the 15+ bug quality gate in Rule 4 is met (then stop immediately, save state, list all bugs, and generate the resume prompt)
- Track fix status: Found, Fixing, Fixed, Wont Fix

### Rule 4: Quality Gate (Overrides Rule 3) + Screenshot and Evidence Strategy
- **Bugs 0-10**: Screenshots of failures AND key milestones (page loads, successful operations)
- **Bugs 11-15**: Screenshots on FAILURES only. Use text-based page reads for passes.
- **Bugs 15+**: STOP TESTING IMMEDIATELY (this overrides Rule 3). Save state, list all bugs found so far, and generate the resume prompt before continuing any further work.

### Rule 5: Save Progress Continuously
- **Every 3-4 pages or endpoints**: Write results to `docs/sessions/live-uat-YYYY-MM-DD.md`
- **Every bug**: Update the bug table immediately
- **At ~70% context usage**: Proactively save ALL results, generate a self-contained resume prompt, and tell the user where to find it

### Rule 6: Check Server Logs on Every Error
On any 500, timeout, or unexpected behavior:
- Run the log check command the user provided
- Include error details in the bug report
- Note the timestamp and endpoint

### Rule 7: Create Test Data When Needed
If a feature requires data that doesn't exist:
- Create it (add a record, upload a file, seed data)
- Don't skip testing because data is missing
- Document what test data you created so it can be cleaned up

### Rule 8: Quality Audit
Before marking any feature PASS, verify:
- Destructive actions use confirmation modals (not browser `confirm()`)
- Forms have validation and clear error messages
- Loading states are present (skeletons or spinners)
- Empty states have descriptions and call-to-action buttons
- Exports use the correct format for the content type (e.g., reports = PDF/DOCX, data = CSV/XLSX)

### Rule 9: Business Logic Verification
Before testing, read the source code for business rules. For each rule found:
- Test the exact boundary values (at threshold, one above, one below)
- Verify computed outputs match what the code should produce
- Example: if code says `if (total > 100) applyDiscount(0.1)`, test with total=99.99, 100.00, 100.01
- Log the source file and line for each business rule tested

### Rule 10: Data Flow / CRUD Lifecycle Testing
For every entity type in the app (users, orders, posts, etc.):
1. **Create** an item with valid data, verify it appears in listings
2. **Read** the item detail page/endpoint, verify all fields are correct
3. **Update** the item, verify changes persist after page reload
4. **Delete** the item, verify it disappears from all listings and related pages
5. Test cascade effects: deleting a parent should handle children correctly

### Rule 11: Regression Tracking
Check if a previous live-uat session exists (`docs/sessions/live-uat-*.md`):
- If yes, load the previous bug table and results
- After testing, compare: flag any previously-passing features that now fail as **REGRESSION**
- Flag any previously-fixed bugs that have returned as **REGRESSION: BUG RETURNED**
- Include a regression summary section in the results

## Step 4: Testing Workflow

### Phase 1: Pre-Flight
1. Verify the app URL is accessible
2. Get browser tab or API client ready
3. Login (let user type passwords)
4. Verify the app loads correctly

### Phase 2: Systematic Testing
**For frontend apps** — test page by page:
1. Navigate to page, verify it loads
2. Read page content, note what is displayed
3. Click every tab, verify content changes
4. Click every button, verify behavior
5. Test every form: fill, submit, verify
6. Test every filter/search, verify results
7. Test every export/download, verify format
8. Test every AI feature, verify output against ground truth
9. Log PASS or FAIL with what you observed

**For API-only apps** — test endpoint by endpoint:
1. Send request, verify response status and schema
2. Test with valid data (happy path)
3. Test with invalid data (validation errors)
4. Test without auth (should get 401)
5. Test with wrong role (should get 403)
6. Test edge cases (empty body, large payload, special characters)
7. Log PASS or FAIL with response details

### Phase 3: Business Logic Verification
1. Read source code for business rules (see Rule 9)
2. For each rule, test boundary values and computed expected outputs
3. If `docs/uat/BUSINESS_RULES.md` exists (from `/generate-uat`), use it as the test plan
4. Log each rule tested with: source file, input, expected output, actual output, PASS/FAIL

### Phase 4: Data Flow / CRUD Lifecycle
1. Identify all entity types from the database schema or API routes
2. For each entity: run the Create -> Read -> Update -> Delete cycle (see Rule 10)
3. Test cross-page visibility: create on page A, verify on page B
4. Test cascade deletes and referential integrity

### Phase 5: Cross-Cutting Concerns
- Role-based access: login as different roles, verify permissions
- AI/ML features: test with real data, verify accuracy
- Reports and exports: generate every type, verify content
- Settings and admin: test every configuration option

### Phase 6: Regression Check
1. Load previous live-uat results if they exist (see Rule 11)
2. Compare current results against previous pass/fail status
3. Flag any regressions prominently

### Phase 7: Server Health
- Check server logs for errors generated during testing
- Report any unhandled exceptions or warnings

## Step 5: Results Format

Write results to `docs/sessions/live-uat-YYYY-MM-DD.md`:

```
# Live UAT Results — [Date]

## Environment
- URL: [app url]
- Stack: [detected stack]
- Roles tested: [list]

## Page/Endpoint: [Name]
| # | Action | Result | Notes |
|---|--------|--------|-------|
| 1 | Page loads | PASS | Shows expected content |
| 2 | Submit form | FAIL | Bug #3: validation missing |

## Bugs Found
| # | Bug | Severity | Location | Status |
|---|-----|----------|----------|--------|
| 1 | Missing validation on email | Medium | /signup | Fixed |
| 2 | AI returns empty results | Critical | /analysis | Fixing |

## Output Quality (if applicable)
| Feature | Expected | Actual | Score |
|---------|----------|--------|-------|
| Data parsing | 26 items | 24 found | 8/10 |
| Report generation | Full report | Missing section 3 | 6/10 |

## Business Logic Verification
| # | Rule | Source | Input | Expected | Actual | Result |
|---|------|--------|-------|----------|--------|--------|
| 1 | Discount > $100 | src/order.js:45 | $150 | $135 | $135 | PASS |
| 2 | Admin-only endpoint | src/api/admin.js:12 | role=user | 403 | 200 | FAIL |

## Data Flow / CRUD Lifecycle
| Entity | Create | Read | Update | Delete | Cascade | Notes |
|--------|--------|------|--------|--------|---------|-------|
| User | PASS | PASS | PASS | FAIL | N/A | Bug #5 |
| Order | PASS | PASS | PASS | PASS | PASS | |

## Regressions (vs previous session)
| Feature | Previous | Current | Status |
|---------|----------|---------|--------|
| Login flow | PASS | PASS | Stable |
| Export PDF | PASS | FAIL | REGRESSION |

## Summary
- Total actions tested: X | PASS: X | FAIL: X
- Business rules tested: X | PASS: X | FAIL: X
- CRUD lifecycles tested: X | PASS: X | FAIL: X
- Regressions found: X
- Bugs: X (Critical: X, High: X, Medium: X, Low: X)
- Fixed during testing: X | Remaining: X
- Recommendation: Ship / Fix and retest / Needs rework
```

## Step 6: Session Resume Prompt

When saving a resume prompt (on pause, bug overflow, or context limit), write to `docs/sessions/live-uat-resume-YYYY-MM-DD.md`:

```
# Resume Live UAT — [Date] Session [N+1]

## Context
Read these files first:
1. docs/sessions/live-uat-YYYY-MM-DD.md — results so far
2. docs/uat/UAT_TEMPLATE.md — test scenarios (if exists)

## Tested So Far
[list pages/endpoints with PASS/FAIL counts]

## Remaining
[list untested pages/endpoints]

## Open Bugs
[full bug table with status]

## Test Data Created
[list of data created during testing, for cleanup]

## Login
User will re-enter passwords

## App URL
[url]

## Resume From
[exact page/endpoint and step number]
```

---

**Ready to start. Tell me the app URL, how to login, and whether you have ground truth documents to test against.**
