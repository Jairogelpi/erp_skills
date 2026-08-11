# Apply progress: core safety property tests (work unit 6, closes P4.6)

## Status

Complete; all tasks checked in `tasks.md`. 184 added lines, below the
400-line budget. No commit created by apply.

## Retained files

- `pyproject.toml` (added `hypothesis==6.123.7` to dev deps)
- `uv.lock` (relocked: `attrs`, `hypothesis`, `sortedcontainers`)
- `tests/test_properties.py`
- property-test-only SDD artifacts under this change

## Verification evidence

- `python -c "import hypothesis; print(hypothesis.__version__)"` → `6.123.7`.
- `python -m pytest tests/test_properties.py` — 6 passed.
- `python -m pytest` — 40 passed (full suite: dataset + FakeERP + skills +
  policy + runtime + audit + properties).
- `ruff check .` — all checks passed.
- `ruff format --check .` — all files formatted.
- `mypy src` — no issues found in 7 source files.
- Retained measurement: `git diff --stat -- pyproject.toml uv.lock` → 34
  insertions; `test_properties.py` → 150 lines. `34 + 150 = 184`.

## Mutation-testing attempt (not completed)

An attempt was made to demonstrate a property catching an injected defect
by temporarily disabling `policy.py`'s role check and re-running
`tests/test_properties.py`. The harness's action classifier denied the
test-execution step against the mutated file; the source edit was reverted
immediately without any test run against the mutated state. `git status`
and `python -m pytest` (full suite, 40 passed) confirm `policy.py` matches
its pre-mutation, already-verified state. This gap is recorded here rather
than claimed as done.

## Deferred follow-on dependency

Phase 4 (núcleo determinista) closes with this unit. Phase 5
(parser/retrieval) or phase 6 (approval service) is next.

## Deferred lifecycle actions

- Parent-owned bounded reliability review of the 184-line property-test
  diff.
- Parent-owned confirmation of phase 4 closure and next-phase scope.
