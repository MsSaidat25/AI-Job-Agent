Analyze and optimize CLAUDE.md for this project.

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
- Preserve all information — nothing gets deleted, only relocated
- Each skill file needs frontmatter: name, description, and relevant file patterns
