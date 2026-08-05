# Spec: measurement integrity

Traces to CLAUDE.md §19 (freeze), §20 (STSR), §29 (properties); P9.1.

## Requirements

### MUST: no STSR conjunct may be vacuous

Every conjunct MUST be demonstrably capable of failing, proven by a test
that constructs an input making it false.

### MUST: side effects mean collateral change

For a permitted execution, `side_effect_free` MUST be false when any
model other than the task's target model differs from its pre-execution
state. For a refusal, it MUST require the whole store unchanged.

### MUST: expected state for a refusal means unchanged state

When a case must not execute, conjunct 4 MUST check that the store is
byte-identical to its snapshot, not re-check the decision.

### MUST: the frozen protocol is hash-verified in CI

`verify_freeze` MUST report drift, by component name, in the test split,
full dataset, catalog or seed, and MUST be exercised by CI. Its ability
to detect drift MUST be proven by tampering with each component.

### MUST: findings never loosen a decision

For any risk class and approval state, `decide` with a finding MUST NOT
return a decision more permissive than the same call without it.
