# Design: canonical intents

## Contract

```python
@dataclass(frozen=True)
class IntentSpec:
    intent_id: str
    skill_id: str
    family: str
    template: str
    fixed_fields: dict[str, str]

    @property
    def required_fields(self) -> list[str]: ...
    def field_pool(self, field: str) -> list[str]: ...
```

## Alternatives considered

- **Derive `required_fields` by duplicating the skill's list on
  `IntentSpec`**: rejected. Reading `CATALOG_BY_ID[skill_id]
  .input_schema["required"]` via a property keeps the catalog the single
  source of truth; a duplicated, hand-copied list would drift the moment
  either side changed.
- **One shared slot pool per field name vs. per-intent pools**: chose
  shared (`_FIELD_POOLS` keyed by field name, e.g. `customer_name` reused
  by every intent that needs a customer). Per-intent pools would 24x the
  authored vocabulary for no behavioral benefit at this dataset's scale.
  `fixed_fields` is the escape hatch for the two intents that need a
  constant rather than a pool (`product.update_field`'s `field`/`value`).

## Risks

- Slot pools are small (4–8 values); at 20 formulations per intent, some
  repetition across NORMAL cases within one intent is expected and
  acceptable for a synthetic benchmark (CLAUDE.md §17: "Datos
  completamente sintéticos").

## Test strategy

`tests/test_bench_intents.py`: exact count, unique ids, cataloged
skill_ids, 2-per-skill grouping, and template-renders-cleanly for every
intent using its own required-field pool.
