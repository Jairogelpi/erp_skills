# Tasks: Harden adapter/runtime error handling (work unit 14)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 90 |
| 400-line budget risk | Low |
| Delivery strategy | single-pr |

## Implementation (strict TDD, discovered mid-unit-15)

- [x] Extend `FakeERPAdapter.create` with optional `record_id`; add
  `DuplicateRecordError`; add `list()`. Evidence: `python -m pytest
  tests/test_fake_erp.py` → 9 passed (5 pre-existing + 4 new).
  <!-- sdd-owner: implementation -->
- [x] Extend `Runtime.execute` to catch `UnknownModelError`/
  `UnknownRecordError`/`KeyError` from handlers. Evidence: `python -m
  pytest tests/test_runtime.py` → 7 passed (5 pre-existing + 2 new).
  <!-- sdd-owner: implementation -->
- [x] Discovery trigger documented: `bench_runner`'s first full run hit a
  real `KeyError` when TF-IDF retrieval matched the wrong skill for a
  short query, crashing the run — this unit's `KeyError` handling is a
  direct fix for an observed failure, not speculative hardening.
  <!-- sdd-owner: implementation -->
- [x] Full-suite regression: `python -m pytest` → 102 passed (before unit
  15's own tests were added). <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted; `mypy src` → no issues found. <!-- sdd-owner: implementation -->
- [x] Measure retained diff: `adapters.py` (+13) + `runtime.py` (+12) +
  `test_fake_erp.py` (+33) + `test_runtime.py` (+32) = 90, below 400.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

Input-schema/argument-range validation (RF-06/07) — a materially larger,
separate policy-engine feature, not this unit's scope.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the 90-line diff.
  <!-- sdd-owner: parent -->
