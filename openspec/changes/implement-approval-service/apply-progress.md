# Apply progress: approval service (work unit 8, closes P6.3)

## Status

Strict TDD complete; all tasks checked in `tasks.md`. 83 added lines,
below the 400-line budget. No commit created by apply.

## Retained files

- `src/erp_agent_os/approval.py`
- `tests/test_approval.py`
- approval-service-only SDD artifacts under this change

## TDD Cycle Evidence

| Area | Test file | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Approval service | `tests/test_approval.py` | `ModuleNotFoundError: erp_agent_os.approval` | 5 passed | 5 passed; expiry/scope-isolation/TTL/no-approval cases | 5 passed; line-length fix only |

## Verification evidence

- `python -m pytest tests/test_approval.py` — 5 passed.
- `python -m pytest` — 55 passed (full suite through work unit 8).
- `ruff check` — all checks passed.
- `ruff format --check` — all files formatted.
- `mypy src` — no issues found in 10 source files.
- Retained measurement: `42 + 41 = 83` additions.

## Deferred follow-on dependency

API layer (P6.1) wiring `grant`/`is_valid` into request handling; DB
persistence (P6.2).

## Deferred lifecycle actions

- Parent-owned bounded reliability review of the 83-line diff.
- Parent-owned confirmation that the follow-on change owns API-layer
  wiring.
