> **CORRECCIÓN (unidad 21).** El razonamiento marcado abajo sobre los
> grupos de paráfrasis **era erróneo** y produjo una fuga real: 10 textos
> idénticos acabaron a la vez en `DEVELOPMENT` y `FINAL_TEST` (8,3 % del
> test). Que un grupo de tamaño 1 «trivialmente no pueda cruzar» no
> satisface §17, que prohíbe además que cruce cualquier *formulación
> semánticamente equivalente*. Se conserva el texto original porque esta
> bitácora es append-only, pero **no debe leerse como una decisión de
> diseño válida**. El arreglo y el validador no vacuo están en
> `openspec/changes/close-scientific-core/`.

# Design: ERP-Skills-Bench v1 generation

## Approach

Per intent (24), build 20 `_CaseDraft`s: 10 via `_STYLE_NORMAL` transforms
applied to the filled template, 6 via `_STYLE_NOISE` transforms (5) plus
one hand-coded required-field omission, and 4 via `_apply_adversarial`
dispatching on a category name drawn from `_ADV_CATEGORIES[(index*4+k) %
11]`. Drafts are shuffled with the module's single seeded `random.Random`
instance (not re-seeded per intent) before slicing into the 10/5/5 split,
so the same seed always reproduces the same overall dataset.

## Alternatives considered

- **Real paraphrase groups (>1 case per group) with a leakage-avoidance
  allocator**: rejected for v1. Building a correct group-aware splitter
  is meaningfully more code and risk than the value it adds at this
  dataset's scale; making every case its own group is a valid, simpler
  reading of "no paraphrase group crosses splits" (a group of size 1
  trivially can't cross) and is stated as a design choice, not hidden.
- **LLM-authored formulations for lexical diversity**: rejected. Would
  need a provider call, non-determinism control, and cost/latency
  management wholly out of scope for a schema/generator unit; the
  template+transform approach is fully deterministic and reproducible
  (RF-17), matching CLAUDE.md §17's "datos completamente sintéticos."
- **One handler function per adversarial category in a separate module**:
  rejected — see proposal.md's explicit budget-exception rationale; kept
  as one dispatch function for reviewability of the category → outcome
  mapping in one place.
- **Persist `initial_state`/`expected_final_state` as real FakeERP
  snapshots**: rejected for this unit. That requires a real skill-handler
  registry executing each case once to capture pre/post state — a phase-8
  concern (piloto), not dataset generation. Placeholder dicts name this
  explicitly (`{"pending_execution_wiring": True}`) rather than
  fabricating state that was never actually produced by execution.

## Risks

- Adversarial category text patterns repeat verbatim across intents that
  draw the same category (documented in the dataset card as a
  reproducibility-over-diversity tradeoff).
- No second-annotator review yet (documented as a pending human step, not
  claimed complete).

## Test strategy

`tests/test_bench_generator.py`: exact case count, exact split counts,
exact noise/adversarial counts, zero group leakage (via
`validate_case_groups`), valid `expected_skill` for every case, unique
`request_id`s, determinism (`generate_cases() == generate_cases()`), and
all 24 intents represented.
