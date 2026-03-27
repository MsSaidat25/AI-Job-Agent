Enforce test-driven development: write failing tests FIRST, then implement.

## TDD Cycle

```
RED → GREEN → REFACTOR → REPEAT
```

1. **RED** — Write a failing test (because the code doesn't exist yet)
2. **GREEN** — Write the minimum code to make the test pass
3. **REFACTOR** — Improve the code while keeping tests green
4. **REPEAT** — Next scenario

## Process

1. Ask the user what feature to implement
2. Launch the `tdd-guide` agent
3. Define types/interfaces first
4. Write failing tests covering: happy path, edge cases, error cases
5. Run `pytest` — verify tests FAIL for the right reason
6. Implement minimal code to pass
7. Run `pytest` — verify tests PASS
8. Refactor if needed, keeping tests green
9. Check coverage — target 80%+ minimum

## Example

```
User: /tdd I need a function to validate email addresses

Step 1 — SCAFFOLD:
  Create types/interfaces for input and output

Step 2 — RED (write failing tests):
  - "should accept valid email: user@example.com"
  - "should reject email without @"
  - "should reject email without domain"
  - "should reject empty string"
  - "should handle unicode characters"

Step 3 — Run tests → all FAIL (expected, no implementation yet)

Step 4 — GREEN (implement minimal code):
  Write just enough to pass all tests

Step 5 — Run tests → all PASS

Step 6 — REFACTOR:
  Extract constants, improve naming, add JSDoc

Step 7 — Run tests → still PASS

Step 8 — Check coverage → 100%
```

## Rules

- NEVER write implementation before tests
- NEVER skip running tests after changes
- Each test should test ONE behavior
- Use descriptive names: "should return 404 when user not found"
- Test behavior, not implementation details
- Don't mock what you're testing

## Coverage Targets

- 80% minimum for all code
- 100% required for: financial calculations, auth logic, security-critical code

## Test Types to Include

- **Unit**: happy path, edge cases (null, empty, max), error conditions, boundary values
- **Integration**: API endpoints, database operations, auth flows
- **E2E**: use `/e2e` command for full user journey tests

## After TDD

- `/build-fix` — if build errors come up
- `/code-review` — review the implementation
- `/done` — verify the task is complete
