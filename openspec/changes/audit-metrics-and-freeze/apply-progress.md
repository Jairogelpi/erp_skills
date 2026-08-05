# Apply progress: measurement audit and freeze (work unit 22)

## Status

Complete. Two vacuous STSR conjuncts repaired, protocol frozen and
CI-verified, documentation corrected.

## Verification evidence

- `python -m pytest` — 188 passed; coverage 96%.
- `ruff check` / `ruff format --check` — clean.
- `mypy src` — no issues in 29 source files.
- `python scripts/freeze_protocol.py --verify` — freeze intact.
- Experiment re-run after the fixes: STSR A 0.000 / B 0.333 / C 0.700,
  identical to before, so no published number changed.
- Conjunct 5 now detects 3 real System B side-effect observations
  (previously 0 across 1.080).

## Carried forward

Real LLM client (blocking for §19); H2/H7/H8 unmeasured; kappa pending;
`SqlAuditStore` not wired into the API; freeze does not yet cover prompts
or provider configuration.
