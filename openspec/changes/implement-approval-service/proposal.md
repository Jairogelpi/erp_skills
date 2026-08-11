# Proposal: Implement approval service (work unit 8, closes P6.3)

## Intent

Deliver roadmap P6.3 and CLAUDE.md §14 (Approval Service): record actor,
scope, granted instant, and expiration for an approval, so a
`REQUIRE_APPROVAL` policy decision can be re-checked with
`approval_granted=True`. Parser/retrieval (work unit 7) is complete.

## Scope

- `Approval`: frozen dataclass (`actor`, `scope`, `granted_at`,
  `expires_at`).
- `ApprovalService.grant(actor, scope, ttl_seconds)`: rejects
  non-positive TTLs; records one approval with an injectable clock.
- `ApprovalService.is_valid(scope)`: `True` only while now is within
  `[granted_at, expires_at)` for some recorded approval on that scope.

## Non-goals

No persistence, no wiring into `policy.decide`/`Runtime.execute` (call-site
wiring is API-layer/system-C integration work), no revocation endpoint
(not in CLAUDE.md §14's approval-service description).

## Follow-on dependency

API layer (P6.1) will call `grant`/`is_valid` and translate the result into
`approval_granted` for `policy.decide`; not implemented here.

## Success criteria

An approval is valid before its TTL elapses and invalid after; a different
scope is never valid from another scope's approval; a non-positive TTL
raises `ValueError`; a scope with no granted approval is invalid.
`python -m pytest` passes in full.

## Forecast

One new source file (`approval.py`, 42 lines) and one new test file
(`test_approval.py`, 41 lines): **83 added lines**, well below the
400-line budget. No split needed.
