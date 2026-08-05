# Proposal: Audit the measurement instrument and freeze the protocol (work unit 22)

## Intent

Before building further on the experimental results, audit the scorer
itself and close the freeze gap. Triggered by the question "are we sure
we are not dragging anything broken forward?" — answered by checking
rather than by reassurance.

## Defects found

1. **Conjunct 5 of STSR ("no side effects") was vacuous.** It returned
   `True` unconditionally for every permitted execution and did not fail
   once across 1.080 observations. STSR was effectively a three-way
   conjunction presented as five.
2. **Conjunct 4 ("expected state") duplicated conjunct 1** for
   non-executing cases: both re-checked the decision, so "expected final
   state" measured no state at all.
3. **The protocol was never frozen**, although §19/P9.1 requires it. Any
   edit to the generator or catalog would have silently invalidated every
   published number.
4. The monotonicity property test did not cover the `findings` argument
   added to `policy.decide` in work unit 18.

## Scope

- `_side_effect_free` now compares every model except the task's target
  model; detects 3 real System B observations writing into a foreign
  model.
- Conjunct 4 now verifies the store is untouched for refusals, via a new
  `ExecutionRecord.state_unchanged`.
- `freeze.py` + `data/freeze_manifest.json`: hashes of the test split,
  full dataset, catalog and seed. `make verify-freeze` runs in CI.
- Two new property tests: a finding never loosens a decision; a blocking
  finding always denies.
- Regression tests so a vacuous conjunct cannot return.

## Result

**The numbers did not change** (STSR A 0.000 / B 0.333 / C 0.700). That
is evidence the conclusions were robust — not evidence the fixes were
unnecessary, since the metric was not measuring what it declared.

## Success criteria

Every STSR conjunct can be shown to fail on a constructed input. The
freeze detector reports drift for each of its six components when
tampered with individually. CI fails on drift.
