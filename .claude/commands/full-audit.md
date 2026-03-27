Run every audit and review agent in a single pass. Use this when you want a comprehensive project health check.

## Step 1: Build + Lint + Tests

1. Run lint: `ruff check .`
2. Run type check: `pyright`
3. Run tests: `pytest`

If any step fails, report the failures but continue with the remaining audits.

## Step 2: Code Review (changed files)

1. Get changed files: `git diff --name-only HEAD`
2. For each changed file, check for:
   - Hardcoded credentials, API keys, tokens
   - SQL injection, XSS, path traversal
   - Functions > 50 lines, files > 800 lines
   - Missing error handling, console.log left in
   - Missing tests for new code

## Step 3: Launch Review Agents

Run these agents in sequence on the full codebase:

1. **code-quality-reviewer** — code patterns, duplication, naming
2. **security-reviewer** — vulnerabilities, secrets, unsafe operations
3. **production-readiness** — deployment readiness, error handling, health checks
4. **database-reviewer** — query performance, N+1, schema issues (skip if no database)

## Step 4: Structural Audits

1. **Wiring audit** — verify all API endpoints are connected between frontend and backend
2. **Spec audit** — if `docs/` contains a spec/PRD, validate implementation coverage

## Step 5: Claude Code Setup + Product Strategy

1. **harness-optimizer** — check if .claude/ setup follows best practices (includes consistency, accuracy, formatting checks)
2. **product-strategist** — research competitors via web search, evaluate project maturity, recommend improvements

## Step 6: Summary Report

Compile all findings into a single report grouped by severity:

```
CRITICAL (must fix before merge):
  - [list]

HIGH (fix soon):
  - [list]

MEDIUM (improve when possible):
  - [list]

LOW (nice to have):
  - [list]

PASSED:
  - [list of checks that found no issues]
```

Include total counts: X critical, Y high, Z medium, W low.
