# Session: 2026-04-10

**Project:** AI Job Agent
**Topic:** React Native + Expo mobile frontend build, code review, backend fixes, and UAT attempt

---

## What We Are Building

A mobile-first React Native + Expo application for the AI Job Agent platform. The app provides job seekers with AI-powered job search, resume/cover letter generation, application tracking (Kanban board), a chat agent, and a dashboard with analytics. It connects to the existing FastAPI backend via REST API with session-based auth (X-Session-ID header).

The app lives in `mobile/` at the project root. It was designed with a "Stone & Copper" color theme (copper #B87333 primary, stone gray surfaces), but the user rejected the theme after seeing it rendered. A new theme and responsive desktop layout are needed before commit.

A project roadmap for Employer Portal and Admin Portal was also created at `docs/PROJECT_ROADMAP.md` to track future work.

---

## What WORKED (with evidence)

- **Full mobile app scaffold** - 40+ TypeScript files created: API client, 7 Zustand stores, 8 screens, 7 UI components, 5 navigation stacks, type definitions mirroring all backend schemas. TypeScript compiles clean (0 errors).
- **Backend fixes** - Removed `from __future__ import annotations` from api.py and all router files (was breaking FastAPI body parameter parsing). All 142 tests pass (previously 36 were failing). Confirmed by: `pytest` 142 passed, `pyright` 0 errors, `ruff check` all passed.
- **New Pydantic model for export-content** - Replaced raw `dict[str,str]` with `ExportContentRequest` with max_length validation. Confirmed by: pyright 0 errors, tests pass.
- **Code review findings all fixed** - CRITICAL (4), HIGH (7), MEDIUM (6+) issues identified and resolved across three review passes. Includes: session race condition, chat FlatList ordering, Toast memory leak, incomplete logout, unused imports, missing error displays, HTTPS URL validation, X-Forwarded-For IP trust direction, session auth on export-content, expo-secure-store for PII.
- **Expo web bundling** - Metro successfully bundles 1205 modules after fixing dependency issues. Confirmed by: bundle compiles in ~20s, serves at localhost:8081.
- **App renders in Chrome** - Welcome screen renders with logo, feature rows (Ionicons), and "Get Started" button. Navigation to ProfileSetup works. Form validation ("Name, email, and location are required.") fires correctly.

---

## What Did NOT Work (and why)

- **Node 24 (system default) + Metro bundler on Windows** - `ERR_UNSUPPORTED_ESM_URL_SCHEME` when Metro tries to `import()` the config file using a Windows `C:\` path. Fixed by installing fnm and using Node 20 (v20.20.2). This is a known Metro + Windows ESM issue affecting Node 22+ as well.
- **react-dom version mismatch** - `npm install` pulled react-dom@19.2.5 but react is pinned at 19.1.0. React 19 requires exact version match. Fixed by pinning `react-dom@19.1.0`.
- **Zustand v5 import.meta.env** - Zustand v5's Redux DevTools integration uses `import.meta.env.MODE` which Metro can't handle in its output (not ESM). A Babel plugin was attempted but didn't catch all patterns. The app still renders despite the console error (it's non-fatal), but a proper fix is needed (either downgrade Zustand to v4 or add a complete import.meta polyfill).
- **SplashScreen.preventAutoHideAsync() on web** - Called at module level, blocked React from rendering on web. Fixed by making font loading non-blocking on web with `Platform.OS !== "web"` guard.
- **Stone & Copper theme** - User rejected after seeing it rendered. Found it looked "horrible" and "AI-built." Need a completely new, more creative theme direction.
- **Desktop layout** - App renders as stretched mobile layout on laptop. No max-width, no responsive breakpoints. Content is left-aligned but header is centered. Looks unprofessional on wide screens.
- **ProfileSetup ScrollView** - Does not scroll on desktop web browser. React Native ScrollView needs explicit height constraints on web.
- **`npx expo install --fix`** - Expo's auto-fix command fails on Windows because it spawns npm with incompatible args. Workaround: manually `npm install` the specific versions.

---

## What Has NOT Been Tried Yet

- Zustand v4 downgrade (would eliminate import.meta issue cleanly)
- `@expo/html-elements` for responsive web containers
- CSS media queries via NativeWind for responsive breakpoints
- A `ResponsiveContainer` wrapper component with max-width on web
- Testing on actual mobile emulator (Android Studio / Xcode Simulator)
- Full UAT execution (only T1-T3 partial completed)
- Dark mode visual testing
- Chat screen with actual LLM responses
- Kanban board with real application data

---

## Current State of Files

| File | Status | Notes |
|------|--------|-------|
| `mobile/App.tsx` | 🔄 In Progress | Font loading works, needs theme overhaul |
| `mobile/src/api/client.ts` | ✅ Complete | Session interceptor with retry + profile re-submission |
| `mobile/src/api/session.ts` | ✅ Complete | Session creation (no dual persistence) |
| `mobile/src/api/endpoints/*.ts` | ✅ Complete | All 8 endpoint files match backend routes |
| `mobile/src/types/*.ts` | ✅ Complete | All types mirror backend schemas exactly |
| `mobile/src/stores/*.ts` | ✅ Complete | 7 Zustand stores with persist (session+profile use SecureStore) |
| `mobile/src/navigation/*.tsx` | ✅ Complete | Root, MainTab, 5 stack navigators |
| `mobile/src/screens/**/*.tsx` | 🔄 In Progress | All 8 screens built, need theme + responsive fixes |
| `mobile/src/components/ui/*.tsx` | 🔄 In Progress | 7 components, need theme update |
| `mobile/src/utils/*.ts` | ✅ Complete | constants, formatters, storage, secureStorage, theme |
| `mobile/tailwind.config.ts` | 🔄 In Progress | Has NativeWind preset, needs new color palette |
| `mobile/babel.config.js` | ✅ Complete | Expo preset + reanimated plugin |
| `mobile/metro.config.js` | ✅ Complete | NativeWind integration |
| `api.py` | ✅ Complete | CORS origins updated, future annotations removed, X-Forwarded-For fixed |
| `routers/*.py` | ✅ Complete | Future annotations removed, KanbanCard reordered, ExportContentRequest added |
| `alembic.ini` | ✅ Complete | Created (was missing) |
| `docs/PROJECT_ROADMAP.md` | ✅ Complete | Employer Portal + Admin Portal phases documented |

---

## Decisions Made

- **React Native + Expo** over PWA or Flutter. Reason: single codebase for iOS/Android/web, JS ecosystem, Expo managed workflow
- **Zustand** over Redux/Context for state. Reason: lightweight, built-in persist, no boilerplate
- **NativeWind** for styling. Reason: Tailwind for RN, dark mode support, familiar syntax
- **expo-secure-store** for session ID and profile PII. Reason: encrypted storage on native, AsyncStorage fallback on web
- **Stone & Copper theme REJECTED** by user. Needs replacement.
- **Full responsive redesign** chosen over phone-frame or mobile-only approach
- **Removed `from __future__ import annotations`** from all FastAPI files. Reason: incompatible with FastAPI's runtime type introspection for body parameters
- **fnm + Node 20** required for Expo dev. System Node 24 breaks Metro on Windows.
- **react-dom must be pinned to 19.1.0** to match react version exactly

---

## Blockers & Open Questions

1. **New theme needed** - User wants genuinely creative options, not typical AI palettes (no coral, no purple/indigo, no Stone & Copper). Reference real brands for inspiration.
2. **Responsive desktop layout** - Every screen needs desktop breakpoints. User chose "full responsive redesign" over phone-frame approach.
3. **ProfileSetup ScrollView broken on web** - Needs explicit height or flex layout fix for web platform.
4. **Zustand v5 import.meta.env console error** - Non-fatal but messy. Consider downgrading to Zustand v4 or adding polyfill.
5. **User dislikes em dashes** - Never use them in any output. Saved in memory.

---

## Exact Next Step

Start a new session. Present 3-4 genuinely creative theme proposals (reference real brands like Stripe, Figma, Vercel, Aesop, etc., not generic AI palettes). After theme approval, update all color tokens, fix the responsive layout with proper desktop breakpoints, fix the ScrollView web bug, then re-run the full UAT from the plan at `docs/sessions/` and `plans/cryptic-leaping-simon.md`.

Run `eval "$(fnm env --shell bash)" && fnm use 20` before any npm/expo commands.
