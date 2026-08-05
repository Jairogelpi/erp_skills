# Spec: FakeERP adapter contract

Traces to CLAUDE.md §14 (adapters), §19 (state restoration per observation),
§27 (Python stack); roadmap P4.1; D-03/D-10.

## Requirements

### MUST: allowlisted models only

The adapter MUST accept an explicit `allowed_models: set[str]` at
construction and MUST reject `create`, `get`, and `update` calls against any
other model with `UnknownModelError`.

**Scenario:** adapter constructed with `{"crm.lead"}`; `create("res.partner",
...)` raises `UnknownModelError`.

### MUST: unknown record rejection

`get` and `update` MUST raise `UnknownRecordError` for a record id not
present in that model's table.

**Scenario:** fresh adapter; `get("crm.lead", "999")` raises
`UnknownRecordError`.

### MUST: exact snapshot/restore

`snapshot()` MUST capture the full record store and id counter. `restore()`
MUST reset the adapter to exactly that captured state, independent of any
mutation performed after the snapshot was taken (no aliasing between the
snapshot and the live store).

**Scenario:** snapshot taken; a record is created; `restore(snapshot)`
removes that record. **Scenario:** snapshot taken after a record exists; the
record is updated; `restore(snapshot)` reverts the update.

### MUST NOT: delete or external I/O

The adapter MUST NOT expose a delete operation and MUST NOT perform any
network or filesystem I/O (CLAUDE.md §11 exclusions).
