Run every audit and review agent in a single pass. Use this when you want a comprehensive project health check.

## Intent Contract

Before invoking any agent, construct this block and pass it as context:

```
INTENT_CONTRACT:
  INTENT: "[User's original request - default: 'Run comprehensive project health check']"
  SCOPE: "[Full codebase - all source files, configs, and .claude/ infrastructure]"
  SUCCESS_CRITERIA: "[All review agents run, all findings grouped by severity, no agent skipped]"
  INTENT_HASH: "[First 8 chars of SHA256(INTENT|SCOPE|SUCCESS_CRITERIA)]"
```

Every agent invocation MUST include this block. If an agent's output does not echo back the INTENT_HASH in its PROOF_OF_INTENT, its results are considered unverified.

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

1. **code-quality-reviewer** - code patterns, duplication, naming
2. **security-reviewer** - vulnerabilities, secrets, unsafe operations
3. **production-readiness** - deployment readiness, error handling, health checks
4. **database-reviewer** - query performance, N+1, schema issues (skip if no database)

## Step 4: Structural Audits

1. **Wiring audit** - verify all API endpoints are connected between frontend and backend
2. **Spec audit** - if `docs/` contains a spec/PRD, validate implementation coverage

## Step 5: Claude Code Setup + Product Strategy

1. **harness-optimizer** - check if .claude/ setup follows best practices (includes consistency, accuracy, formatting checks)
2. **product-strategist** - research competitors via web search, evaluate project maturity, recommend improvements

## Step 5.5: Intent Verification Protocol Audit

1. **prompt-auditor** - audit all agent prompts for clarity, completeness, and protocol compliance
2. Verify every agent invoked in Steps 3-5 returned a PROOF_OF_INTENT block
3. Check all INTENT_RECEIVED hashes match the original INTENT_HASH
4. Flag any INTENT_MATCH: NO or PARTIAL results

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

INTENT VERIFICATION:
  Contract issued: YES/NO
  Agents verified: [X of Y returned PROOF_OF_INTENT]
  Intent matches: [X of Y returned INTENT_MATCH: YES]
  Drift detected: [list any agents where INTENT_RECEIVED didn't match]
  Gaps reported: [list any agents that reported coverage gaps]
```

Include total counts: X critical, Y high, Z medium, W low.
