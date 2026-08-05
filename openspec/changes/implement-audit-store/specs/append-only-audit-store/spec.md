# Spec: append-only audit store

Traces to CLAUDE.md §14 (Audit Store), §30 (redaction control); roadmap
P4.5; RF-15.

## Requirements

### MUST: append-only public surface

`AuditStore` MUST expose no method that deletes or mutates a previously
recorded `AuditEvent`. `record()` MUST only append.

**Scenario:** two `record()` calls; `events()` returns both, in call order,
and no public method exists to remove either.

### MUST: correlation-filtered, independent query

`events(correlation_id)` MUST return only events matching that id when
given, and all events when omitted. The returned collection MUST be
independent of internal state — external mutation of the returned value
MUST NOT affect subsequent `events()` calls.

**Scenario:** `events()` result is cleared by the caller; a later
`events()` call still returns the original count.

### MUST: configurable field redaction

Output dict values whose key is in the store's configured `redact_keys`
MUST be replaced with the `REDACTED` sentinel before storage; keys outside
that set MUST pass through unchanged, including in nested dicts.

**Scenario:** `redact_keys={"email"}`; output `{"name": "Acme", "email":
"a@b.com"}` is stored as `{"name": "Acme", "email": "***REDACTED***"}`.

### MUST: deterministic, injectable timestamp

The store MUST accept a `clock` callable and use it (not a hidden global
clock) to stamp `recorded_at`, so tests are deterministic.

**Scenario:** a fixed clock produces an identical `recorded_at` on every
recorded event within the same test.
