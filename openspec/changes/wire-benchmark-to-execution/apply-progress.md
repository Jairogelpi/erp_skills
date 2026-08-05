# Apply progress: wire benchmark to System C execution (work unit 15)

## Status

Complete; all tasks checked in `tasks.md`. **488 hand-authored added
lines — over the 400-line budget, disclosed and justified in
`proposal.md`/`tasks.md`.** No commit created by apply.

## Retained files

- `src/erp_agent_os/handlers.py`
- `src/erp_agent_os/bench_runner.py`
- `tests/test_handlers.py`
- `tests/test_bench_runner.py`
- `scripts/run_bench_wiring_report.py`
- `data/bench_v1_wiring_report.json` (generated, flagged separately)
- `docs/dataset-card.md` (updated)
- wiring-only SDD artifacts under this change

## TDD Cycle Evidence

| Area | Test file | RED | GREEN | Notes |
|---|---|---|---|---|
| Handlers | `tests/test_handlers.py` | `ModuleNotFoundError: erp_agent_os.handlers` | 5 passed | — |
| Bench runner | `tests/test_bench_runner.py` | `ModuleNotFoundError: erp_agent_os.bench_runner` | Uncaught `KeyError` on first real run (retrieval misrouted a query) | Root-caused and fixed via work unit 14's `Runtime` hardening, then 6 passed |

## Verification evidence

- `python -m pytest tests/test_handlers.py tests/test_bench_runner.py` — 11 passed.
- `python -m pytest` — 102 passed (full suite through work unit 15).
- `ruff check` / `ruff format --check` — clean.
- `mypy src` — no issues found in 17 source files.
- `python scripts/run_bench_wiring_report.py` — 480/480 cases executed
  without crashing; report written to `data/bench_v1_wiring_report.json`.
- Retained hand-authored measurement: `139 + 136 + 38 + 112 + 63 = 488`
  (over 400, disclosed).

## Honest findings (not hidden — full detail in docs/dataset-card.md)

- NORMAL 87.5%, NOISE 72.2%, ADVERSARIAL 17.7% match rate against the
  dataset's ideally-correct `expected_decision`.
- ADVERSARIAL gap: no prompt-injection/range/bulk-scope/irreversible-
  operation/permission-text detection exists in `policy.py` yet — exactly
  what H4 is meant to measure once the confirmatory experiment runs.
- CLARIFY vs. ABSTAIN: the system has no distinct clarification signal;
  all 24 `missing_required_field` NOISE cases mismatch for this reason.
- 46 NORMAL/NOISE mismatches from TF-IDF occasionally misrouting short
  queries.
- 52/480 executions hit a caught `handler_error`.

## Deferred follow-on dependency

API layer (user-directed next priority); real LLM parser; input-schema
validation; a `CLARIFY` decision path.

## Deferred lifecycle actions

- Parent-owned bounded reliability review of the 488-line diff, with
  explicit acknowledgment of the budget exception.
- Parent-owned confirmation the ADVERSARIAL-gap finding is carried into
  the memoria's honest-limitations discussion.
