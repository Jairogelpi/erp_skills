# Design: adapter/runtime error handling

## Alternatives considered

- **A separate `seed()` method instead of extending `create()`**:
  rejected. `create(record_id=...)` is still "create a record," just with
  a caller-chosen key instead of an auto one; a new method name would
  duplicate the model-allowlist/deep-copy logic `create` already has.
- **Catch all `Exception` in `Runtime.execute`**: rejected — too broad,
  would silently swallow real bugs (e.g. a `TypeError` from a malformed
  handler). Only the three exception types a handler can legitimately
  raise from adapter/args mismatches are caught; anything else still
  propagates, which is correct (a crash on a genuine bug should be loud).
- **Add input-schema validation instead of catching `KeyError`**:
  rejected for this unit's scope. That is materially more work (RF-06/07,
  needs a JSON-Schema-shaped validator run before the handler, not after
  it fails) and was deliberately deferred; catching `KeyError` is the
  minimal fix for "a handler crash must not crash the whole run."

## Risks

- Catching `KeyError` broadly could mask a genuine handler bug (missing a
  key it should always have) as a benign "handler_error." Accepted:
  `handler_error` is surfaced and reported (e.g. in the wiring report),
  not silently dropped, so a real bug is still visible in the count.

## Test strategy

`test_fake_erp.py`: explicit-record-id roundtrip, duplicate rejection,
`list` returns all records, `list` result independence.
`test_runtime.py`: `UnknownRecordError` from a handler is caught;
`KeyError` from mismatched handler args is caught, with the exception
type name present in `handler_error`.
