# Proposal: Populate the 12-skill catalog (work unit 11, closes P3.2 part 1)

## Intent

Deliver the fixed skill catalog CLAUDE.md §11 requires before the
benchmark can be generated: exactly 12 `SkillDefinition` instances
spanning the 8 confirmed families. Blocks A/B/C (phase 8) and the
confirmatory experiment (phase 9) until it exists — this session's
highest-priority gap, confirmed by the user.

## Scope

- `catalog.CATALOG`: 12 `SkillDefinition` instances (2 CRM, 1 contacts,
  3 sales, 1 purchasing, 1 product, 1 inventory, 1 tasks, 1 billing — all
  8 families covered, no family without a skill).
- All `ACTIVE`, no `R4`, unique `skill_id`s.
- `CATALOG_BY_ID`, `FAMILIES` lookups for downstream use (intents,
  generator, retrieval).

## Non-goals

No canonical intents (next unit), no generated benchmark cases (unit
after that), no persistence/registry service (roadmap P6.2).

## Follow-on dependency

24 canonical intents (2 per skill) map onto this catalog next.

## Success criteria

Exactly 12 skills, covering all 8 `CLAUDE.md` §11 families, none `R4`, all
`ACTIVE`, unique ids. `python -m pytest` passes in full.

## Forecast

One new source file (`catalog.py`, 169 lines) and one new test file
(`test_catalog.py`, 26 lines): **195 added lines**, below the 400-line
budget.
