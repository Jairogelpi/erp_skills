# Spec: versioned skill contract

Traces to CLAUDE.md §15 (contract, lifecycle), §16 (risk taxonomy R0–R4);
roadmap P4.2; D-05.

## Requirements

### MUST: complete contract fields

`SkillDefinition` MUST require `skill_id`, `version`, `module`, `operation`,
`description`, `risk_class`, `input_schema`, `permissions.allowed_roles`
(nonempty), `preconditions`, `execution` (`handler` as dotted path,
`timeout_seconds` > 0, `max_retries` ≥ 0, `idempotent`), and `postconditions`
(nonempty). `approval_required_when` and `state` MUST default to `[]` and
`DRAFT` respectively when omitted.

**Scenario:** all fields present with a nonempty `allowed_roles` and
`postconditions` list; construction succeeds and `state == DRAFT`.

### MUST: semantic version format

`version` MUST match `MAJOR.MINOR.PATCH`.

**Scenario:** `version="1.2"` raises `ValidationError`.

### MUST NOT: register R4 risk

`risk_class` MUST NOT accept `R4` (CLAUDE.md §16: unconditional block, never
registered as an executable skill).

**Scenario:** `risk_class=RiskClass.R4` raises `ValidationError`.

### MUST: fixed lifecycle graph, no DRAFT→ACTIVE

`transition(current, target)` MUST allow only:
`DRAFT→VALIDATED`, `VALIDATED→TESTED`, `TESTED→APPROVED`,
`APPROVED→ACTIVE`, `ACTIVE→DEPRECATED`, and any state `→QUARANTINED`. It
MUST reject every other move, including a direct `DRAFT→ACTIVE` jump
(CLAUDE.md §15: "No se permitirá la transición directa de `DRAFT` a
`ACTIVE`").

**Scenario:** `transition(DRAFT, ACTIVE)` raises `InvalidTransitionError`.
**Scenario:** `transition(state, QUARANTINED)` succeeds for every
non-quarantined state.
