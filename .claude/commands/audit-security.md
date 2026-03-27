Run a focused security audit on all changed files.

1. Get list of changed files: `git diff --name-only`
2. Launch the security-reviewer agent on those files
3. Additionally check:
   - No secrets committed (grep for API keys, tokens, passwords in code)
   - No `.env` files in git tracking
   - Dependencies have no known critical vulnerabilities
4. Report all findings by severity

For any CRITICAL findings, provide immediate remediation steps.
