Run all validation checks and show a project dashboard.

## Steps

1. Run lint: `ruff check .`
2. Run type check: `pyright`
3. Run tests: `pytest`
4. Check git status for uncommitted changes
5. Check for any `.env` files accidentally tracked

## Output Format

```
AIJobAgent Status
──────────────────────────
Lint:       PASS / FAIL (N issues)
Types:      PASS / FAIL (N errors)
Tests:      PASS / FAIL (N passed, M failed)
Git:        clean / N uncommitted changes
Secrets:    clean / WARNING
──────────────────────────
```

If anything fails, suggest the next step to fix it.
