# Tasks: Implement versioned skill contract (work unit 3)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 214 (source + focused test) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_skills.py` written against nonexistent
  `erp_agent_os.skills`. Evidence: `python -m pytest tests/test_skills.py` →
  `ModuleNotFoundError: No module named 'erp_agent_os.skills'` (collection
  error). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/skills.py` with
  `SkillDefinition`, `SkillState`, `ALLOWED_TRANSITIONS`, `transition`.
  Evidence: `python -m pytest tests/test_skills.py` → 7 passed.
  <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Independent cases for quarantine-from-every-state,
  the full six-state lifecycle path, and parametrized rejections (R4 risk,
  empty postconditions, malformed version). Evidence: same 7-test run, all
  pass. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Shared `_Model` strict/frozen base reused from the
  dataset module's pattern; `RiskClass` imported rather than redefined; no
  semantic change. Evidence: `python -m pytest` → 19 passed (full suite).
  <!-- sdd-owner: implementation -->
- [x] Measure retained files: `src/erp_agent_os/skills.py` (137) +
  `tests/test_skills.py` (77) = 214 additions, below 400.
  <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → already formatted; `mypy src` → no issues found in 4 source files.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- Runtime + policy engine (P4.3–P4.4): registered-handler execution,
  idempotency keys, postcondition verification, deny-by-default policy
  decisions. Consumes this contract's `execution`/`permissions`/
  `risk_class` fields; not implemented here.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the skill-contract diff, reliability
  as dominant lens, 214-line measurement as scope boundary.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns runtime/policy planning before any
  scope expansion. <!-- sdd-owner: parent -->
