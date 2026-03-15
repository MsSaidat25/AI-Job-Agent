Show the developer what workflows are available.

## Available Workflows

### Daily Development
- `/status` — Run all checks and show a project dashboard
- `/next` — Figure out what to work on next
- `/done` — Verify the current task is complete before moving on

### Verification
- `/verify-all` — Run lint, type check, tests, then launch all reviewers
- `/audit-spec` — Validate implementation against a spec/PRD
- `/audit-wiring` — Find dead or unwired features
- `/audit-security` — Run a security audit

### Release
- `/pre-pr` — Run the complete pre-PR checklist
- `/run-uat` — Execute UAT scenarios

### Generation
- `/generate-prd` — Generate a PRD from the current codebase
- `/generate-uat` — Generate UAT scenarios and checklists
- `/optimize-claude-md` — Slim down an oversized CLAUDE.md

## Quick Start
Run `/status` to see where things stand, then `/next` to pick up work.
