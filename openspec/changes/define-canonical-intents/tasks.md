# Tasks: Define 24 canonical intents (work unit 12)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 297 |
| 400-line budget risk | Low |
| Delivery strategy | single-pr |

## Implementation

- [x] Implement `src/erp_agent_os/bench_intents.py`: `IntentSpec`, slot
  pools, 24-entry `INTENTS` list (2 per catalog skill).
  <!-- sdd-owner: implementation -->
- [x] `tests/test_bench_intents.py` written and run against the completed
  module. Evidence: `python -m pytest tests/test_bench_intents.py` → 5
  passed. <!-- sdd-owner: implementation -->

**Honesty note on TDD cycle:** `bench_intents.py` and
`bench_generator.py` (next unit) were authored together as one working
session before being split into separate SDD change records for
reviewability; `test_bench_intents.py` was written and run against the
already-implemented module rather than RED-first against an absent one.
This is characterization coverage of already-correct, already-tested
(via `test_bench_generator.py`) behavior, not first-implementation TDD —
recorded honestly rather than reconstructing a RED step that didn't
happen, consistent with the property-tests unit's precedent.

- [x] Full-suite regression: `python -m pytest` → 85 passed (at the time
  of this unit). <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted. <!-- sdd-owner: implementation -->
- [x] Measure retained files: `bench_intents.py` (265) +
  `test_bench_intents.py` (32) = 297 additions, below 400.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

Formulation generation (styles, noise, adversarial categories, split
allocation) — next SDD change.

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the 297-line intents diff.
  <!-- sdd-owner: parent -->
