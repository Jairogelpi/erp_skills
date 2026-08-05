# Apply progress: dataset schema and scaffold (work unit 1)

## Status

- The user selected the physical split after the prior combined slice measured 448 lines.
- Strict TDD remains active; all retained implementation tasks are visibly checked in `tasks.md`.
- Work unit 1 measures **188 added lines**, below the 400-line budget. No commit was created.

## Retained files

- `pyproject.toml`
- `src/erp_agent_os/__init__.py`
- `src/erp_agent_os/dataset.py`
- `tests/test_dataset.py`
- dataset-only SDD artifacts under this change

## Removed from this change

- `src/erp_agent_os/adapters.py`
- `src/erp_agent_os/skills.py`
- `tests/test_fake_erp.py`
- `tests/test_skills.py`
- `specs/fake-erp-adapter/spec.md`
- `specs/skill-contract/spec.md`

## TDD Cycle Evidence

| Area | Test file | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Dataset | `tests/test_dataset.py` | missing dataset import (expected) | 4 passed | 5 passed; overlap/rejection cases | 5 passed; shared builder retained |

## Verification evidence

- `python -m pytest tests/test_dataset.py` — prior focused evidence: 5 passed.
- `python -m pytest` — post-split evidence: 5 passed.
- Retained implementation/test/scaffold measurement: `16 + 1 + 102 + 69 = 188` additions.

## Deferred follow-on dependency

FakeERP and the versioned skill contract are removed from this change. A new SDD change must plan and implement FakeERP before the skill contract; no adapter, lifecycle, runtime, policy, persistence, service, generated-data, or external-ERP behavior remains in this work unit.

## Deferred lifecycle actions

- Parent-owned bounded reliability review of the 188-line dataset/scaffold diff.
- Parent-owned confirmation that a follow-on change owns the deferred FakeERP and skills work.
