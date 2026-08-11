# Proposal: Wire ERP-Skills-Bench v1 to System C execution (work unit 15, P8.1 groundwork)

## Intent

User-directed priority: "wiring de ejecución primero, API después." Take
the 480 generated cases and actually run them through the governed
system (`SystemC`) instead of leaving execution as a documented
placeholder. Depends on the completed catalog/intents/generator (units
11–13) and the adapter/runtime hardening this discovered was needed
(work unit 14).

## Scope

- `handlers.py`: one handler per catalog skill (12), wired to
  documented `FakeERPAdapter` model names.
- `bench_runner.py`: `run_case`/`run_all`/`summarize` — per case, an
  isolated `FakeERPAdapter`+`Runtime`+`TfidfRetriever`+`AuditStore`+
  `SystemC`, seeding whatever reference entity the skill needs (skipped
  for the deliberately-missing-reference adversarial category), executing
  via the case's own `expected_arguments` as a stand-in parsed proposal,
  and comparing actual vs. dataset `expected_decision`.
- `scripts/run_bench_wiring_report.py` → `data/bench_v1_wiring_report.json`.
- `docs/dataset-card.md` updated with the real match-rate findings.

## Non-goals

No real LLM-backed parser (uses `expected_arguments` as ground truth).
No input-schema/argument-range validation (RF-06/07, separate work). No
fixing the low ADVERSARIAL match rate — that gap is reported as a
finding, consistent with CLAUDE.md §35.18 ("se documenten resultados
negativos") and directly relevant to H4, not silently patched.

## Follow-on dependency

The API layer (roadmap P6.1–P6.2/P6.4) is next per the user's stated
order. A real parser call and input-schema validation are separate,
larger future units.

## Success criteria

All 480 cases execute without crashing; `summarize` reports exact
per-label totals (240/144/96); the ADVERSARIAL match-rate gap is
reported, not hidden, with a category-level breakdown
(`mismatch_by_error_type`); `python -m pytest` passes in full.

## Forecast and explicit budget exception

Hand-authored: `handlers.py` (139) + `bench_runner.py` (136) +
`test_handlers.py` (38) + `test_bench_runner.py` (112) +
`run_bench_wiring_report.py` (63) = **488 lines**, over the 400-line
budget — disclosed, same treatment as work unit 13. Splitting further
(e.g. handlers in one PR, runner in another) was considered and rejected:
`bench_runner.py`'s seeding/execution/comparison logic is meaningless to
review without the 12 handlers it drives, and the report script is a
five-line consumer of both — three PRs reviewing one coherent pipeline
would cost more reviewer context-switching than one 488-line PR with a
clear per-file breakdown.
