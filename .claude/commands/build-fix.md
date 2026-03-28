Incrementally fix build, lint, and type errors with minimal, safe changes.

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

## Step 1: Detect and Run Build

Run the build and capture errors:

```
docker build -t app .
ruff check .
pyright
```

## Step 2: Parse and Group Errors

1. Group errors by file path
2. Sort by dependency order (fix imports/types before logic errors)
3. Count total errors for progress tracking

## Step 3: Fix Loop (One Error at a Time)

For each error:
1. Read the file to see error context
2. Diagnose the root cause (missing import, wrong type, syntax error)
3. Apply the smallest possible fix
4. Re-run all three commands (build, lint, type check) to confirm the error is gone and no new errors were introduced
5. Move to the next error

## Step 4: Guardrails

Stop and ask the user if:
- A fix introduces more errors than it resolves
- The same error persists after 3 attempts
- The fix requires architectural changes (not just a build fix)
- Build errors stem from missing dependencies

## Step 5: Summary

Show results:
- Errors fixed (with file paths)
- Errors remaining (if any)
- Suggested next steps for unresolved issues

Fix one error at a time. Prefer minimal diffs over refactoring.

## Step 6: Recommend Next Step

After the fix summary, always recommend the single best next action. Evaluate in this order:

1. **Remaining errors** — if any build/lint/type errors remain, recommend the specific fix
2. **Test gaps** — if the fix touched untested code, recommend writing tests
3. **Security review** — if the fix touched auth, input handling, or API routes, recommend `/audit-security`
4. **Code review** — if significant logic changed, recommend `/code-review`
5. **UAT impact** — if the fix affects user-facing behavior, flag which UAT scenarios need re-verification
6. **Performance** — if the fix introduced new queries, loops, or async patterns, flag for perf review
7. **All clean** — if everything passes, recommend `/pre-pr` or the next feature to build

Format: **Next step:** one sentence with the specific command or action to take.
