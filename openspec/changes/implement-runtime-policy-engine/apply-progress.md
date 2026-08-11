# Apply progress: deterministic runtime and policy engine (work unit 4)

## Status

Strict TDD complete; all tasks checked in `tasks.md`. 310 added lines,
below the 400-line budget. No commit created by apply.

## Retained files

- `src/erp_agent_os/policy.py`
- `src/erp_agent_os/runtime.py`
- `tests/test_policy.py`
- `tests/test_runtime.py`
- runtime/policy-only SDD artifacts under this change

## TDD Cycle Evidence

| Area | Test file | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Policy + runtime | `tests/test_policy.py`, `tests/test_runtime.py` | `ModuleNotFoundError: erp_agent_os.policy` | 10 passed | 10 passed; state/risk-tier/DENY-no-call/unregistered/idempotency/postcondition-failure cases | 10 passed; `runtime.py` line-length fix only |

## Verification evidence

- `python -m pytest tests/test_policy.py tests/test_runtime.py` — 10 passed.
- `python -m pytest` — 29 passed (full suite: dataset + FakeERP + skills +
  policy + runtime).
- `ruff check` — all checks passed.
- `ruff format --check` — all files formatted.
- `mypy src` — no issues found in 6 source files.
- Retained measurement: `71 + 79 + 59 + 101 = 310` additions.

## Deferred follow-on dependency

Audit store and approval service are the next SDD change (roadmap P4.5,
P6.3). Postcondition-string-to-callable mapping and the §25 idempotency-key
hash derivation are deferred to the parser/API layer.

## Deferred lifecycle actions

- Parent-owned bounded reliability review of the 310-line runtime/policy
  diff.
- Parent-owned confirmation that the follow-on change owns audit-store
  planning.
