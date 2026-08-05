# Spec: HTTP API over System C

Traces to CLAUDE.md §14 (API component); roadmap P6.1.

## Requirements

### MUST: every route requires the demo API key

Every route MUST reject a request missing or mismatching `X-API-Key`
with `401`, including read-only routes.

### MUST: correlation id is server-generated

`POST /requests` MUST generate its own correlation id; it MUST NOT accept
one from the request body (a client-supplied id would let a caller spoof
or collide audit correlation).

### MUST: rate limit applies uniformly

Exceeding `RATE_LIMIT_PER_MINUTE` requests within a 60-second window MUST
return `429` on every route that depends on `enforce_rate_limit`, not a
subset.

### MUST: audit endpoint reflects real state

`GET /audit/{correlation_id}` MUST report the decisions actually recorded
by `AuditStore` for that id, including zero events for an unknown id
(not an error).
