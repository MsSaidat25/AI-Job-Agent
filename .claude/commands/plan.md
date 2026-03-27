Invoke the **planner** agent to create a comprehensive implementation plan before writing any code.

## Process

1. Ask the user what they want to build (or use the description they provided)
2. Launch the `planner` agent with the feature description
3. The planner will analyze the codebase, break down the work into phases, and identify risks
4. Present the plan and WAIT for user confirmation before proceeding

## Important

- NEVER write code until the user explicitly confirms the plan
- If the user wants modifications, update the plan and re-present
- After approval, suggest using `/tdd` to implement with test-driven development

## Integration

After planning, use these commands:
- `/tdd` — implement with test-driven development
- `/build-fix` — fix any build errors that come up
- `/code-review` — review the completed implementation
