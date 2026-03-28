Load a saved session file and orient before doing any work.

## Process

1. **Find the session file**: Check `docs/sessions/` for the most recent `*-session.md` file
2. **Read the entire file**: Do not summarize yet
3. **Present a briefing** in this format:

```
SESSION LOADED: [file path]
════════════════════════════════════════════════

PROJECT: [project name / topic]

WHAT WE'RE BUILDING:
[2-3 sentence summary in your own words]

CURRENT STATE:
✅ Working: [count] items confirmed
🔄 In Progress: [list files in progress]
🗒️ Not Started: [list planned but untouched]

WHAT NOT TO RETRY:
[list every failed approach with its reason]

OPEN QUESTIONS / BLOCKERS:
[list any blockers]

NEXT STEP:
[exact next step from the file]

════════════════════════════════════════════════
Ready to continue. What would you like to do?
```

4. **WAIT for the user**. Do NOT start working automatically

## Edge Cases

- **No session files found**: Tell the user to run `/save-session` first
- **Session references deleted files**: Note "file.ts referenced but not found on disk"
- **Session is > 7 days old**: Note "This session is N days old, things may have changed"
- **Empty or malformed file**: Report and suggest creating a new session

## Rules

- Never modify the session file. It's a read-only historical record
- Never skip the "What Not To Retry" section. It's the most important
- Always wait for the user before starting work
- If the next step is defined and the user says "continue", proceed with that exact step
