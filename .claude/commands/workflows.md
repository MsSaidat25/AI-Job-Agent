Show the developer what workflows are available.

## Available Workflows

### Development
- `/plan` - Create an implementation plan before writing code
- `/tdd` - Write failing tests first, then implement (test-driven development)
- `/build-fix` - Fix build, lint, and type errors incrementally
- `/fix-loop` - Automated fix-review-regression loop until green
- `/build-ui` - Build frontend UI with AI-powered generation (Google Stitch + UI UX Pro Max)
- `/code-review` - Review changes for security and quality (required before commit)
- `/simplify` - Find duplicate code, long files, and extract shared utilities

### Daily
- `/help` - Not sure what to do? This guides you to the right workflow
- `/status` - Run all checks and show a project dashboard
- `/next` - Figure out what to work on next

### Verification
- `/verify-all` - Run lint, type check, tests, then launch all reviewers
- `/full-audit` - Run every audit and review agent in a single pass
- `/audit-spec` - Validate implementation against a spec/PRD
- `/audit-wiring` - Find dead or unwired features
- `/audit-security` - Run a security audit
- `/verify-intent` - Verify all agents comply with Intent Verification Protocol

### Strategy
- Use `product-strategist` agent - Research competitors, evaluate project maturity, recommend improvements

### Release
- `/pre-pr` - Prepare and create a pull request
- `/run-uat` - Execute UAT scenarios
- `/live-uat` - Run live UAT by interacting with the running application

### Generation
- `/generate-prd` - Generate a PRD from the current codebase
- `/generate-sdd` - Generate a Software Design Document from the codebase
- `/generate-uat` - Generate UAT scenarios and checklists
- `/optimize-claude-md` - Slim down an oversized CLAUDE.md

### Session
- `/save-session` - Save current work context for later resumption
- `/resume-session` - Load a saved session and continue where you left off

## Quality Gates (automatic)

These run automatically, you don't need to remember them:
- **On commit**: Pre-commit gate runs lint, tests, secrets check, and requires code review
- **On stop**: Code hygiene check runs automatically

## Quick Start
Run `/status` to see where things stand, then `/next` to pick up work.
