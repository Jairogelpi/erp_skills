# Spec: System C integration

Traces to CLAUDE.md §14 (architecture), §19 (D-03), §25 (terminal
auditing); roadmap P5.4.

## Requirements

### MUST: abstain before any policy/runtime call

`SystemC.handle` MUST call `should_abstain` before `policy.decide` or
`Runtime.execute`, and MUST NOT call either when it abstains.

**Scenario:** missing required field → `SystemCResult.decision ==
"ABSTAIN"`; `FakeERPAdapter` unchanged; no `AuditEvent` recorded, exactly
one `AbstentionEvent` recorded.

### MUST: every non-abstain terminal decision is audited

Any call to `policy.decide`/`Runtime.execute` reached through `handle`
MUST result in exactly one `AuditStore.record` call, regardless of the
resulting decision (`ALLOW`, `SIMULATE`, `REQUIRE_APPROVAL`, `DENY`).

**Scenario:** an inactive skill resolves to `DENY`; exactly one
`AuditEvent` is still recorded for that correlation id.

### MUST: approval feeds policy when present

When an `ApprovalService` is supplied and `is_valid(skill.skill_id)` is
`True`, `handle` MUST pass `approval_granted=True` into both `decide` and
`Runtime.execute`.

**Scenario:** R2 skill with a valid grant on its `skill_id` resolves to
`ALLOW`, not `REQUIRE_APPROVAL`.
