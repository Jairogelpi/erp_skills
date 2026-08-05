# Tasks: Implement FakeERPAdapter (work unit 2)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 104 (source + focused test) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_fake_erp.py` written against nonexistent
  `erp_agent_os.adapters`. Evidence: `python -m pytest tests/test_fake_erp.py`
  → `ModuleNotFoundError: No module named 'erp_agent_os.adapters'` (collection
  error). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/adapters.py` with allowlisted
  create/get/update and snapshot/restore. Evidence: `python -m pytest
  tests/test_fake_erp.py` → 5 passed. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Independent cases for disallowed-model rejection,
  unknown-record rejection, and restore-after-post-snapshot-update
  (proves deep-copy independence, not just initial-state reset). Evidence:
  same 5-test run, all pass. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Shared `_require_model` guard used by all three mutating
  operations; no semantic change. Evidence: `python -m pytest` → 12 passed
  (full suite, including prior dataset tests). <!-- sdd-owner: implementation -->
- [x] Measure retained files: `src/erp_agent_os/adapters.py` (63) +
  `tests/test_fake_erp.py` (41) = 104 additions, below 400.
  <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → already formatted; `mypy src` → no issues found in 3 source files.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- Versioned skill contract (strict models, lifecycle transitions, focused
  tests) is the next SDD change; it may treat this adapter's
  model/operation shape as an execution-target reference.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the adapter diff, reliability as
  dominant lens, 104-line measurement as scope boundary.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns skill-contract planning before any
  scope expansion. <!-- sdd-owner: parent -->
