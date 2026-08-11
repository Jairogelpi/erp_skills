# Proposal: Implement append-only audit store (work unit 5)

## Intent

Deliver roadmap P4.5 (audit portion) and CLAUDE.md §14/§30: an append-only
record of every policy decision + execution outcome, queryable by
correlation id, with field redaction. Runtime and policy engine (work unit
4) are complete and are exactly what this store records.

## Scope

- `AuditEvent`: frozen dataclass capturing correlation id, skill identity/
  version, role, decision, risk score, reasons, idempotency key/replay
  flag, postcondition outcome, (redacted) output, and an injectable-clock
  timestamp.
- `AuditStore.record(...)`: builds and appends one event; no update/delete
  method is exposed anywhere on the class — append-only by public surface.
- `AuditStore.events(correlation_id=None)`: returns an immutable `tuple`
  copy, optionally filtered.
- `_redact`: recursively masks configured dict keys in the stored output
  (CLAUDE.md §30 redaction control).

## Non-goals

Persistence (PostgreSQL), the API/correlation-ID-generation layer, approval
service (actor/scope/expiration — roadmap P6.3), and metrics aggregation
(RF-16, phase 8–9) remain excluded.

## Follow-on dependency

Property-based tests (roadmap P4.6: R4 never executes, no double mutation,
disallowed field never reaches the adapter, every terminal execution has an
audit event, monotonic policy restrictiveness) are the next SDD change and
will exercise this store together with runtime/policy end to end.

## Success criteria

`AuditStore` has no method that removes or mutates a stored event;
`events()` returns a filtered, order-preserving, independent copy;
configured redact keys are masked in nested dict output without altering
unrelated keys. `python -m pytest` passes in full.

## Forecast

One new source file (`audit.py`, 87 lines) and one new test file
(`test_audit.py`, 96 lines): **183 added lines**, well below the 400-line
budget. No split needed.
