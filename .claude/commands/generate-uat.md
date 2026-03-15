Generate UAT (User Acceptance Test) scenarios for this project.

## Instructions

1. Read the codebase to identify all user-facing features:
   - API endpoints and their purposes
   - UI pages and forms
   - Authentication flows
   - Business logic and workflows

2. For each feature, create test scenarios covering:
   - Happy path (expected usage)
   - Edge cases (empty inputs, max values, special characters)
   - Error cases (invalid data, unauthorized access, network failures)
   - Integration points (features that depend on each other)

3. Prioritize scenarios:
   - P0: Critical path — app is broken if these fail (login, core CRUD, data integrity)
   - P1: Important — significant user impact (permissions, validation, error handling)
   - P2: Nice to have — minor features, cosmetic issues

## Output

Generate two files:

### docs/uat/UAT_TEMPLATE.md
Markdown table with columns:
| ID | Feature | Scenario | Steps | Expected Result | Priority |

### docs/uat/UAT_CHECKLIST.csv
CSV with columns:
ID,Feature,Scenario,Priority,Status,Tester,Date,Notes

Include at least 5 P0 scenarios, 10 P1 scenarios, and 5 P2 scenarios.
Do NOT modify any code — this is a documentation-only task.
