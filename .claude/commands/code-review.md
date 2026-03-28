Review uncommitted changes for security issues and code quality. This is the required review step before committing.

The pre-commit gate will block commits until this review completes. After review, the commit will be allowed.

## Intent Contract

Before invoking any agent, construct this block and pass it as context:

```
INTENT_CONTRACT:
  INTENT: "[User's original request verbatim]"
  SCOPE: "[Files/areas to examine]"
  SUCCESS_CRITERIA: "[What done looks like]"
  INTENT_HASH: "[First 8 chars of SHA256(INTENT|SCOPE|SUCCESS_CRITERIA)]"
```

Every agent invocation MUST include this block. If an agent's output does not echo back the INTENT_HASH, its results are considered unverified.

## Step 1: Get Changed Files

```bash
git diff --name-only HEAD
```

If no changes, report "Nothing to review" and exit.

## Step 2: Launch Review Agents (in parallel)

Launch all three agents on the changed files:

| Agent | Focus |
|-------|-------|
| `code-quality-reviewer` | Code patterns, complexity, maintainability, naming |
| `security-reviewer` | Vulnerabilities, injection, credential exposure, input validation |
| `deep-reviewer` | Behavioral integrity, runtime correctness, configuration validity, dependency quality, user-facing text, regression and scalability risks |

## Step 3: Collect and Report Findings

For each issue found:
- **Severity**: CRITICAL, HIGH, MEDIUM, LOW
- **File**: path and line number
- **Issue**: what's wrong
- **Fix**: how to fix it

## Step 4: Verdict

- If CRITICAL issues found: list required fixes, do NOT mark as reviewed
- If HIGH issues found (no CRITICAL): strongly recommend fixes, mark as reviewed with warnings
- If only MEDIUM/LOW: approve with suggestions, mark as reviewed

## Step 5: Update Review Marker

After review completes (with no CRITICAL findings), write the review marker so the pre-commit gate knows these files have been reviewed:

```bash
echo '{"files": [<list of reviewed files>], "timestamp": "<ISO timestamp>", "verdict": "<APPROVED|APPROVED_WITH_WARNINGS>"}' > .claude/.last-review
```

This marker is checked by the pre-commit gate. If new files are staged after review, the gate will require re-review.

## Step 6: Recommend Next Step

After the review, always recommend the single best next action:

1. **CRITICAL fixes** — if any CRITICAL findings, recommend the specific fix with file:line
2. **HIGH fixes** — if HIGH findings with clear fixes, recommend `/build-fix` or manual fix
3. **Test coverage** — if reviewed code lacks tests, recommend writing tests for the specific functions
4. **Security hardening** — if security findings exist, recommend `/audit-security` for a deeper pass
5. **Ready to commit** — if review is clean, recommend committing with a suggested commit message
6. **Ready for PR** — if already committed, recommend `/pre-pr`

Format: **Next step:** one sentence with the specific command or action to take.
