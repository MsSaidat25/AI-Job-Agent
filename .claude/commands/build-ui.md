Build frontend UI components using AI-powered generation with Google Stitch and UI UX Pro Max design intelligence.

## Intent Contract

Before invoking any agent, construct this block and pass it as context:

```
INTENT_CONTRACT:
  INTENT: "[User's original request - e.g., 'Build a login page with social auth buttons']"
  SCOPE: "[Components to generate, target directory, framework]"
  SUCCESS_CRITERIA: "[Component renders, matches design system, user accepts preview]"
  INTENT_HASH: "[First 8 chars of SHA256(INTENT|SCOPE|SUCCESS_CRITERIA)]"
```

## Step 1: Gather Requirements

Ask the user (if not already specified):
1. **What to build**: page, component, section, layout?
2. **Functionality**: what does it do?
3. **Style preference**: any aesthetic direction? (minimal, bold, playful, corporate, etc.)

Detect automatically:
- Project framework (check package.json, tsconfig, etc.)
- Existing design system or component library
- CSS approach (Tailwind, CSS Modules, styled-components)

## Step 2: Launch Frontend Builder

Invoke the **frontend-builder** agent with:
- The user's request
- Detected framework and conventions
- The Intent Contract

The agent will:
1. Generate a design system (via UI UX Pro Max if available)
2. Generate UI code (via Google Stitch if available, or manually)
3. Preview the result for user approval
4. Write accepted components to the project

## Step 3: Post-Build Verification

After the agent completes:
1. Run the project's dev server if not already running
2. Verify the component renders without console errors
3. Check responsive layout (mobile, tablet, desktop)
4. Run lint and type check to ensure no issues introduced

## Quick Examples

```
# Generate a landing page
/build-ui Create a SaaS landing page with hero, features grid, pricing table, and CTA

# Generate a specific component
/build-ui Build a data table component with sorting, filtering, and pagination

# Generate with style direction
/build-ui Build a dashboard sidebar with glassmorphism style and dark mode support
```
