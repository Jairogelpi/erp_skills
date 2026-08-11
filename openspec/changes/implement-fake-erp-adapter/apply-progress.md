# Apply progress: FakeERPAdapter (work unit 2)

## Status

Strict TDD complete; all tasks checked in `tasks.md`. 104 added lines,
below the 400-line budget. No commit created by apply.

## Retained files

- `src/erp_agent_os/adapters.py`
- `tests/test_fake_erp.py`
- FakeERP-only SDD artifacts under this change

## TDD Cycle Evidence

| Area | Test file | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| FakeERP | `tests/test_fake_erp.py` | `ModuleNotFoundError: erp_agent_os.adapters` | 5 passed | 5 passed; allowlist/unknown-record/post-snapshot-mutation cases | 5 passed; shared `_require_model` guard |

## Verification evidence

- `python -m pytest tests/test_fake_erp.py` — 5 passed.
- `python -m pytest` — 12 passed (full suite, dataset + FakeERP).
- `ruff check` — all checks passed.
- `ruff format --check` — already formatted.
- `mypy src` — no issues found in 3 source files.
- Retained measurement: `63 + 41 = 104` additions.

## Deferred follow-on dependency

Skill contract (versioned schema, lifecycle transitions) is the next SDD
change. No runtime, policy, persistence, service, or external-ERP behavior
is retained in this work unit.

## Deferred lifecycle actions

- Parent-owned bounded reliability review of the 104-line adapter diff.
- Parent-owned confirmation that the follow-on change owns skill-contract
  planning.
