# Design: Dataset schema and minimal scaffold (work unit 1)

## Boundary

This change contains only `pyproject.toml`, `src/erp_agent_os/__init__.py`, `src/erp_agent_os/dataset.py`, and `tests/test_dataset.py`. It uses Python 3.12, Pydantic v2, and pytest. The measured implementation/test/scaffold total is 188 added lines, below the 400-line budget.

## Dataset contract

`dataset.py` exposes `DATASET_SCHEMA_VERSION = "1.0"`; strict frozen Pydantic models; `DatasetSplit`, `RiskClass`, `CaseLabel`, and `ExpectedDecision` enums; `BenchmarkCase`; `SplitPlan`; and pure `validate_case_groups`.

Every case and plan accepts only schema version `1.0`. Cases require all approved annotations, nonblank identifier/text fields, an explicit non-null `expected_skill` (including `sin_skill/abstención`), explicit `error_type`, and a label set where `NORMAL` occurs iff neither abnormal label occurs. `NOISE` and `ADVERSARIAL` may overlap. Split counts are exactly 240/120/120 and a paraphrase group may not cross splits.

## TDD evidence retained

The dataset sequence remains: RED missing dataset import; GREEN 4 tests passed; TRIANGULATE 5 tests passed including overlap/rejection; REFACTOR reran 5 passing tests with the shared case builder retained as the single test fixture source.

## Deferred follow-on

FakeERP and skills are deliberately absent. A new SDD change must create their specs/tasks and implement FakeERP before the skill lifecycle contract. No runtime, policy, persistence, services, generated data, or external ERP behavior is introduced here.
