# Tasks: Implement deterministic runtime and policy engine (work unit 4)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 310 (2 source + 2 focused test files) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_policy.py` and `tests/test_runtime.py` written
  against nonexistent `erp_agent_os.policy`/`erp_agent_os.runtime`.
  Evidence: `python -m pytest tests/test_policy.py tests/test_runtime.py` →
  `ModuleNotFoundError: No module named 'erp_agent_os.policy'` (collection
  error on both files). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/policy.py` (`decide`,
  `PolicyOutcome`, `PolicyDecision`) and `src/erp_agent_os/runtime.py`
  (`Runtime`, `ExecutionResult`, `UnregisteredHandlerError`). Evidence:
  `python -m pytest tests/test_policy.py tests/test_runtime.py` → 10
  passed. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Independent cases — inactive-skill denial regardless
  of role, R2 vs. R3 approval-outcome divergence (ALLOW vs. SIMULATE),
  DENY-never-calls-handler via a call-counting handler, unregistered
  handler raising, idempotent replay, and a failing postcondition check.
  Evidence: same 10-test run, all pass. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Line-length fix in `runtime.py`'s cached-result branch;
  no semantic change. Evidence: `python -m pytest` → 29 passed (full
  suite). <!-- sdd-owner: implementation -->
- [x] Measure retained files: `policy.py` (71) + `runtime.py` (79) +
  `test_policy.py` (59) + `test_runtime.py` (101) = 310 additions, below
  400. <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted; `mypy src` → no issues found in 6 source files.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- Audit store (append-only trace, correlation IDs) and approval service
  (actor/scope/expiration) are the next required pieces (roadmap P4.5,
  P6.3) before API/retrieval work.
- Mapping `SkillDefinition.postconditions` string identifiers to executable
  checks, and deriving idempotency keys per the CLAUDE.md §25 hash formula,
  are deferred to the parser/API layer that will call this runtime.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the runtime/policy diff, reliability
  as dominant lens, 310-line measurement as scope boundary.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns audit-store planning before any
  scope expansion. <!-- sdd-owner: parent -->
