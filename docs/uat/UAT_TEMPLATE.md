# UAT Scenario Pack: AI-Job-Agent

## Pre-Conditions
- [ ] Application is deployed to staging
- [ ] Test accounts are created
- [ ] Test data is seeded

## Scenarios

### UAT-001: Health Check
**Priority:** P0
**Preconditions:** Application is running
**Steps:**
1. Send GET request to the health endpoint
2. Verify response status is 200
3. Verify response body contains status: "ok"
**Expected Result:** Health endpoint responds with 200 and status "ok"
**Actual Result:** ___
**Status:** NOT RUN
**Tester:** ___
**Date:** ___
**Notes:** ___

### UAT-002: Structured Error Response
**Priority:** P1
**Preconditions:** Application is running
**Steps:**
1. Send a request to a non-existent endpoint
2. Verify response has structured error format
3. Verify no stack traces or internal details are leaked
**Expected Result:** Error response follows format: { error: { code, message } }
**Actual Result:** ___
**Status:** NOT RUN
**Tester:** ___
**Date:** ___
**Notes:** ___

### UAT-003: Graceful Shutdown
**Priority:** P1
**Preconditions:** Application is running with active connections
**Steps:**
1. Send SIGTERM to the application process
2. Verify in-flight requests complete
3. Verify database connections are closed
4. Verify process exits with code 0
**Expected Result:** Application shuts down gracefully without dropping requests
**Actual Result:** ___
**Status:** NOT RUN
**Tester:** ___
**Date:** ___
**Notes:** ___
