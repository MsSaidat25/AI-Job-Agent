Ask the developer: "What are you trying to do?" Then guide them to the right workflow.

## Decision Tree

Based on the developer's answer, recommend the appropriate workflow:

### "I want to start building a feature"
→ Run `/plan` to create an implementation plan first

### "I want to build frontend UI"
→ Run `/build-ui` to generate UI with AI-powered tools

### "I want to write tests first"
→ Run `/tdd` to follow test-driven development

### "I have build errors / lint errors / type errors"
→ Run `/build-fix` to fix them incrementally

### "I want to check if everything is working"
→ Run `/status` for a quick dashboard
→ Run `/verify-all` for a thorough check

### "My code is messy / I have duplicate code / files are too long"
→ Run `/simplify` to find duplicates, split long files, and extract shared utilities

### "I want to review my code before committing"
→ Run `/code-review` for security + quality review

### "I'm ready to make a PR"
→ Run `/pre-pr` for the complete pre-PR checklist

### "I want to run UAT"
→ Run `/run-uat` for one-off or sandbox UAT runs using the checklist/template flow
→ Run `/live-uat` for UAT against live-like data or long-lived UAT environments

### "I want a full audit of the project"
→ Run `/full-audit` to run every review agent

### "I want to check security"
→ Run `/audit-security` for a focused security audit

### "I want to generate documentation"
→ `/generate-prd` for a Product Requirements Document
→ `/generate-sdd` for a Software Design Document
→ `/generate-uat` for UAT test scenarios

### "I don't know what to work on"
→ Run `/next` to figure out the highest-priority task

### "I think I'm done with this task"
→ Just commit. The pre-commit gate automatically runs lint, tests, and security checks.
→ If the gate blocks the commit, run `/build-fix` to resolve issues.

### "I want to save my progress and come back later"
→ Run `/save-session` to save context
→ Run `/resume-session` to pick up where you left off

### "I want to see all available workflows"
→ Run `/workflows` for the complete list

## All Commands Reference

**Daily:** `/workflows`, `/status`, `/next`
**Development:** `/plan`, `/tdd`, `/build-fix`, `/fix-loop`, `/build-ui`, `/code-review`, `/simplify`
**Verification:** `/verify-all`, `/full-audit`, `/audit-spec`, `/audit-wiring`, `/audit-security`, `/verify-intent`
**Release:** `/pre-pr`, `/run-uat`, `/live-uat`
**Generation:** `/generate-prd`, `/generate-sdd`, `/generate-uat`, `/optimize-claude-md`
**Session:** `/save-session`, `/resume-session`
