Run the complete pre-PR checklist before creating a pull request.

1. Run lint: `ruff check .`
2. Run type check: `pyright`
3. Run tests: `pytest`
4. Check for uncommitted changes
5. Launch code-quality-reviewer agent on the PR diff
6. Launch security-reviewer agent on the PR diff
7. Check that no `.env` files or secrets are staged

If all checks pass, output:
- Summary of changes (files changed, lines added/removed)
- Suggested PR title and description
- Any warnings (non-blocking issues)

If any check fails, output:
- Which checks failed
- How to fix each failure
- Do NOT proceed with PR creation
