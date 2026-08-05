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

Every case is its own paraphrase group (`paraphrase_group_id ==
request_id`): each formulation is generated independently from its own
seeded slot values, so no two cases are literal duplicates sharing a group,
and `dataset.validate_case_groups` trivially cannot detect leakage because
no group has more than one member. Per intent, the 20 drafts are
deterministically shuffled (seeded) before slicing into 10 dev / 5
validation / 5 test, so category labels interleave across splits instead
of clustering in one (verified: `python -m pytest tests/test_bench_generator.py`).

## Execution wiring (done — roadmap P8 groundwork)

`src/erp_agent_os/bench_runner.py` runs every case through a real,
isolated `FakeERPAdapter` + `Runtime` (12 handlers registered,
`src/erp_agent_os/handlers.py`) + `TfidfRetriever` + `AuditStore` +
`SystemC`, using the case's own `expected_arguments` as the parsed
proposal (no LLM call yet — see below). `scripts/run_bench_wiring_report.py`
produces `data/bench_v1_wiring_report.json`. Latest run:

| Label | Matched | Total | Rate |
|---|---|---|---|
| NORMAL | 210 | 240 | 87.5% |
| NOISE | 104 | 144 | 72.2% |
| ADVERSARIAL | 17 | 96 | 17.7% |

**Honest findings, not hidden:**

- The low ADVERSARIAL rate is *expected and diagnostic*, not a wiring
  bug: `policy.py`/`runtime.py` implement deny-by-default on
  role/state/risk only. There is no prompt-injection detector, no
  argument-range validator, no disguised-bulk-scope detector, and no
  irreversible-operation-framing detector — so those categories
  legitimately execute as `ALLOW`/`REQUIRE_APPROVAL` instead of the
  dataset's ideally-correct `DENY`. This is exactly what H4 (false allow
  rate) is meant to measure once the confirmatory experiment runs; fixing
  it is future policy-engine work (RF-06/07), not claimed done here.
- The dataset distinguishes `CLARIFY` from `ABSTAIN`; the current system
  only produces `ABSTAIN` (via `retrieval.should_abstain`) for missing
  fields — there is no separate clarification signal yet. All 24
  `missing_required_field` NOISE cases mismatch for exactly this reason.
- 46 NORMAL/NOISE mismatches (`error_type="none"`) come from TF-IDF
  occasionally ranking the wrong skill for short/ambiguous queries — a
  known baseline-retriever limitation, part of why §22 also specifies
  embeddings/hybrid ranking (`src/erp_agent_os/embeddings.py`,
  `retrieval.HybridRetriever`) as comparison points.
- 52 of 480 executions hit a caught `handler_error` (mismatched-skill
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
