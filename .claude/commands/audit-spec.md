Run the spec-validator agent against the specification.

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

1. Find spec files in `docs/` (look for files with "spec", "requirements", or "PRD" in the name)
2. If no spec found, ask the user to provide the spec file path
3. Launch the spec-validator agent with the spec file
4. Report the traceability matrix
5. Highlight any MISSING or PARTIAL requirements

Focus on P0 requirements first, then P1, then P2.
