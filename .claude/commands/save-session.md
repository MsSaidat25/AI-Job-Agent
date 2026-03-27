Save the current session state so work can be resumed in a future conversation.

## Process

1. **Gather context** — Review what was discussed, built, and decided this session
2. **Create folder** — `mkdir -p docs/sessions` (or `~/.claude/sessions/`)
3. **Write session file** — `docs/sessions/YYYY-MM-DD-session.md`
4. **Show to user** — Display contents and ask for corrections

## Session File Format

```markdown
# Session: YYYY-MM-DD

**Project:** [project name]
**Topic:** [one-line summary]

---

## What We Are Building
[1-3 paragraphs with enough context for someone with zero memory of this session]

---

## What WORKED (with evidence)
- **[thing]** — confirmed by: [specific evidence like "tests pass", "200 response"]

---

## What Did NOT Work (and why)
- **[approach]** — failed because: [exact reason / error message]

---

## What Has NOT Been Tried Yet
- [approach worth exploring]

---

## Current State of Files

| File | Status | Notes |
|------|--------|-------|
| `path/file.ts` | ✅ Complete | [what it does] |
| `path/file.ts` | 🔄 In Progress | [what's left] |
| `path/file.ts` | 🗒️ Not Started | [planned] |

---

## Decisions Made
- **[decision]** — reason: [why]

---

## Blockers & Open Questions
- [blocker or unanswered question]

---

## Exact Next Step
[The single most important thing to do when resuming]
```

## Rules

- Write every section honestly — "Nothing yet" is better than skipping a section
- The "What Did NOT Work" section is the most critical — prevents retrying failed approaches
- Each session gets its own file — never append to previous sessions
- Wait for user confirmation before closing
