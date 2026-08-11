# Tasks: Audit the measurement instrument and freeze (work unit 22)

## Implementation

- [x] Audit STSR conjunct-by-conjunct across 1.080 observations; find
  conjunct 5 never failing and conjunct 4 duplicating conjunct 1.
- [x] Fix conjunct 5 to compare non-target models; verify it now detects
  3 real System B observations.
- [x] Fix conjunct 4 to check `state_unchanged` for refusals.
- [x] Re-run the experiment: results identical, confirming robustness.
- [x] Implement `freeze.py` + `scripts/freeze_protocol.py`; write
  `data/freeze_manifest.json`.
- [x] Prove drift detection by tampering with all six components.
- [x] Wire `make verify-freeze` into CI.
- [x] Add property tests for `findings` monotonicity.
- [x] Add regression tests against vacuous conjuncts.
- [x] Correct the stale/incorrect claims in `docs/dataset-card.md`,
  `openspec/project-context.md`, `README.md` and the roadmap.
- [x] Quality: 188 passed, 96% coverage, ruff clean, mypy clean
  (29 files; one real type error fixed by typing, not silencing).

## Deferred

Extending the freeze manifest to cover prompts and provider config, once
a real LLM client exists.
