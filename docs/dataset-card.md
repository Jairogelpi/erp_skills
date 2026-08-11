# ERP-Skills-Bench v1 — dataset card

## Summary

480 fully synthetic Spanish ERP requests across 8 families, 24 canonical
intents, and the frozen 12-skill catalog (CLAUDE.md §11, §17). Generated
deterministically by `erp_agent_os.bench_generator.generate_cases()`
(seed `20260805`) and exported to `data/bench_v1.jsonl` by
`scripts/export_bench_v1.py`. No real customer, product, or personal data
— all names, amounts, and identifiers are synthetic placeholders drawn
from small fixed pools (`src/erp_agent_os/bench_intents.py`).

## Composition

| Property | Value |
|---|---|
| Total cases | 480 |
| Families | 8 (crm, contacts, sales, purchasing, product, inventory, tasks, billing) |
| Canonical intents | 24 (2 per skill) |
| Skills (catalog) | 12, frozen (`src/erp_agent_os/catalog.py`) |
| Split | 240 development / 120 validation / 120 test |
| NOISE label | 144 (30%) |
| ADVERSARIAL label | 96 (20%) |
| Overlap (NOISE ∩ ADVERSARIAL) | 0 by construction — every case gets exactly one abnormal label or none |

Per intent: 20 formulations = 10 NORMAL + 6 NOISE (5 stylistic transforms +
1 required-field omission, forcing `CLARIFY`) + 4 ADVERSARIAL (rotating
through 4 of the 11 categories in CLAUDE.md §17, selected deterministically
by intent index so all 11 categories appear across the 24 intents).

## Split methodology

Split allocation is 10 development / 5 validation / 5 test per intent
(240/120/120 overall), assigned after a seeded shuffle.

**Corrección de un defecto anterior.** Una versión previa de esta tarjeta
afirmaba que, al ser cada caso su propio grupo de paráfrasis,
`validate_case_groups` «trivialmente no puede detectar fuga». Eso era
cierto — y precisamente por eso era **una justificación equivocada**: el
validador pasaba de forma vacua mientras **10 textos idénticos** estaban a
la vez en `DEVELOPMENT` y `FINAL_TEST` (8,3 % del test). §17 prohíbe que
cruce «ni formulación semánticamente equivalente», no solo un id de grupo.

Arreglado: pools de valores ampliados de 4–8 a 24, asignación de slots sin
repetición dentro de una intención, un estilo duplicado sustituido y el
truncado de `incomplete_instruction` alargado. El validador real es ahora
`validate_no_split_leakage` (texto normalizado **y** par
(intención, argumentos)), **probado con una fuga plantada** para que no
vuelva a ser vacuo. Estado actual: **480/480 textos únicos, 0 cruces**.

## Execution wiring (done — roadmap P8 groundwork)

`src/erp_agent_os/bench_runner.py` runs every case through a real,
isolated `FakeERPAdapter` + `Runtime` (12 handlers registered,
`src/erp_agent_os/handlers.py`) + `TfidfRetriever` + `AuditStore` +
`SystemC`, using the case's own `expected_arguments` as the parsed
proposal (no LLM call yet — see below). `scripts/run_bench_wiring_report.py`
produces `data/bench_v1_wiring_report.json`. Latest run:

| Label | Matched | Total | Rate | (first pass, before `validation.py`) |
|---|---|---|---|---|
| NORMAL | 211 | 240 | 87.9% | 87.5% |
| NOISE | 129 | 144 | 89.6% | 72.2% |
| ADVERSARIAL | 55 | 96 | 57.3% | 17.7% |

The first-pass column is the honest baseline measured *before* any
adversarial detection existed. Two changes moved it:

1. `src/erp_agent_os/validation.py` — lexical detection of prompt
   injection, bulk-scope, irreversible-operation framing and permission
   claims, plus numeric range/type checks. Blocking findings deny before
   any risk-tier reasoning, preserving the monotonicity property
   (a more restrictive input never yields a more permissive decision).
2. `SystemC` now distinguishes `CLARIFY` (required data is missing — the
   system knows what to ask for) from `ABSTAIN` (no candidate is
   trustworthy enough), which the dataset always distinguished.

**Honest findings and remaining gaps, not hidden:**

- **The detectors are lexical, not semantic.** They are tuned to this
  frozen benchmark's *template-generated* adversarial text. They are not
  a general-purpose prompt-injection defence, and the 57.3% figure must
  be reported as "detection of known patterns" with that ceiling stated
  (CLAUDE.md §36, validez de constructo). An adversary phrasing the same
  intent differently would likely pass.
- **41 adversarial cases still mismatch**, by category:
  `unknown_record_id` (9, needs a pre-execution existence check),
  `conflicting_fields` (8, needs semantic analysis),
  `near_miss_skill_conflict` (7), `argument_out_of_range` (6, fields
  outside the two numeric limits currently declared),
  `irreversible_operation_requested` (5, phrasings the regexes miss),
  `disguised_bulk_change` (3), `retry_expect_idempotent` (2),
  `prompt_injection_detected` (1).
- 46 NORMAL/NOISE mismatches (`error_type="none"`) come from TF-IDF
  occasionally ranking the wrong skill for short/ambiguous queries — a
  known baseline-retriever limitation, part of why §22 also specifies
  embeddings/hybrid ranking (`src/erp_agent_os/embeddings.py`,
  `retrieval.HybridRetriever`) as comparison points.
- 47 of 480 executions hit a caught `handler_error` (mismatched-skill
  arguments or the deliberately-unseeded `identificador_inexistente`
  reference) — `Runtime.execute` catches these (`UnknownModelError`,
  `UnknownRecordError`, `KeyError`) and reports them rather than crashing,
  a hardening this wiring pass discovered was needed and added.
- `initial_state`/`expected_final_state` in `data/bench_v1.jsonl` remain
  the original annotation placeholders — they describe intended pre/post
  conditions independent of any one execution run's seeding choices, not
  a literal snapshot from this particular wiring pass.

## Known limitations (explicit, not hidden)

- **No LLM parser yet.** Execution wiring uses each case's own
  `expected_arguments` as a stand-in "perfect parse," not a real
  structured-generation call — that is separate, provider-facing work
  (CLAUDE.md §23) belonging to phase 8/system-C-integration proper.
- **No second annotator.** CLAUDE.md §17 calls for a sample reviewed by a
  second annotator and a reported agreement (kappa). This dataset was
  generated programmatically by one contributor session; a genuine
  second-annotator review is a pending human step, not something this
  session can produce on its own — recorded as pending, not claimed done.
- **Adversarial category texts are template-based**, not independently
  authored per case; a category's textual pattern (e.g. the prompt-
  injection suffix) repeats verbatim across the ~9 intents where it's
  selected. This is a reproducibility choice (auditable, deterministic)
  traded against textual diversity within a category.
- **Argument/decision correctness is self-consistent by construction**
  (the generator computes `expected_decision` from the same risk-class
  logic as `policy.decide`), not independently verified against a second
  ground truth. This is standard for a synthetic benchmark but should be
  named as a construct-validity caveat in the memoria (CLAUDE.md §36).

## Regeneration

```sh
uv run python scripts/export_bench_v1.py
uv run python scripts/run_bench_wiring_report.py
```

Deterministic: re-running overwrites `data/bench_v1.jsonl` and
`data/bench_v1_wiring_report.json` with byte-identical content (same
seed, same generation order, same execution logic).
