Run the Intent Verification Protocol compliance check across all agents and commands.

## Intent Contract

Before invoking any agent, construct this block:

```
INTENT_CONTRACT:
  INTENT: "Verify all agents and commands comply with the Intent Verification Protocol"
  SCOPE: ".claude/agents/, .claude/commands/"
  SUCCESS_CRITERIA: "Every agent has PROOF_OF_INTENT, every command that invokes agents has Intent Contract, no cross-agent consistency violations"
  INTENT_HASH: "IVP-COMPLIANCE"
```

## Step 1: Protocol Compliance Scan

For each file in `.claude/agents/`:
1. Check for `PROOF_OF_INTENT` block in output section
2. Check for `NO_CONTRACT_RECEIVED` fallback handling
3. Record compliance status

For each file in `.claude/commands/` that references an agent:
1. Check for `INTENT_CONTRACT` section
2. Check that `INTENT_HASH` is referenced
3. Record compliance status

## Step 2: Launch prompt-auditor

Run the **prompt-auditor** agent on the full `.claude/` configuration with the Intent Contract above.

## Step 3: Cross-Validation

1. Pick 3 agents at random
2. For each, evaluate: given a sample intent, would the agent's instructions produce output that includes a valid PROOF_OF_INTENT?
3. Flag any agent whose instructions are ambiguous enough that the proof section could be skipped

## Step 4: Compliance Report

```
INTENT VERIFICATION PROTOCOL - COMPLIANCE REPORT

OVERALL: [X/Y agents compliant, A/B commands compliant]

NON-COMPLIANT AGENTS:
- [agent name]: [what's missing]

NON-COMPLIANT COMMANDS:
- [command name]: [what's missing]

CONSISTENCY ISSUES:
- [cross-agent term conflicts, severity definition mismatches]

RECOMMENDATIONS:
- [prioritized list of fixes]
```
