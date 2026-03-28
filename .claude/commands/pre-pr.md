Prepare a pull request. Quality checks (lint, tests, code review, security) already ran at commit time via the pre-commit gate. This command handles PR-specific preparation.

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

## Step 1: Verify Commit State

1. Check that all changes are committed (no uncommitted changes)
2. Check that the branch is pushed to remote
3. If there are uncommitted changes, tell the user to commit first (the pre-commit gate will handle quality checks)

## Step 2: Review the Full PR Diff

1. Get the base branch: `git rev-parse --abbrev-ref HEAD@{upstream} 2>/dev/null || echo main`
2. Get the full diff: `git diff <base-branch>...HEAD`
3. Get all commits in this branch: `git log <base-branch>..HEAD --oneline`
4. Review the full diff for:
   - Coherence: do all changes serve the same purpose?
   - Completeness: are there any half-finished features?
   - Any `.env` files, secrets, or debug code that slipped through

## Step 3: Generate PR Description

Based on the diff and commit history, generate:

```
## Summary
<1-3 bullet points describing what changed and why>

## Changes
<grouped list of changes by area>

## Test plan
<bulleted checklist of what to test>
```

## Step 4: Create PR

Use `gh pr create` with the generated title and description.
If the user hasn't pushed yet, push first with `git push -u origin <branch>`.

## Output

- PR URL
- Summary of what was included
- Any warnings (large diff, many files, etc.)
