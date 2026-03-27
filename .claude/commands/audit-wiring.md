Verify that all API endpoints are properly wired between frontend and backend.

1. Find all backend API endpoints (route handlers, FastAPI routers)
2. Find all frontend API calls (fetch, axios, server actions)
3. Cross-reference: every backend endpoint should have at least one frontend caller
4. Cross-reference: every frontend API call should hit a real backend endpoint
5. Check that request/response types match between frontend and backend

Output a wiring matrix:
| Backend Endpoint | Method | Frontend Caller | Type Match | Status |
|---|---|---|---|---|
| /api/users | GET | src/app/users/page.tsx | YES/NO | WIRED/ORPHAN |

Flag:
- ORPHAN backend endpoints (no frontend caller)
- DEAD frontend calls (no backend endpoint)
- TYPE MISMATCH (request/response shape differs)
