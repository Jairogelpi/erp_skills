# Design: measurement and paired experiment

## Alternatives considered

- **Group whole intents into one split** (all 20 formulations of an
  intent to a single partition): rejected. It removes leakage but also
  removes all 24 intents from the test set except 6, making per-intent
  analysis impossible and turning the study into unseen-intent
  generalization — not what §21's "formulación vista o no vista"
  segmentation asks for. Making formulations genuinely distinct by
  construction achieves non-leakage without that cost.
- **Keep `validate_case_groups` as the leakage gate**: rejected. It is
  vacuous under size-1 groups. Kept for contract compatibility, but the
  real gate is now `validate_no_split_leakage`, which is tested against a
  planted leak so it cannot silently become vacuous again.
- **Score System A on final-state equivalence only** (ignore action
  identity): rejected as too generous — it would erase the "selects the
  right action" conjunct §20 explicitly requires. Mapping the generic
  tool to the equivalent skill keeps the conjunct meaningful while giving
  A credit for the right *kind* of action.
- **Give System A the `state` field so its records pass postconditions**:
  rejected — that would be manufacturing the result. A's records lack
  business state precisely because it has no skill contract; that is the
  effect under study, and `docs/results.md` demonstrates the attribution
  with a side-by-side of what A and B write for the same input.
- **Run with a real LLM now**: not possible without credentials, and
  credentials must never be committed. Holding the selector constant is
  the honest alternative, labelled `is_confirmatory_run: false`.

## Risks

- **A as a strawman.** Its STSR of 0 is near-deterministic given generic
  CRUD. Stated in `results.md`; the informative contrast is C − B.
- **Circularity in postconditions.** B and C pass partly because their
  handlers write exactly what the postconditions check. Mitigated by the
  postconditions coming from the §15 skill contract, which predates the
  handlers, but not eliminated. Declared in `results.md`.
- **H3 is undiscriminable** with a deterministic selector; reported as a
  null result rather than as evidence for C.

## Test strategy

`test_bench_generator.py`: uniqueness, leakage, planted-leak detection.
`test_metrics.py`: each STSR conjunct fails independently; false
allow/block on constructed records; MRR at rank 3; abstention does not
inflate selective accuracy. `test_experiment.py`: exact 1.080 count,
3 repetitions per (case, system), state isolation, seed determinism, and
that a stub selector is marked non-confirmatory.
