# Design: twelve-skill catalog

## Alternatives considered

- **Use exactly the 12 illustrative examples in CLAUDE.md §11 verbatim**:
  rejected as impossible without invention — that list (buscar contacto,
  crear oportunidad, ...) doesn't name a "compras" (purchasing) example,
  yet §11 requires all 8 families represented. The 12 skills here are
  authored to satisfy the same intent (illustrative operations per
  family) while covering all 8 families explicitly, since §11 prefaces
  its list with "Ejemplos:" — illustrative, not an exact enumeration.
- **More than one skill's worth of families sharing a single skill**:
  rejected. Every family gets at least one dedicated skill so retrieval/
  policy behavior can be exercised per family in the confirmatory
  experiment.

## Risks

- Skill descriptions/postconditions are authored, not derived from a real
  Odoo/ERP schema; consistent with FakeERP being the confirmatory core
  (CLAUDE.md §14/§26).

## Test strategy

`tests/test_catalog.py`: count, family coverage, no-R4, all-ACTIVE,
unique-ids.
