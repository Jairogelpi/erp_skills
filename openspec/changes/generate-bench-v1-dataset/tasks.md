# Tasks: Generate ERP-Skills-Bench v1 (work unit 13)

## Review Workload Forecast

| Field | Value |
|---|---|
| Hand-authored diff | 525 lines — **over the 400-line budget, disclosed** |
| Generated data | `data/bench_v1.jsonl`, 480 lines, flagged separately |
| Split considered and rejected | see proposal.md's explicit exception rationale |
| Delivery strategy | single-pr, with the exception called out for review |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_bench_generator.py` written against
  nonexistent `erp_agent_os.bench_generator`. Evidence: `python -m
  pytest tests/test_bench_generator.py` → `ModuleNotFoundError: No
  module named 'erp_agent_os.bench_generator'` (collection error).
  <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/bench_generator.py`
  (`generate_cases`, style tables, `_apply_adversarial`). Evidence:
  `python -m pytest tests/test_bench_generator.py` → 8 passed on first
  run (all 8 assertions — exact counts, split, leakage, determinism,
  catalog/abstention consistency, unique ids, 24-intent coverage — held
  without further iteration). <!-- sdd-owner: implementation -->
- [x] Full-suite regression: `python -m pytest` → 80 passed (at the time
  of this unit, before the intents-only test file was added
  separately). <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed (after formatting
  fixes for line length); `ruff format --check` → all formatted; `mypy
  src` → no issues found in 15 source files. <!-- sdd-owner: implementation -->
- [x] Export: `scripts/export_bench_v1.py` → `data/bench_v1.jsonl`.
  Evidence: `python scripts/export_bench_v1.py` → "wrote 480 cases";
  `wc -l data/bench_v1.jsonl` → 480. <!-- sdd-owner: implementation -->
- [x] `docs/dataset-card.md` written: composition table, split
  methodology, explicit known limitations (no execution wiring, no
  second annotator), regeneration command. <!-- sdd-owner: implementation -->
- [x] Measure and disclose: hand-authored 525 lines (over 400 — see
  proposal.md exception); generated data 480 lines (flagged separately).
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- Wiring these cases to real `SystemC`/`FakeERPAdapter` execution
  (roadmap P8.1–P8.3) — `initial_state`/`expected_final_state` remain
  placeholders until then.
- Second-annotator review and Cohen's kappa (CLAUDE.md §17, §21) — a
  pending human step, not producible by this session alone.
- A/B/C systems and the experiment runner (phase 8–9).

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the 525-line hand-authored diff —
  **flagged as exceeding the 400-line budget**; review should weigh the
  proposal.md rationale for not splitting further.
  <!-- sdd-owner: parent -->
- [ ] Confirm second-annotator review is scheduled as a human step before
  the dataset is treated as validation-ready per CLAUDE.md §17.
  <!-- sdd-owner: parent -->
