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

**Delivered and tested** (35 modules, 298 tests, `ruff`/`mypy` clean, CI green):

| Layer | Modules |
|---|---|
| Deterministic core | `adapters` (incl. `ErpAdapter` Protocol), `skills`, `policy`, `runtime` (generic over adapter type), `audit`, `validation` |
| Retrieval | `parser`, `retrieval`, `embeddings` |
| Systems under comparison | `system_a`, `system_b`, `system_c`, `llm_client`, `groq_client`, `gemini_client`, `openrouter_client` |
| Benchmark | `catalog`, `bench_intents`, `bench_generator`, `bench_runner`, `handlers` |
| Measurement | `metrics`, `postconditions`, `statistics`, `agreement`, `experiment`, `freeze`, `traceability` |
| Infrastructure | `api`, `approval`, `persistence` |
| Post-core Odoo 19 | `odoo_client` (JSON-2 API adapter), `odoo_handlers` (2 skills mapped to real models) |

**The confirmatory paired experiment has been run for real**: 1.080
observations (120 frozen test cases × 3 systems × 3 repetitions),
inference unit = case (n=120), `manifest.selector: "OpenRouterClient"`
(`openai/gpt-oss-20b:free`), `is_confirmatory_run: true`. Results in
`data/experiment_results.json`, full analysis in `docs/results.md`. STSR
A 0.000 / B 0.517 / C 0.700; false allow rate A 0.333 / B 0.889 / C
0.111; C−A +0.700 CI95[+0.617,+0.783] Holm *p*=2.71e-19 OR=169; C−B
+0.183 CI95[+0.058,+0.308] Holm *p*=7.65e-3 OR=2.07; Cochran's
Q=109.46 (df 2). H2 (tokens) and H7 (traceability) are populated with
real numbers for the first time: mean tokens/execution A=198 B=230 C=0;
mean traceability score A=0.19 B=0.36 C=0.80. System C never calls the
LLM (TF-IDF retrieval), so its metrics are byte-identical across every
real run tried — by architecture, not by accident. A stub-selector run
is kept as an architecture-isolation baseline in `docs/results.md`.

**Provider history, for transparency.** Groq (`llama-3.1-8b-instant`)
completed one full confirmatory run before H2/H7 existed; relaunching
with the new instrumentation exhausted Groq's daily quota (prior
interrupted attempts, before checkpointing existed, had already spent
it). Gemini was tried next (`gemini-flash-latest`, `gemini-2.5-flash-lite`,
`gemini-3.1-flash-lite`) — every model on this key carries a
20-requests-PER-DAY free-tier cap, unusable for the ~240 real calls one
run needs. OpenRouter (`openai/gpt-oss-20b:free`) is what actually
completed with the full H2/H7 instrumentation and is the run reported
above. All three clients are kept in the codebase, tested, and
selectable via `--provider {groq,gemini,openrouter}` — this is a
disclosed practical constraint (free-tier quota shopping), not a hidden
methodology change; CLAUDE.md D-03 requires one provider *within* a run,
not a specific provider.

**Checkpoint/resume and call caching**, added after three interrupted
Groq runs: `run_experiment(..., checkpoint_path=...)` persists each
completed observation to a per-provider JSONL file, so an interruption
(quota, Windows sleep — the actual root cause once diagnosed, now
disabled for this session — or anything else) only costs the calls not
yet checkpointed. `CachingLLMClient` serves repetitions 2 and 3 of the
same case from an in-process cache (temperature=0 makes this exact, per
H3=1.0 in three independent real runs), cutting real calls for A+B from
720 to ~240.

**External adversarial stress test (InjecAgent).** The declared
limitation "detectors are lexical, tuned to our own templated corpus"
(`docs/results.md`, CLAUDE.md §36) was measured, not just asserted,
against 510 real out-of-distribution cases (Zhan et al. 2024): 0.0%
detection with the Spanish-only detector, 3.3% (17/510) after adding
English patterns. Going bilingual did not close the gap — most
InjecAgent payloads are polite direct requests with no attack-style
framing at all, invisible to any lexical detector by construction, not
a vocabulary gap. Full result in `docs/injecagent-stress-test.md`.

**Odoo 19 post-core demo, both adapter-only and fully governed.**
`odoo_client.py` (`Odoo19Adapter`) is a statically-typed drop-in for
`FakeERPAdapter` (`ErpAdapter` Protocol in `adapters.py`; `Runtime`
made `Generic[T]` after mypy caught a real `Callable` parameter-
variance error handlers.py's FakeERP-typed handlers would otherwise
have failed). Two live demos against a real Odoo.sh Development-branch
instance (confirmed demo data, not a production clone, before any
write): `scripts/odoo_demo.py` (adapter only: create→verify→update→
independent re-read) and `scripts/odoo_governed_demo.py` (the *same*
`Runtime`/`SystemC`/`ApprovalService`/`AuditStore` the confirmatory
core runs 1.080 times, pointed at real Odoo — an R1 skill
auto-executes, an R2 skill is blocked with `REQUIRE_APPROVAL` and
proven via an independent Odoo read to leave the record untouched,
then executes correctly once approved). Full audit trail captured.
Only 2 of 12 catalog skills are mapped to real Odoo models — declared,
not hidden. Details and both live results in `docs/odoo-demo.md`.

## What is deliberately not done

- **The freeze manifest does not yet cover provider config** (model,
  temperature, retries) — a disclosed trade-off, not an oversight.
- **H8 (cost)** is a declared-rate sensitivity analysis per CLAUDE.md
  §20, not measured spend (the providers used are genuinely free).
  **H3 cannot discriminate** even with a real LLM, because
  `temperature=0.0` (mandated by CLAUDE.md §23) makes it perfectly
  reproducible by design — confirmed across three independent real runs
  on three different providers, not just once.
- **Second-annotator kappa pending.** The instrument exists
  (`data/annotation_review_sheet.csv`, 96 stratified cases) and
  `scripts/compute_agreement.py` refuses to emit a number without human
  annotation — the human step itself has not happened yet.
- **`SqlAuditStore` is not wired into the API** (API state is still
  process-local). pgvector is provisioned but unused — retrieval embeds
  in-process over 12 skills.
- **Only 2 of 12 catalog skills mapped to real Odoo models**; no
  graceful degradation if retrieval routes to one of the other 10 (would
  raise `UnregisteredHandlerError`) — acceptable for a scoped demo, not
  for a production integration.
- Tableau dashboard, demo video, presentation and the written memoria
  are post-core or unstarted.

## Defects found by self-audit (do not reintroduce)

The 8 items below (some bundle more than one CLAUDE.md-numbered defect,
e.g. #4 covers two separate mutation-testing survivors) summarize the
self-audit history — full detail, with exact per-defect numbering, in
`docs/audit.md` and the `CLAUDE.md` bitácora. The recurring shape: code
that passed *silently*, never code that failed loudly.

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
5. **A manifest caveat inconsistent with `is_confirmatory_run`** in the
   first real run's own report: it claimed "NOT the confirmatory
   protocol" next to `is_confirmatory_run: true`.
6. **A manifest caveat that hardcoded the wrong provider name.** After
   fixing #5, the confirmatory-branch text still literally said "Groq
   free tier" regardless of which provider actually ran — a run made
   with OpenRouterClient would have published a caveat naming Groq.
7. **A `Callable` parameter-variance bug caught by mypy, not guessed.**
   Retyping `Runtime`/`SystemC`/`postconditions.py` against a broad
   `ErpAdapter` Protocol (so `Odoo19Adapter` could be a genuine typed
   drop-in) initially fixed `Handler` to `Callable[[ErpAdapter], Any]`
   — mypy then correctly rejected every handler in `handlers.py`
   (typed for `FakeERPAdapter` specifically), since `Callable`
   parameter types are contravariant: a function promising to accept
   only `FakeERPAdapter` does not satisfy "accepts any `ErpAdapter`".
   Fixed by making `Runtime` generic (`Generic[T]`), not by widening
   the type or suppressing the error.
8. **Two error classes with the same name, different identity.**
   `odoo_client.py` originally defined its own `UnknownModelError`/
   `UnknownRecordError`, distinct objects from `adapters.py`'s classes
   of the same name. `Runtime.execute()`'s `except (UnknownModelError,
   UnknownRecordError, KeyError)` imports those from `adapters.py`
   specifically, so it would **not** have caught the Odoo versions — an
   Odoo failure during a governed request would have crashed the whole
   call instead of surfacing as a normal `handler_error`. Fixed by
   re-exporting and raising the same classes; a test pins class
   identity so this cannot silently regress.

All were fixed; results did not change sign after any of them —
evidence the conclusions were robust, not that the fixes were needless.
Mutation testing covers the 23 logic-bearing modules from before the
Odoo/InjecAgent work: 40 mutants injected, 40 killed. **Not yet
mutation-tested**: `odoo_client`, `odoo_handlers`, `gemini_client`,
`openrouter_client`, `traceability` — declared gap, not claimed covered.

**The lesson generalizes:** a green check that *cannot* fail is worse
than no check, because it manufactures confidence. Every new guard must
be demonstrated failing — planted leak, tampered component, constructed
input, or injected mutant.
