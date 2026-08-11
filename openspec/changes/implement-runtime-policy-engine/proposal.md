# Proposal: Implement deterministic runtime and policy engine (work unit 4)

## Intent

Deliver roadmap P4.3–P4.4 and CLAUDE.md §§16, 24–25: a deny-by-default
policy engine and a runtime that only executes registered handlers,
replays idempotent results, and reports postcondition outcomes. The skill
contract (work unit 3) and FakeERP (work unit 2) are both complete, so this
is the next unblocked step per D-10.

## Scope

- `policy.decide(skill, role, approval_granted=False) -> PolicyOutcome`:
  deny-by-default; role/state gating; R0–R1 auto-allow; R2 requires
  approval then allows; R3 requires approval and simulates even once
  approved (CLAUDE.md §16 R3 note).
- `runtime.Runtime`: `register(skill_id, version, handler)`,
  `execute(skill, args, role, idempotency_key, ...)`. Only ALLOW invokes
  the handler; DENY/REQUIRE_APPROVAL/SIMULATE never mutate `FakeERPAdapter`.
  Repeated idempotency keys replay the cached result instead of
  re-invoking. Optional postcondition-check callables run after execution
  and their aggregate result is reported, not silently dropped.
- Focused tests for both modules.

## Non-goals

Approval-service persistence (actor/scope/expiration), audit trail, API,
retrieval, LLM/parser, and the A/B/C systems remain excluded (CLAUDE.md
§11; project-context.md).

## Follow-on dependency

Audit store (append-only trace) and the approval service are the next
required pieces before API/retrieval work; they are not implemented here.

## Success criteria

`decide` denies an unpermitted role and an inactive skill regardless of
risk; R2/R3 both require approval before anything executes; R3 stays
`SIMULATE` even when approved. `Runtime.execute` raises
`UnregisteredHandlerError` for an unregistered skill, never calls the
handler on DENY, and a repeated idempotency key returns the same output
without a second handler invocation. `python -m pytest` passes in full.

## Forecast

Two new source files (`policy.py` 71, `runtime.py` 79) and two new test
files (`test_policy.py` 59, `test_runtime.py` 101): **310 added lines**,
below the 400-line budget. No split needed.
