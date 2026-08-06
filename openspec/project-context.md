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
  by design; any result computed after a drift is exploratory (§19). The
  manifest does **not yet** cover LLM provider configuration — extend it
  before treating any `--real-llm` run as part of the frozen protocol.
- API keys live only in `.env` (gitignored, see `.env.example`); never in
  a committed file, never inside `src/`.
- The inference unit for any paired statistical test is the **case**, not
  the execution — repetitions of one case are not independent
  observations. See `collapse_repetitions` in `metrics.py`.

## Current state

**Delivered and tested** (30 modules, 231 tests, `ruff`/`mypy` clean, CI green):

| Layer | Modules |
|---|---|
| Deterministic core | `adapters`, `skills`, `policy`, `runtime`, `audit`, `validation` |
| Retrieval | `parser`, `retrieval`, `embeddings` |
| Systems under comparison | `system_a`, `system_b`, `system_c`, `llm_client`, `groq_client` |
| Benchmark | `catalog`, `bench_intents`, `bench_generator`, `bench_runner`, `handlers` |
| Measurement | `metrics`, `postconditions`, `statistics`, `agreement`, `experiment`, `freeze` |
| Infrastructure | `api`, `approval`, `persistence` |

**The confirmatory paired experiment has been run for real**: 1.080
observations (120 frozen test cases × 3 systems × 3 repetitions),
inference unit = case (n=120), `manifest.selector: "GroqClient"`,
`is_confirmatory_run: true`. Results in `data/experiment_results.json`,
full analysis in `docs/results.md`. STSR A 0.000 / B 0.483 / C 0.700;
false allow rate A 0.889 / B 0.889 / C 0.111; C−A +0.700 CI95
[+0.617, +0.783] Holm *p*=2.71e-19 OR=169; C−B +0.217 CI95
[+0.100, +0.333] Holm *p*=1.03e-3 OR=2.58; Cochran's Q = 110.96 (df 2).
System C never calls the LLM (its retrieval is TF-IDF), so its metrics
are byte-identical to the earlier stub run — by architecture, not by
accident. A stub-selector run (`is_confirmatory_run: false`) is kept as
an architecture-isolation baseline; both are documented side by side in
`docs/results.md`.

**Real LLM client**: `groq_client.py` wraps Groq's free tier
(`llama-3.1-8b-instant`, temperature 0). CLAUDE.md D-03 requires A/B/C to
share one model/provider/config, not a specific paid tier; using a free
one is a stated limitation disclosed in the memoria, not a hidden
shortcut.

## What is deliberately not done

- **The freeze manifest does not yet cover provider config** (model,
  temperature, retries) — the real run was launched at full scale before
  extending it, a disclosed trade-off, not an oversight.
- **H2/H8 (tokens, cost) not instrumented**; **H7 (traceability rubric)
  defined but not computed per execution**; **H3 cannot discriminate**
  even with a real LLM, because `temperature=0.0` (mandated by CLAUDE.md
  §23) makes it perfectly reproducible by design — a genuine tension
  between the low-temperature requirement and H3's testability, to
  discuss in the memoria rather than silently raise the temperature.
- **Second-annotator kappa pending.** The instrument exists and
  `scripts/compute_agreement.py` refuses to emit a number without human
  annotation.
- **`SqlAuditStore` is not wired into the API** (API state is still
  process-local). pgvector is provisioned but unused — retrieval embeds
  in-process over 12 skills.
- Odoo 19 adapter, Tableau dashboard, demo, video and the written
  memoria are post-core or unstarted.

## Defects found by self-audit (do not reintroduce)

Seven rounds of self-audit found seven real defects — full detail in
`docs/audit.md`. The recurring shape: code that passed *silently*, never
code that failed loudly.

1. **A vacuous split validator.** `validate_case_groups` passed while 10
   identical texts sat in both DEVELOPMENT and FINAL_TEST, because every
   case was its own group and a group of size 1 cannot cross.
2. **Two vacuous STSR conjuncts.** "No side effects" returned `True`
   unconditionally for permitted executions (never failed in 1.080
   observations) and "expected state" duplicated the decision check.
3. **Pseudo-replication.** 360 observations per system were treated as
   independent when all three repetitions of a case were verified
   identical — narrowed CIs by ≈√3, shrank p-values by 15 orders of
   magnitude. Fixed by `collapse_repetitions`.
4. **Two mutation-testing survivors** in the statistics layer: McNemar
   without its continuity correction (anti-conservative), and the
   bootstrap CI test accepting a degenerate `[x, x]` interval.

All seven were fixed; results did not change sign after any of them —
evidence the conclusions were robust, not that the fixes were needless.
Mutation testing now covers all 23 logic-bearing modules: 40 mutants
injected, 40 killed.

**The lesson generalizes:** a green check that *cannot* fail is worse
than no check, because it manufactures confidence. Every new guard must
be demonstrated failing — planted leak, tampered component, constructed
input, or injected mutant.
