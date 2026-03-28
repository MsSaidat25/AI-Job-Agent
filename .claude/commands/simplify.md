Review the current codebase for structural quality and clean it up. This is not about style or formatting — it is about architecture hygiene.

## What to check

1. **Long files** (over 300 lines): Split into smaller, focused modules. Each file should have a single responsibility.

2. **Long functions** (over 50 lines): Extract helper functions. If a function does more than one thing, break it apart.

3. **Duplicate code**: Find code blocks that appear in multiple files. Extract them into a shared utility module that individual files can import. Common patterns to look for:
   - Repeated validation logic
   - Identical error handling blocks
   - Copy-pasted API call patterns
   - Similar data transformation functions

4. **Directory bloat**: If a directory has more than 20 source files, suggest grouping them into subdirectories by feature or domain.

5. **Stale test files**: Find test files whose corresponding source files have been deleted or renamed. Ask if they should be removed.

6. **Dead exports**: Find exported functions or constants that nothing imports. Ask if they should be removed.

## How to fix

For each issue found:
- Explain what the problem is and why it matters
- Show the specific files and line numbers
- Make the fix (extract utility, split file, delete dead code)
- Verify imports still work after refactoring
- Run tests to confirm nothing broke

## Rules
- Do NOT add new dependencies
- Do NOT change public APIs or function signatures
- Do NOT refactor code that is already clean
- Keep the fixes minimal and focused — one problem at a time
- When extracting shared utilities, place them in the most logical existing directory (e.g., `src/lib/`, `src/utils/`, `shared/`)
- Always preserve existing test coverage
