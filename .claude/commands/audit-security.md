Run a focused security audit on all changed files.

## Intent Contract

Before invoking any agent, construct this block and pass it as context:

```
INTENT_CONTRACT:
  INTENT: "[User's original request verbatim]"
  SCOPE: "[Files/areas to examine]"
  SUCCESS_CRITERIA: "[What done looks like]"
  INTENT_HASH: "[First 8 chars of SHA256(INTENT|SCOPE|SUCCESS_CRITERIA)]"
```

Every agent invocation MUST include this block. If an agent's output does not echo back the INTENT_HASH, its results are considered unverified.

1. Get list of changed files: `git diff --name-only`
2. Launch the security-reviewer agent on those files
3. Additionally check:
   - No secrets committed (grep for API keys, tokens, passwords in code)
   - No `.env` files in git tracking
   - Dependencies have no known critical vulnerabilities
4. Report all findings by severity

For any CRITICAL findings, provide immediate remediation steps.
