# Apply progress: Systems A and B baselines (work unit 17)

## Status

Complete; 293 added lines, below the 400-line budget. No commit created
by apply (committed separately per the session's git workflow).

## Retained files

- `src/erp_agent_os/llm_client.py`
- `src/erp_agent_os/system_a.py`
- `src/erp_agent_os/system_b.py`
- `tests/test_llm_client.py`, `tests/test_system_a.py`, `tests/test_system_b.py`
- systems-A/B-only SDD artifacts under this change

## Verification evidence

- `python -m pytest tests/test_llm_client.py tests/test_system_a.py tests/test_system_b.py` — 9 passed.
- `python -m pytest` — 118 passed (full suite through work unit 17).
- `ruff check` / `ruff format --check` — clean.
- `mypy src` — no issues found in 21 source files.

## Deferred follow-on dependency

Real `LLMClient` (provider credentials required), A/B/C comparison
runner, frozen-manifest confirmatory protocol.
