# Design: System C integration

## Contract

```python
@dataclass(frozen=True)
class SystemCResult:
    decision: str
    selected_skill_id: str | None
    execution: ExecutionResult | None
    reasons: tuple[str, ...]

class SystemC:
    def __init__(self, erp, runtime, retriever, audit, approval=None) -> None: ...
    def handle(self, correlation_id, query_text, proposal, role,
               idempotency_key) -> SystemCResult: ...
```

## Alternatives considered

- **Skip auditing abstention**: rejected. CLAUDE.md §25 requires every
  terminal decision recorded; abstention is a terminal decision reachable
  before any skill is selected, so it needs its own event shape
  (`AbstentionEvent` has no skill/execution to attach to `AuditEvent`).
- **Call `Runtime.execute` and derive the `PolicyOutcome` from its return
  value alone**: rejected. `ExecutionResult` doesn't carry `reasons`/
  `risk_score`; `SystemC` calls `policy.decide` once itself to get the
  `PolicyOutcome` for the audit record, accepting the minor duplication
  with `Runtime.execute`'s own internal `decide` call rather than
  widening `Runtime`'s return type for this one caller.
- **Have `SystemC` own retry/timeout handling**: deferred. Not in scope
  per CLAUDE.md §25's retry conditions, which need transient-failure
  classification that doesn't exist yet; `Runtime`'s own `max_retries`
  field on `SkillDefinition.execution` remains unconsumed until that
  classification is built.

## Risks

- `SystemC` takes an already-built `TfidfRetriever` (fixed skill list at
  construction); a mutable catalog (skills added/approved live) needs a
  registry, which is out of this unit's scope.

## Test strategy

`tests/test_system_c.py`: full ALLOW path (mutation + one audit event),
missing-field abstention (no mutation, one abstention event), low-score
abstention, inactive-skill DENY (still audited, no mutation), repeated
idempotency key (single mutation through the full path), and an R2 skill
turning `ALLOW` once a valid approval is granted.
