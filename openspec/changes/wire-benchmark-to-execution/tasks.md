# Tasks: Wire ERP-Skills-Bench v1 to System C execution (work unit 15)

## Review Workload Forecast

| Field | Value |
|---|---|
| Hand-authored diff | 488 lines — **over the 400-line budget, disclosed** |
| Split considered and rejected | see proposal.md's explicit exception rationale |
| Delivery strategy | single-pr, with the exception called out for review |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_handlers.py` written against nonexistent
  `erp_agent_os.handlers`. Evidence: `python -m pytest
  tests/test_handlers.py` → `ModuleNotFoundError` (collection error).
  <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/handlers.py` (12 handlers).
  Evidence: `python -m pytest tests/test_handlers.py` → 5 passed.
  <!-- sdd-owner: implementation -->
- [x] **RED:** `tests/test_bench_runner.py` written against nonexistent
  `erp_agent_os.bench_runner`. Evidence: `ModuleNotFoundError` (collection
  error). <!-- sdd-owner: implementation -->
- [x] **GREEN → discovered failure → fix:** first `bench_runner.py`
  implementation crashed with an uncaught `KeyError` because TF-IDF
  retrieval matched the wrong skill for a short query and the mismatched
  handler tried to read an argument that didn't exist — root cause fixed
  in work unit 14 (`Runtime.execute` now catches `KeyError`), not papered
  over here. Evidence: `python -m pytest tests/test_bench_runner.py` → 6
  passed after the fix. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Iterated two test assumptions that were
  empirically wrong on first write (an R2 skill correctly does *not*
  mutate without approval; the "unknown-record" test needed a
  deterministically-constructed case rather than relying on the
  generator's category rotation landing on a specific skill) — both
  fixed by correcting the test, not the implementation, once the actual
  (correct) system behavior was understood. <!-- sdd-owner: implementation -->
- [x] Full-suite regression: `python -m pytest` → 102 passed.
  <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed (after manual
  line-length fixes across 5 files — `ruff format` alone couldn't
  shorten several unbreakable-by-format expressions); `ruff format
  --check` → all formatted; `mypy src` → no issues found in 17 source
  files. <!-- sdd-owner: implementation -->
- [x] Run all 480 cases: `python scripts/run_bench_wiring_report.py` →
  `data/bench_v1_wiring_report.json` written; NORMAL 87.5%, NOISE 72.2%,
  ADVERSARIAL 17.7% match rates; 52/480 `handler_error`s.
  <!-- sdd-owner: implementation -->
- [x] `docs/dataset-card.md` updated: "Execution wiring (done)" section
  with the real numbers and four honest findings (ADVERSARIAL gap,
  CLARIFY-vs-ABSTAIN gap, TF-IDF misrouting, handler_error count); no
  claim of a fix for what wasn't fixed. <!-- sdd-owner: implementation -->
- [x] Measure and disclose: 488 hand-authored lines (over 400 — see
  proposal.md exception). <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- API layer (roadmap P6.1–P6.2/P6.4) — user-stated next priority.
- Real LLM-backed parser call (replacing `expected_arguments`-as-ground-
  truth).
- Input-schema/argument-range validation (RF-06/07) to close the
  ADVERSARIAL gap this unit's report surfaced.
- A `CLARIFY` decision path distinct from `ABSTAIN`.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the 488-line hand-authored diff —
  **flagged as exceeding the 400-line budget**; review should weigh the
  proposal.md rationale for not splitting further.
  <!-- sdd-owner: parent -->
- [ ] Confirm the ADVERSARIAL-gap finding is carried into the memoria's
  honest-limitations discussion (CLAUDE.md §35.18), not silently dropped.
  <!-- sdd-owner: parent -->
