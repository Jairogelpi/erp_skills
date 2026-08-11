# Tasks: Implement append-only audit store (work unit 5)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 183 (source + focused test) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_audit.py` written against nonexistent
  `erp_agent_os.audit`. Evidence: `python -m pytest tests/test_audit.py` →
  `ModuleNotFoundError: No module named 'erp_agent_os.audit'` (collection
  error). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/audit.py` with `AuditEvent`,
  `AuditStore.record`/`events`, and `_redact`. Evidence: `python -m pytest
  tests/test_audit.py` → 5 passed. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Independent cases for correlation-id filtering,
  redaction masking one key while preserving another, returned-tuple
  independence from later mutation, and append-order across two records.
  Evidence: same 5-test run, all pass. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Removed unused `field` import; line-length fix in the
  test's `record()` call; no semantic change. Evidence: `python -m pytest`
  → 34 passed (full suite). <!-- sdd-owner: implementation -->
- [x] Measure retained files: `src/erp_agent_os/audit.py` (87) +
  `tests/test_audit.py` (96) = 183 additions, below 400.
  <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted; `mypy src` → no issues found in 7 source files.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- Property-based tests (roadmap P4.6) covering R4-never-executes,
  no-double-mutation, disallowed-field-never-reaches-adapter,
  every-terminal-execution-has-an-audit-event, and monotonic policy
  restrictiveness are the next SDD change.
- Approval service (actor/scope/expiration, roadmap P6.3) and
  PostgreSQL persistence (roadmap P6.2) remain deferred.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the audit-store diff, reliability
  as dominant lens, 183-line measurement as scope boundary.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns the property-test suite before any
  scope expansion. <!-- sdd-owner: parent -->
