Review uncommitted changes for security issues and code quality.

## Step 1: Get Changed Files

```bash
git diff --name-only HEAD
```

## Step 2: Review Each File

For each changed file, check:

**Security (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- SQL injection vulnerabilities
- XSS vulnerabilities
- Missing input validation
- Path traversal risks

**Code Quality (HIGH):**
- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling
- console.log / print statements left in
- TODO/FIXME comments without tracking

**Best Practices (MEDIUM):**
- Missing tests for new code
- Mutation of shared state (use immutable patterns)
- Missing accessibility attributes (a11y)

**Code Style (LOW):**
- Naming convention violations
- Minor formatting inconsistencies
- Missing documentation comments

## Step 3: Generate Report

For each issue found:
- **Severity**: CRITICAL, HIGH, MEDIUM, LOW
- **File**: path and line number
- **Issue**: what's wrong
- **Fix**: how to fix it
## Step 4: Verdict

- If CRITICAL issues found → block commit, list required fixes
- If HIGH issues found (no CRITICAL) → strongly recommend fixes before commit
- If only MEDIUM/LOW → approve with suggestions
- Never approve code with security vulnerabilities
