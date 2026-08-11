# Tasks: Populate the 12-skill catalog (work unit 11)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 195 |
| 400-line budget risk | Low |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_catalog.py` written against nonexistent
  `erp_agent_os.catalog`. Evidence: `python -m pytest tests/test_catalog.py`
  → `ModuleNotFoundError: No module named 'erp_agent_os.catalog'`
  (collection error). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/catalog.py` with 12
  `SkillDefinition` entries. Evidence: `python -m pytest
  tests/test_catalog.py` → 5 passed. <!-- sdd-owner: implementation -->
- [x] Full-suite regression: `python -m pytest` → 72 passed (at the time
  of this unit). <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted; `mypy src` → no issues found. <!-- sdd-owner: implementation -->
- [x] Measure retained files: `catalog.py` (169) + `test_catalog.py` (26)
  = 195 additions, below 400. <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

24 canonical intents (2 per skill) — next SDD change.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the 195-line catalog diff.
  <!-- sdd-owner: parent -->
