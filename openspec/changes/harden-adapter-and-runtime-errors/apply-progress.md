# Apply progress: adapter/runtime error handling (work unit 14)

## Status

Complete; 90 added lines, below the 400-line budget. No commit created
by apply.

## Retained files

- `src/erp_agent_os/adapters.py` (extended)
- `src/erp_agent_os/runtime.py` (extended)
- `tests/test_fake_erp.py` (extended)
- `tests/test_runtime.py` (extended)
- hardening-only SDD artifacts under this change

## Verification evidence

- `python -m pytest tests/test_fake_erp.py tests/test_runtime.py` — 16 passed.
- `python -m pytest` — 102 passed (full suite at this point in the session).
- `ruff check` / `ruff format --check` — clean.
- `mypy src` — no issues found.
- Retained measurement: `13 + 12 + 33 + 32 = 90` additions.

## Deferred follow-on dependency

Input-schema/argument-range validation (RF-06/07) — separate, larger
scope.
