Analyze and optimize CLAUDE.md for this project.

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

## Instructions

1. Read the current CLAUDE.md and measure its size (line count).

2. The target is **under 150 lines**. CLAUDE.md should contain ONLY:
   - WHAT: One-line project description
   - HOW: Key commands (lint, test, build, dev)
   - RULES: Universal rules that apply everywhere (max 10-15 rules)
   - PITFALLS: Known gotchas specific to this project (max 5)

3. Identify content that should be **moved out**:
   - Detailed schemas, specs, or data models → `.claude/skills/<topic>/SKILL.md`
   - Backend-specific rules → `backend/CLAUDE.md`
   - Frontend-specific rules → `src/CLAUDE.md` or `frontend/CLAUDE.md`
   - Detailed API documentation → `docs/`
   - Step-by-step procedures → `.claude/commands/`
   - Lists of more than 5 items → `.claude/skills/`

4. Present a proposal as a table:

| Content | Current Location | Move To | Lines Saved |
|---------|-----------------|---------|-------------|
| ...     | CLAUDE.md:45-80 | .claude/skills/schema/SKILL.md | 35 |

## Rules
- Do NOT modify any files until I explicitly approve the proposal
- Show the current line count and target line count
- Preserve all information. Nothing gets deleted, only relocated
- Each skill file needs frontmatter: name, description, and relevant file patterns
