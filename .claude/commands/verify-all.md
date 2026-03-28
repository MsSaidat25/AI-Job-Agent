Run the full verification chain on the current changes.

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

1. Run lint: `ruff check .`
2. Run type check: `pyright`
3. Run tests: `pytest`
4. Launch the code-quality-reviewer agent on all changed files (use `git diff --name-only`)
5. Launch the security-reviewer agent on all changed files
6. Launch the production-readiness agent

Summarize all findings grouped by severity (critical, high, medium, low).
If any critical issues found, list them prominently at the top.

## Recommend Next Step

After the summary, always recommend the single best next action based on findings:
- **CRITICAL findings** → recommend the specific fix
- **HIGH findings** → recommend addressing before proceeding
- **No issues** → recommend `/pre-pr`
- **MEDIUM/LOW only** → recommend committing, note optional improvements

Format: **Next step:** one sentence with the specific command or action to take.
