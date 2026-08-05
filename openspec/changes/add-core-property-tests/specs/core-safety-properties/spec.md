# Spec: core safety properties

Traces to CLAUDE.md §29 (property-based testing); roadmap P4.6.

## Requirements

### MUST: R4 is never a registrable skill

For any role, module, and description, constructing a `SkillDefinition`
with `risk_class=RiskClass.R4` MUST raise `ValidationError`.

### MUST: an idempotency key never produces two mutations

For any repeat count ≥ 1, calling `Runtime.execute` the same number of
times with an identical idempotency key MUST leave exactly one record in
the adapter's store for that model.

### MUST: a disallowed model never reaches the adapter store

For any model name not in the adapter's allowlist, `create` MUST raise
`UnknownModelError` and the store MUST have no entry for that model name.

### MUST: every terminal execution has an audit event

For any role, recording a `Runtime.execute` result via `AuditStore.record`
MUST increase `len(store.events())` by exactly one.

### MUST: restrictive policy inputs never outrank permissive ones

For any non-R4 risk class and any state: a denied role's decision MUST NOT
rank more permissive (`DENY < REQUIRE_APPROVAL < SIMULATE < ALLOW`) than an
allowed role's decision under otherwise-identical inputs; a non-`ACTIVE`
state's decision MUST NOT rank more permissive than the same skill in
`ACTIVE` state under otherwise-identical inputs.
