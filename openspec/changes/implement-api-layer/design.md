# Design: HTTP API over System C

## Contract

```
POST /requests   {query_text, proposal, role, idempotency_key} -> {correlation_id, decision, selected_skill_id, reasons}
GET  /skills     -> [{skill_id, module, risk_class, description}, ...]
GET  /audit/{id} -> {events: [decision, ...], abstentions: int}
POST /approvals  {actor, scope, ttl_seconds} -> {actor, scope, expires_at}
```

`create_app()` builds one `FakeERPAdapter`/`Runtime`/`TfidfRetriever`/
`AuditStore`/`ApprovalService`/`SystemC` per app instance — tests call it
fresh per test for isolation; the module-level `app = create_app()` is
the single process-lifetime instance a real server process would run.

## Alternatives considered

- **Module-level global state instead of `create_app()`**: rejected.
  A factory function is what makes `tests/test_api.py` able to build an
  isolated app per test (matching every other module's "fresh instance
  per test" pattern in this codebase) while still exposing a single
  `app` object for `uvicorn erp_agent_os.api:app` to run.
- **Accept correlation_id from the client**: rejected — see spec.md.
  Server-generated ids are a deliberate trust-boundary decision (CLAUDE.md
  §30: separation between instructions and data extends to not letting
  client input control audit-trail identity).
- **JWT/OAuth2 instead of a demo API key**: rejected for this unit.
  CLAUDE.md §14 explicitly scopes API auth to "autenticación para la
  demo"; a real auth system is out of scope for the confirmatory core and
  would be premature before the API even has a real deployment target.
- **Redis/external rate limiter**: rejected. In-memory, sliding-window,
  single-process is honest about what this unit actually provides
  ("límites básicos"), and doesn't add an external dependency for a demo
  concern.

## Risks

- No persistence: restarting the process loses all skills/audit/approval
  state (skills are fine — reloaded from `catalog.py` — but audit history
  and approvals are not). Documented, not hidden; P6.2 is the fix.
- The demo API key is a single shared constant, not per-user; fine for a
  demo, explicitly not a production auth model.

## Test strategy

`tests/test_api.py`: missing-key rejection, skill listing count, a full
ALLOW execution round-trip (with correlation id), a missing-field
abstention, audit reflecting a prior execution, an approval grant
response, and rate-limit enforcement (looping past the limit and
asserting 429 — not just trusting the implementation).
