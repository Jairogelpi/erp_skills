# Spec: adapter/runtime error handling

Traces to CLAUDE.md §14 (adapter), §25 (runtime); discovered during
roadmap P8.1 groundwork.

## Requirements

### MUST: optional explicit record id on create

`create(model, fields, record_id=None)` MUST use `record_id` as the key
when given, and MUST raise `DuplicateRecordError` when that key already
exists. Omitting `record_id` MUST preserve the existing auto-increment
behavior.

### MUST: list returns an independent copy

`list(model)` MUST return all records for that model as a deep copy;
mutating the returned dict MUST NOT affect the adapter's internal state.

### MUST: handler exceptions are caught, not propagated

`Runtime.execute` MUST catch `UnknownModelError`, `UnknownRecordError`,
and `KeyError` raised inside a registered handler and return an
`ExecutionResult` with `handler_error` set to a descriptive string,
rather than letting the exception propagate to the caller.
