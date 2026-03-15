Verify that the current task is actually complete before moving on.

## Checklist

1. Run lint and confirm it passes: `ruff check .`
2. Run type check and confirm it passes: `pyright`
3. Run tests and confirm they pass: `pytest`
4. Check that no `.env` files or secrets are in the changes
5. Review the git diff to make sure only intended files changed
6. Verify the feature works as described (manual check or UAT scenario)

## Output

If everything passes:
```
Task complete. Ready to commit or move on.
```

If something fails, explain what needs to be fixed before the task can be considered done.
