Show the developer what workflows are available.

## Available Workflows

### Development
- `/plan` — Create an implementation plan before writing code
- `/tdd` — Write failing tests first, then implement (test-driven development)
- `/build-fix` — Fix build, lint, and type errors incrementally
- `/code-review` — Review uncommitted changes for security and quality

### Daily
- `/status` — Run all checks and show a project dashboard
- `/next` — Figure out what to work on next
- `/done` — Verify the current task is complete before moving on

### Verification
- `/verify-all` — Run lint, type check, tests, then launch all reviewers
- `/full-audit` — Run every audit and review agent in a single pass
- `/audit-spec` — Validate implementation against a spec/PRD
- `/audit-wiring` — Find dead or unwired features
- `/audit-security` — Run a security audit

### Strategy
- Use `product-strategist` agent — Research competitors, evaluate project maturity, recommend improvements

### Release
- `/pre-pr` — Run the complete pre-PR checklist
- `/run-uat` — Execute UAT scenarios

### Generation
- `/generate-prd` — Generate a PRD from the current codebase
- `/generate-uat` — Generate UAT scenarios and checklists
- `/optimize-claude-md` — Slim down an oversized CLAUDE.md

### Session
- `/save-session` — Save current work context for later resumption
- `/resume-session` — Load a saved session and continue where you left off

## Quick Start
Run `/status` to see where things stand, then `/next` to pick up work.
