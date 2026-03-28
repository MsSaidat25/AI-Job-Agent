Generate comprehensive UAT (User Acceptance Test) scenarios by analyzing the actual codebase, not guessing.

## Phase 1: Deep Code Analysis

Read the codebase systematically to build a complete feature inventory:

### 1.1 Route/Endpoint Discovery
- Read ALL route files (API routes, page routes, middleware)
- For each route: extract HTTP method, path, parameters, request body schema, response schema
- Note which routes require authentication and which roles can access them

### 1.2 Business Logic Extraction
- Read service/logic files (not just routes, the actual business logic)
- For each function that transforms data: extract the input, the rule, and the expected output
- Examples: "if order total > $100, apply 10% discount", "if user.role !== 'admin', return 403"
- Record these as testable assertions with computed expected values

### 1.3 UI Page Inventory (frontend projects)
- Read all page/view components
- For each page: list all interactive elements (forms, buttons, dropdowns, modals, tabs)
- Note form validation rules (required fields, min/max, regex patterns)
- Note conditional rendering (what appears/disappears based on state)

### 1.4 Data Flow Mapping
- Trace CRUD lifecycles: where is data created, read, updated, deleted?
- Map cross-page dependencies: "creating X on page A should show X on page B"
- Identify cascade effects: "deleting user should delete their posts"

### 1.5 Integration Points
- External API calls (payment, email, auth providers)
- File uploads/downloads
- WebSocket/real-time features
- Background jobs/queues

## Phase 2: Scenario Generation

For EVERY feature discovered in Phase 1, generate scenarios in these categories:

### Category A: Happy Path
- Standard usage with valid data
- Include specific test data values and computed expected results
- Example: "Submit order with 3 items totaling $150 -> expect 10% discount applied, total $135"

### Category B: Business Logic Verification
- Test every conditional branch found in Phase 1.2
- Include boundary values (exactly at threshold, one above, one below)
- Example: "Order total $99.99 -> no discount; $100.00 -> 10% discount; $100.01 -> 10% discount"

### Category C: Data Flow / Multi-Step Workflows
- CRUD lifecycle: create -> verify exists -> update -> verify changed -> delete -> verify gone
- Cross-page: create on page A -> navigate to page B -> verify appears
- Concurrent: two users modifying same resource

### Category D: Validation & Error Handling
- Every form field: empty, too short, too long, special characters, SQL injection attempt, XSS attempt
- API: missing required fields, wrong types, invalid values
- Auth: unauthenticated access, wrong role, expired token

### Category E: Edge Cases
- Empty states (no data, first-time user)
- Maximum load (list with 1000 items, very long text input)
- Rapid actions (double-click submit, back button during save)
- Network failure (what happens if API call fails mid-operation?)

### Category F: Permissions & Roles
- For each role: what can they access, what is denied?
- Role escalation: can a regular user access admin endpoints?
- Test every route/page against each role

## Phase 3: Prioritization

- **P0 (Critical)**: Authentication, core CRUD, data integrity, payment flows, security boundaries
- **P1 (Important)**: Validation, permissions, error handling, search/filter, export
- **P2 (Standard)**: UI polish, empty states, loading states, edge cases
- **P3 (Low)**: Cosmetic issues, minor UX improvements

Target: Generate scenarios proportional to the codebase size. A typical app should have:
- 1-2 scenarios per API endpoint
- 1-2 scenarios per UI page
- 3-5 scenarios per business logic rule
- At minimum: 10 P0, 20 P1, 15 P2, 5 P3

## Output

Generate three files:

### docs/uat/UAT_TEMPLATE.md
Full scenario document with columns:
| ID | Feature | Scenario | Steps | Expected Result | Priority | Source |

The **Source** column references the file and line where the logic was found (e.g., `src/services/order.js:45`).

### docs/uat/UAT_CHECKLIST.csv
CSV for tracking:
ID,Feature,Scenario,Priority,Status,Tester,Date,Notes

### docs/uat/BUSINESS_RULES.md
Extracted business rules with test values:
```
## Rule: [name]
- Source: [file:line]
- Logic: [description]
- Test cases:
  | Input | Expected Output | Boundary? |
```

Do NOT modify any code. This is a documentation-only task.
