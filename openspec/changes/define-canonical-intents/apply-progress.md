# Apply progress: 24 canonical intents (work unit 12)

## Status

Complete; 297 added lines, below the 400-line budget. No commit created
by apply.

## Retained files

- `src/erp_agent_os/bench_intents.py`
- `tests/test_bench_intents.py`
- intents-only SDD artifacts under this change

## Verification evidence

- `python -m pytest tests/test_bench_intents.py` — 5 passed.
- `python -m pytest` — 85 passed (full suite at this point in the session).
- `ruff check` / `ruff format --check` — clean.
- Retained measurement: `265 + 32 = 297` additions.

## Honesty note

Authored alongside `bench_generator.py` in one session before being split
for reviewability; tests were written and run against the already-working
module (characterization coverage), not RED-first. See `tasks.md`.

## Deferred follow-on dependency

Formulation generation and split allocation — next SDD change.
