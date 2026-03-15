Run the full verification chain on the current changes.

1. Run lint: `ruff check .`
2. Run type check: `pyright`
3. Run tests: `pytest`
4. Launch the code-quality-reviewer agent on all changed files (use `git diff --name-only`)
5. Launch the security-reviewer agent on all changed files
6. Launch the production-readiness agent

Summarize all findings grouped by severity (critical, high, medium, low).
If any critical issues found, list them prominently at the top.
