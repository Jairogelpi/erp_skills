# Proposal: Harden adapter/runtime error handling (work unit 14)

## Intent

Discovered while building benchmark execution wiring: `FakeERPAdapter`
had no way to seed a record under a caller-chosen natural key (needed to
pre-populate entities referenced by id/name in benchmark cases), no way
to list a model's records (needed by search/duplicate-detection
handlers), and `Runtime.execute` crashed the whole run on any handler
exception instead of surfacing it as a result. Fix all three before
wiring benchmark cases to execution.

## Scope

- `FakeERPAdapter.create(..., record_id: str | None = None)`: optional
  caller-supplied key; raises `DuplicateRecordError` if already taken.
- `FakeERPAdapter.list(model) -> dict[str, dict]`: read-only, independent
  copy of all records for a model.
- `Runtime.execute`: catches `UnknownModelError`, `UnknownRecordError`,
  and `KeyError` (malformed/mismatched handler arguments) raised by a
  handler, returning `ExecutionResult(..., handler_error=str)` instead of
  propagating the exception.

## Non-goals

No input-schema/argument-range validation (that's RF-06/07, a larger,
separate policy-engine feature — this unit only prevents a handler
exception from crashing the caller, it does not add pre-execution
validation).

## Success criteria

`create(record_id=...)` seeds under that key; a duplicate explicit key
raises `DuplicateRecordError`; `list` returns an independent copy;
`Runtime.execute` returns a result with `handler_error` set (not an
exception) for `UnknownRecordError`/`UnknownModelError`/`KeyError` raised
inside a handler, for role/state/risk that would otherwise reach the
handler. `python -m pytest` passes in full.

## Forecast

`adapters.py` (+13), `runtime.py` (+12), `test_fake_erp.py` (+33),
`test_runtime.py` (+32): **90 added lines**, below the 400-line budget.
