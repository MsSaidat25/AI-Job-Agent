---
name: git-workflow
description: Git branching, commits, PR workflow, and conflict resolution patterns
---

## Branching Strategy

- `main` - production-ready code, never commit directly
- `feat/<name>` - new features, branch from main
- `fix/<name>` - bug fixes, branch from main
- `chore/<name>` - maintenance, config changes, dependency updates

Always create a feature branch before starting work:
```bash
git checkout -b feat/my-feature main
```

## Commit Conventions

Use conventional commit messages:

| Prefix | When |
|--------|------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `test:` | Adding or updating tests |
| `refactor:` | Code change that neither fixes nor adds |
| `chore:` | Build process, deps, config |

Rules:
- Keep subject under 72 characters
- Use imperative mood ("add feature" not "added feature")
- Body explains WHY, not WHAT (the diff shows what)
- Reference issue numbers: `fix: handle null user (#123)`

## Pull Request Workflow

1. Push feature branch: `git push -u origin feat/my-feature`
2. Create PR with clear title and description
3. PR description should include: what changed, why, how to test
4. Request review, address feedback
5. Squash merge to main (keeps history clean)
6. Delete the feature branch after merge

## Conflict Resolution

When conflicts occur:
1. `git fetch origin main`
2. `git rebase origin/main` (preferred over merge)
3. Resolve conflicts file by file
4. `git add <resolved-files>`
5. `git rebase --continue`
6. Run tests after resolving: ensure nothing broke

If rebase gets messy: `git rebase --abort` and start over.

## Common Mistakes

- Never force-push to `main`
- Never commit `.env` files, credentials, or large binaries
- Never rebase shared branches (`main`, `develop`). Only rebase your own feature branches
- Update feature branches with `git rebase origin/main`, not `git merge main` (force-push your branch after)
- Always pull before pushing: `git pull --rebase` (pulls current branch's upstream)
