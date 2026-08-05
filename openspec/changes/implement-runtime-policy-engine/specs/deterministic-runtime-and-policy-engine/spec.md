# Spec: deterministic runtime and policy engine

Traces to CLAUDE.md §16 (risk taxonomy), §24 (policy engine), §25
(idempotency/postconditions); roadmap P4.3–P4.4; RF-06–RF-14.

## Requirements

### MUST: deny by default

`decide` MUST return `DENY` when the role is not in
`skill.permissions.allowed_roles`, and MUST return `DENY` when
`skill.state is not ACTIVE`, regardless of risk class.

**Scenario:** role absent from `allowed_roles` → `DENY`. **Scenario:**
skill in `APPROVED` (not `ACTIVE`) with an otherwise-valid role → `DENY`.

### MUST: risk-tiered decisions

R0/R1 MUST resolve to `ALLOW` once role/state checks pass. R2 MUST resolve
to `REQUIRE_APPROVAL` unless `approval_granted`, then `ALLOW`. R3 MUST
resolve to `REQUIRE_APPROVAL` unless `approval_granted`, then `SIMULATE`
(never `ALLOW` — CLAUDE.md §16: R3 "preferentemente simulación").

**Scenario:** R3 skill, approved → `SIMULATE`, not `ALLOW`.

### MUST: only registered handlers execute

`Runtime.execute` MUST raise `UnregisteredHandlerError` when no handler was
registered for `(skill_id, version)`, and MUST NOT invoke any handler when
the policy decision is `DENY`, `REQUIRE_APPROVAL`, or `SIMULATE`.

**Scenario:** `DENY` decision; handler registered; handler function is not
called (no side effect on `FakeERPAdapter`).

### MUST: idempotent replay

A repeated `idempotency_key` on `ALLOW` MUST return the previously stored
`ExecutionResult.output` and MUST NOT invoke the handler a second time.

**Scenario:** same skill/args/key executed twice; handler call count stays
at one; both results carry identical `output`.

### MUST: postcondition outcome is observable

When `postcondition_checks` are supplied, `ExecutionResult.postconditions_met`
MUST reflect their aggregate boolean result; when none are supplied it MUST
be `None` (no verification requested, not silently "passed").

**Scenario:** a failing check yields `postconditions_met is False` without
raising or hiding the executed output.
