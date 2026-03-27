Figure out what the developer should work on next.

## Steps

1. Check git log for recent commits to understand current progress
2. Look for TODO/FIXME/HACK comments in the codebase
3. Check if there are failing tests: `pytest`
4. Check if there are lint errors: `ruff check .`
5. Check if docs/uat/UAT_CHECKLIST.csv exists and has unchecked items
6. Look for open issues or PRs if this is a GitHub repo

## Priority Order
1. Failing tests or build errors (fix first)
2. Security issues (from recent audit or TODO comments)
3. Unchecked UAT scenarios
4. TODO/FIXME items in code
5. New feature work

## Output
Recommend the single most important thing to work on next, with a clear action.
