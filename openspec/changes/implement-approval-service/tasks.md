# Tasks: Implement approval service (work unit 8, closes P6.3)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 83 (source + focused test) |
| 400-line budget risk | Low |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_approval.py` written against nonexistent
  `erp_agent_os.approval`. Evidence: `python -m pytest
  tests/test_approval.py` → `ModuleNotFoundError: No module named
  'erp_agent_os.approval'` (collection error). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/approval.py` with `Approval`,
  `ApprovalService.grant`/`is_valid`. Evidence: `python -m pytest
  tests/test_approval.py` → 5 passed. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Independent cases — expiry via mutable clock, scope
  isolation, non-positive TTL rejection, no-approval-ever-granted. Evidence:
  same 5-test run, all pass. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Line-length fix on the `__init__` signature; no
  semantic change. Evidence: `python -m pytest` → 55 passed (full suite).
  <!-- sdd-owner: implementation -->
- [x] Measure retained files: `approval.py` (42) + `test_approval.py` (41)
  = 83 additions, below 400. <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted; `mypy src` → no issues found in 10 source files.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- API layer (P6.1) wiring `grant`/`is_valid` into request handling and
  `policy.decide`'s `approval_granted` input.
- Persistence (P6.2) remains deferred.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the approval-service diff,
  reliability as dominant lens, 83-line measurement as scope boundary.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns API-layer wiring before any scope
  expansion. <!-- sdd-owner: parent -->
