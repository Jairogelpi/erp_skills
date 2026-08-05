# Design: skill contract

## Contract

```python
class SkillState(str, Enum):
    DRAFT = "DRAFT"; VALIDATED = "VALIDATED"; TESTED = "TESTED"
    APPROVED = "APPROVED"; ACTIVE = "ACTIVE"; DEPRECATED = "DEPRECATED"
    QUARANTINED = "QUARANTINED"

def transition(current: SkillState, target: SkillState) -> SkillState: ...

class SkillDefinition(BaseModel):  # strict, frozen, extra="forbid"
    skill_id: str
    version: str          # MAJOR.MINOR.PATCH
    module: str
    operation: str
    description: str
    risk_class: RiskClass  # R4 rejected
    input_schema: dict[str, Any]
    permissions: Permissions   # allowed_roles: nonempty list[str]
    preconditions: list[str]
    execution: Execution       # handler dotted path, timeout>0, retries>=0
    postconditions: list[str]  # nonempty
    approval_required_when: list[str] = []
    state: SkillState = SkillState.DRAFT
```

## Alternatives considered

- **Store the state graph as a method on `SkillDefinition`**: rejected. The
  graph is fixed and stateless (CLAUDE.md §15 lifecycle is normative, not
  per-skill configurable); a free function plus a module-level constant is
  simpler and the graph can be unit-tested independent of any instance.
- **`jsonschema`-validate `input_schema` contents**: rejected for this unit.
  `input_schema` is stored as an opaque `dict[str, Any]` (matching the YAML
  example's own JSON-Schema shape); actually validating candidate skill
  *arguments* against it is runtime/policy-engine work (P4.3), not part of
  the contract itself.
- **Reuse `RiskClass` from `dataset.py`** rather than redefining it: single
  source of truth for the five-value taxonomy shared by benchmark cases and
  skills.

## Risks

- The dotted-path regex for `handler` is a syntactic check only; it does not
  verify the handler is actually registered. Runtime (P4.4) owns rejecting
  unregistered handlers at execution time — "only registered handlers
  execute" is a runtime property, not a schema property.

## Test strategy

Focused `tests/test_skills.py`: default-state check, direct `DRAFT→ACTIVE`
rejection, quarantine-from-every-state, the full six-state happy path, and a
parametrized rejection set (R4 risk, empty postconditions, bad version).
