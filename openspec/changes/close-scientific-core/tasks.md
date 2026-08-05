# Tasks: Close the scientific core (work unit 21)

## Implementation

- [x] Diagnose leakage: 10 identical texts in DEVELOPMENT and FINAL_TEST,
  19 crossing splits. Root cause identified as the tautological group
  check. <!-- sdd-owner: implementation -->
- [x] Widen slot pools to 24 values; deterministic non-repeating slot
  assignment; replace duplicated style; lengthen truncation. Evidence:
  480/480 unique texts, 0 crossings. <!-- sdd-owner: implementation -->
- [x] Add `validate_no_split_leakage` + planted-leak test proving it is
  not vacuous. Evidence: `tests/test_bench_generator.py` → 11 passed.
  <!-- sdd-owner: implementation -->
- [x] Implement `postconditions.py`; verify 12/12 catalog skills resolve.
  <!-- sdd-owner: implementation -->
- [x] Implement `metrics.py` (STSR, security, retrieval, stability).
  Evidence: `tests/test_metrics.py` → 12 passed.
  <!-- sdd-owner: implementation -->
- [x] Implement `experiment.py` + `scripts/run_experiment.py`. Evidence:
  1.080 observations; `tests/test_experiment.py` → 5 passed.
  <!-- sdd-owner: implementation -->
- [x] Find and fix two comparison biases (System A skill-identity
  scoring; English tool descriptions vs Spanish corpus) **before**
  publishing any number. <!-- sdd-owner: implementation -->
- [x] Write `docs/results.md` answering the research question with the
  scope caveat, the A-strawman limitation, and the circularity risk
  stated. <!-- sdd-owner: implementation -->
- [x] Wire `make experiment` into CI with artifact upload.
  <!-- sdd-owner: implementation -->
- [x] Quality: `python -m pytest` → 176 passed; `ruff check` /
  `ruff format --check` clean; `mypy src` → 28 files, no issues.
  <!-- sdd-owner: implementation -->

## Deferred

Real LLM client (credentials); token/latency/cost (H2/H8); automatic
traceability scoring (H7); human annotation for kappa; memoria, demo,
dashboard, video.

## Parent lifecycle actions

- [ ] Bounded review of the measurement layer, with attention to whether
  the STSR conjuncts are fair to all three systems.
  <!-- sdd-owner: parent -->
