# Tasks: Integrate System C end to end (work unit 9, closes P5.4)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 249 (1 new source + 1 test + audit extension) |
| 400-line budget risk | Low |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_system_c.py` written against nonexistent
  `erp_agent_os.system_c`. Evidence: `python -m pytest
  tests/test_system_c.py` → `ModuleNotFoundError: No module named
  'erp_agent_os.system_c'` (collection error). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/system_c.py`
  (`SystemC`, `SystemCResult`) and extend `src/erp_agent_os/audit.py`
  with `AbstentionEvent`/`record_abstention`/`abstentions`. Evidence:
  `python -m pytest tests/test_system_c.py tests/test_audit.py` → 11
  passed. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Independent cases — missing-field abstention,
  no-confident-candidate abstention, inactive-skill DENY still audited,
  repeated idempotency key through the full path, and R2-approval-grants-
  ALLOW. Evidence: same 11-test run, all pass. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Line-length/format fixes in `system_c.py` and
  `test_system_c.py`; no semantic change. Evidence: `python -m pytest` →
  61 passed (full suite). <!-- sdd-owner: implementation -->
- [x] Measure retained diff: `system_c.py` (82) + `test_system_c.py`
  (145) + `audit.py` net addition (109 - 87 = 22) = 249, below 400.
  <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted; `mypy src` → no issues found in 11 source files.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- API layer (P6.1) calling `SystemC.handle` per HTTP request.
- Retry/timeout consumption of `SkillDefinition.execution.max_retries`
  (needs transient-failure classification, not yet built).
- Embeddings/hybrid ranking remains a separate, parallel in-progress unit.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the System C diff, reliability as
  dominant lens, 249-line measurement as scope boundary.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns the API layer before any scope
  expansion. <!-- sdd-owner: parent -->
