# Spec: approval service

Traces to CLAUDE.md §14 (Approval Service); roadmap P6.3.

## Requirements

### MUST: TTL-bounded validity

`is_valid(scope)` MUST return `True` only when the clock's current time is
within `[granted_at, expires_at)` for some approval recorded on that exact
scope, and `False` otherwise (no approval, expired, or different scope).

**Scenario:** approval granted with `ttl_seconds=60`; valid immediately;
invalid once the clock advances past 60 seconds.

### MUST: reject non-positive TTL

`grant(..., ttl_seconds)` MUST raise `ValueError` when `ttl_seconds <= 0`.

### MUST: scope isolation

An approval granted for one scope MUST NOT make `is_valid` return `True`
for a different scope.
