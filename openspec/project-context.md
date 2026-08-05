# ERP Agent OS — SDD project context

## Authority and scope

`../CLAUDE.md` is the normative product and experimental specification.
This context does not replace or reinterpret it; it records where the
implementation currently stands so a new work unit starts from fact
rather than from a stale plan.

## Non-negotiable constraints inherited from CLAUDE.md

- Use synthetic data only.
- `FakeERPAdapter` is mandatory for the confirmatory core; Odoo 19 is
  post-core.
- The benchmark has 24 canonical intents, 480 requests, 8 ERP families,
  and fixed development/validation/test splits of 240/120/120.
- No formulation may cross splits — not just no shared group id, but no
  identical text and no identical (intent, arguments) pair.
- A confirmatory run restores the same FakeERP initial state for each
  paired `request_id`–state–repetition observation.
- Skills are versioned and stateful. Execution is restricted to
  registered handlers; no arbitrary generated code is executable.
- R4 operations are unconditionally denied. No physical deletion,
  payments, production access, or bulk automatic changes are in scope.
- The frozen protocol is hashed in `data/freeze_manifest.json`. Changing
  the test split, dataset, catalog or seed without re-freezing breaks CI
  by design; any result computed after a drift is exploratory (§19).

## Current state

**Delivered and tested** (29 modules, 188 tests, 96% coverage, CI green):

| Layer | Modules |
|---|---|
| Deterministic core | `adapters`, `skills`, `policy`, `runtime`, `audit`, `validation` |
| Retrieval | `parser`, `retrieval`, `embeddings` |
| Systems under comparison | `system_a`, `system_b`, `system_c`, `llm_client` |
| Benchmark | `catalog`, `bench_intents`, `bench_generator`, `bench_runner`, `handlers` |
| Measurement | `metrics`, `postconditions`, `statistics`, `agreement`, `experiment`, `freeze` |
| Infrastructure | `api`, `approval`, `persistence` |

**The paired experiment has been run**: 1.080 observations (120 frozen
test cases × 3 systems × 3 repetitions). Results in
`data/experiment_results.json`, analysis in `docs/results.md`. STSR
A 0.000 / B 0.333 / C 0.700; false allow rate A 1.000 / B 0.778 /
C 0.111; C−A +0.700 CI95 [+0.653, +0.747], C−B +0.367 CI95
[+0.306, +0.425], both Holm-corrected; Cochran's Q = 353.1 (df 2).

## What is deliberately not done

- **No real LLM client.** The selector is held constant across A/B/C, so
  the run isolates the architectural contribution and is **not** the §19
  confirmatory protocol. The manifest records
  `is_confirmatory_run: false`. This is the single blocking dependency.
- **H2/H8 (tokens, cost) not instrumented**; **H7 (traceability rubric)
  defined but not computed per execution**; **H3 cannot discriminate**
  with a deterministic selector (null result, reported as such).
- **Second-annotator kappa pending.** The instrument exists and
  `scripts/compute_agreement.py` refuses to emit a number without human
  annotation.
- **`SqlAuditStore` is not wired into the API** (API state is still
  process-local). pgvector is provisioned but unused — retrieval embeds
  in-process over 12 skills.
- Odoo 19 adapter, Tableau dashboard, demo, video and the written
  memoria are post-core or unstarted.

## Two defects found by self-audit (do not reintroduce)

1. **A vacuous split validator.** `validate_case_groups` passed while 10
   identical texts sat in both DEVELOPMENT and FINAL_TEST, because every
   case was its own group and a group of size 1 cannot cross. Any new
   validator must be proven non-vacuous by a planted failure, as
   `validate_no_split_leakage` and `verify_freeze` now are.
2. **Two vacuous STSR conjuncts.** "No side effects" returned `True`
   unconditionally for permitted executions (never failed in 1.080
   observations) and "expected state" duplicated the decision check.
   Both now measure state; regression tests guard them.

The lesson generalizes: a green check that *cannot* fail is worse than
no check, because it manufactures confidence. Prove the guard fails.
