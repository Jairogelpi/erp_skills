# Proposal: Define 24 canonical intents (work unit 12, closes P3.2)

## Intent

Deliver the second half of roadmap P3.2 and CLAUDE.md §11: exactly 24
canonical intents, 2 per catalog skill, each with a Spanish request
template and a deterministic slot-value pool. Depends on the completed
12-skill catalog (work unit 11).

## Scope

- `bench_intents.IntentSpec`: frozen dataclass — `intent_id`, `skill_id`,
  `family`, `template` (Spanish, `{field}` placeholders), `fixed_fields`
  (constant overrides, e.g. `product.update_field`'s two intents each pin
  `field`/`value` to a specific target).
- `bench_intents.INTENTS`: exactly 24 entries, 2 per catalog skill.
- Shared slot pools (`_CUSTOMERS`, `_PRODUCTS`, ... `_FIELD_POOLS`) reused
  by the generator (next unit).

## Non-goals

No formulation generation (styles, noise, adversarial categories — next
unit), no case objects, no split allocation.

## Follow-on dependency

The generator (work unit 13) turns each intent into 20 `BenchmarkCase`
formulations.

## Success criteria

Exactly 24 intents, unique ids, every intent's `skill_id` is in the
catalog, exactly 2 intents per skill, every template renders cleanly with
its required-field pool values (no leftover `{...}` placeholder).
`python -m pytest` passes in full.

## Forecast

One new source file (`bench_intents.py`, 265 lines) and one new test file
(`test_bench_intents.py`, 32 lines): **297 added lines**, below the
400-line budget.
