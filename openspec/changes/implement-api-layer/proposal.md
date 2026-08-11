# Proposal: Implement FastAPI layer over System C (work unit 16, P6.1)

## Intent

User-directed priority after execution wiring: close the API layer.
Deliver CLAUDE.md §14's API component (FastAPI, demo auth, validation,
correlation ID, basic limits) and roadmap P6.1: an HTTP surface over the
already-built `SystemC`, catalog, audit, and approval service.

## Scope

- `POST /requests`: validates an `ExecuteRequest` (query text + structured
  proposal + role + idempotency key), generates a server-side correlation
  id (`uuid4`, never client-supplied — prevents a caller from forging
  audit correlation), calls `SystemC.handle`, returns decision/skill/
  reasons.
- `GET /skills`: read-only catalog listing.
- `GET /audit/{correlation_id}`: read-only audit/abstention lookup.
- `POST /approvals`: wraps `ApprovalService.grant`.
- Demo API-key auth (`X-API-Key` header, `Depends`), applied to every
  route — no unauthenticated read.
- In-memory, single-process rate limiter (`RateLimiter`, sliding
  60-second window), applied to every route.

## Non-goals

No PostgreSQL/pgvector persistence (roadmap P6.2 — state remains
process-local in-memory, matching every module built so far). No real
authentication/authorization system (the demo API key is explicitly
named as demo-only, not a production credential). No distributed rate
limiting. No Odoo/production deployment concerns.

## Follow-on dependency

Persistence (P6.2) and integration/contract tests beyond the FastAPI
`TestClient` suite (P6.4) are next; A/B systems (P8.1 remainder) build on
having this API surface to drive from an experiment runner later.

## Success criteria

Missing/wrong API key is rejected (401) on every route; a normal request
executes and returns a server-generated correlation id; a missing-field
request abstains; the audit endpoint reflects a prior execution; an
approval grant returns its actor/scope/expiry; exceeding the rate limit
returns 429 on every route, not just one. `python -m pytest` passes in
full.

## Forecast

One new source file (`api.py`, 162 lines) and one new test file
(`test_api.py`, 104 lines): **266 added lines**, below the 400-line
budget. `pyproject.toml`/`uv.lock` show 867 insertions from resolving
`fastapi`/`starlette`/`uvicorn`/`httpx` — machine-generated, flagged
separately, same treatment as prior dependency additions.
