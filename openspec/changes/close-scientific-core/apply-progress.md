# Apply progress: close the scientific core (work unit 21)

## Status

Complete. §35 criteria 1-9 addressed; criteria 1, 2, 4, 5, 6, 7, 8 move
from ❌ to ✅ with measured evidence, criterion 3 (dataset) from ⚠️ to ✅
after the leakage fix, criterion 9 was already ✅.

## Retained files

- `src/erp_agent_os/{metrics,postconditions,experiment}.py`
- `src/erp_agent_os/dataset.py` (validate_no_split_leakage)
- `src/erp_agent_os/bench_intents.py` (24-value pools)
- `src/erp_agent_os/bench_generator.py` (non-repeating slots, style fix)
- `src/erp_agent_os/system_a.py` (Spanish tool descriptions)
- `tests/test_{metrics,experiment}.py`, extended `test_bench_generator.py`
- `scripts/run_experiment.py`, `docs/results.md`
- `data/experiment_results.json`

## Verification evidence

- `python -m pytest` — 176 passed.
- `ruff check` / `ruff format --check` — clean.
- `mypy src` — no issues in 28 source files.
- Leakage: 480/480 unique texts, 0 cross-split texts, 0 cross-split
  (intent, arguments) pairs; validator proven by planted leak.
- Experiment: 1.080 observations, 3 per (case, system), deterministic
  under a fixed seed.

## Honest limitations carried forward

Selector held constant (not the §19 confirmatory protocol); System A is
close to a strawman so C − B is the informative contrast; postcondition
circularity; H2/H3/H7/H8 not measured; kappa pending.
