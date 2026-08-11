# Proposal: Integrate System C end to end (work unit 9, closes P5.4)

## Intent

Deliver roadmap P5.4 and the CLAUDE.md §14 architecture diagram's governed
path: parser proposal → TF-IDF retriever → policy engine → runtime →
audit, as a single orchestrator. All prerequisite pieces (units 2–8) are
complete.

## Scope

- `SystemC.handle(correlation_id, query_text, proposal, role,
  idempotency_key)`: ranks candidates via `TfidfRetriever`, abstains (and
  audits the abstention) when `should_abstain` holds, otherwise resolves
  approval via an optional `ApprovalService`, calls `policy.decide` +
  `Runtime.execute`, and records the outcome via `AuditStore.record`.
- `AuditStore` extended with `record_abstention`/`abstentions`
  (`AbstentionEvent`): CLAUDE.md §25 requires every terminal decision
  recorded, and abstention is now a terminal decision this system can
  reach before any policy/runtime call exists to audit.

## Non-goals

No LLM call producing the `IntentProposal` (still work unit 7's scope: the
proposal is taken as already produced). No API/HTTP layer (P6.1). No
embeddings/hybrid ranking (separate, in-progress unit).

## Follow-on dependency

The API layer (P6.1) will call `SystemC.handle` per request; not
implemented here.

## Success criteria

A confident, permitted request mutates `FakeERPAdapter` exactly once and
produces one `AuditEvent`; a missing required field or a low-confidence
match abstains without any adapter mutation and produces one
`AbstentionEvent`; an inactive skill still resolves to `DENY` and is
audited (no silent drop); a repeated idempotency key through `SystemC`
mutates the adapter only once; a valid `ApprovalService` grant turns an
R2 `REQUIRE_APPROVAL` into `ALLOW`. `python -m pytest` passes in full.

## Forecast

One new source file (`system_c.py`, 82 lines), one new test file
(`test_system_c.py`, 145 lines), and an extension to `audit.py` (+22
lines, `record_abstention`/`abstentions`/`AbstentionEvent`): **249 added
lines**, below the 400-line budget. No split needed.
