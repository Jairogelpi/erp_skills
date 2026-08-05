# Tasks: Freeze ERP-Skills-Bench dataset schema (work unit 1)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 188 (scaffold, source, focused test) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | This is work unit 1 of the prior oversized slice. |
| Delivery strategy | single-pr |
| Chain strategy | size-exception avoided by split |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception avoided by split
400-line budget risk: Low

## Planning dependency

The approved dataset specification is present at `specs/erp-skills-bench/spec.md`. FakeERP and skill-contract work is explicitly deferred to a follow-on SDD change; their implementation, tests, and specs are not retained here.

## Implementation (strict TDD)

- [x] **RED:** Create `pyproject.toml`, `src/erp_agent_os/__init__.py`, and failing `tests/test_dataset.py` tests for a complete `BenchmarkCase`, explicit `sin_skill/abstención`, missing/inconsistent annotations, fixed `SplitPlan`, and group leakage. Evidence: `python -m pytest tests/test_dataset.py` failed only for the missing dataset import. <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/dataset.py` with frozen `1.0` strict models, required annotations, label invariant, allocation validation, and pure group-leakage validation. Evidence: 4 focused tests passed. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Add independent `NOISE` + `ADVERSARIAL` valid and `NORMAL` + `NOISE` invalid cases. Evidence: 5 focused tests passed. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Retain the shared dataset test builder as the single fixture source without changing public schema semantics. Evidence: 5 focused tests passed. <!-- sdd-owner: implementation -->
- [x] Measure retained `pyproject.toml`, `src/erp_agent_os/{__init__,dataset}.py`, and `tests/test_dataset.py`: 188 additions, below 400. <!-- sdd-owner: implementation -->
- [x] Run `python -m pytest`; evidence: 5 passed. Confirm no FakeERP, skill contract, external ERP, generated data, services, runtime, policy, or specification artifact outside the dataset work unit was retained. <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- FakeERP adapter (protocol, synthetic state restoration, operation allowlist, and focused tests) is deferred to a new SDD change.
- Versioned skill contract (strict models, lifecycle transitions, and focused tests) is deferred until that follow-on has planned/implemented FakeERP.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the dataset/scaffold implementation diff, with reliability as the dominant lens and the 188-line measurement as the scope boundary. <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on SDD change owns FakeERP and skill-contract planning before any scope expansion. <!-- sdd-owner: parent -->
