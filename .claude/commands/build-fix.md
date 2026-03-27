Incrementally fix build, lint, and type errors with minimal, safe changes.

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
