Read docs/uat/UAT_TEMPLATE.md and execute the UAT verification process.

For each scenario in the UAT template:
1. Check if automated tests exist that cover this scenario
2. If automated: run the test and report PASS/FAIL
3. If not automated: flag as MANUAL REQUIRED
4. Update docs/uat/UAT_CHECKLIST.csv with results

Output:
- Automated coverage: X/Y scenarios have automated tests
- Results: X passed, Y failed, Z need manual testing
- Blocking issues: list any P0 failures

For P0 failures:
- Show the test output
- Suggest a fix if the failure is obvious
- Mark as BLOCKED in the checklist

For scenarios needing manual testing:
- Provide step-by-step instructions for the tester
- Note any test data or setup required
