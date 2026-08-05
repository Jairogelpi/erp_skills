# Spec: Systems A and B

Traces to CLAUDE.md §18 (sistemas comparados); roadmap P8.1.

## Requirements

### MUST: System A has no governance layer

`SystemA.handle` MUST call the adapter directly on the LLM's tool
selection with no skill registry lookup, no risk classification, no
approval check, and no audit record.

### MUST: System B validates typed arguments, nothing else

`SystemB.handle` MUST reject execution when any of the selected skill's
`input_schema["required"]` fields is absent or blank, and MUST NOT apply
any risk-tiered policy decision (an R2/R3 skill with complete arguments
executes immediately, unlike System C).

### MUST: both systems surface errors, never crash

Adapter/argument errors (`UnknownModelError`, `UnknownRecordError`,
`KeyError`) raised while executing MUST be caught and returned as a
result field, not propagated.

### MUST NOT: the deterministic stub is not a confirmatory LLM

`DeterministicStubClient` MUST be documented as test/dev-only; nothing in
this unit uses it to claim a confirmatory A/B/C result.
