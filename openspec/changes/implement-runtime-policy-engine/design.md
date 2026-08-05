# Design: runtime and policy engine

## Contract

```python
class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"; SIMULATE = "SIMULATE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"; DENY = "DENY"

@dataclass(frozen=True)
class PolicyOutcome:
    decision: PolicyDecision
    risk_score: float
    reasons: list[str]
    policy_version: str

def decide(skill, role, *, approval_granted=False) -> PolicyOutcome: ...

class Runtime:
    def __init__(self, erp: FakeERPAdapter) -> None: ...
    def register(self, skill_id: str, version: str, handler) -> None: ...
    def execute(self, skill, args, role, idempotency_key, *,
                approval_granted=False, postcondition_checks=()) -> ExecutionResult: ...
```

## Alternatives considered

- **Fold policy into runtime as one module**: rejected. CLAUDE.md §14 keeps
  Policy Engine and Runtime as separate architectural components with
  distinct responsibilities (decide vs. execute); separating them also
  keeps `decide` pure and trivially testable without any adapter/handler
  wiring.
- **Idempotency key derived internally via the §25 hash formula**: deferred.
  The formula needs `user_scope`/`normalized_arguments`/`business_time_
  window`, which are parser/API concerns not yet built. The runtime accepts
  a caller-supplied key now; a helper that derives it per §25 belongs with
  the parser/API work.
- **Auto-approve R2/R3 based on an amount threshold in the skill's own
  `approval_required_when`**: deferred. Evaluating those expressions is
  approval-service/policy-detail work; this unit takes `approval_granted`
  as an explicit boolean input, keeping `decide` a pure function without an
  expression evaluator.
- **Raise on postcondition failure**: rejected. CLAUDE.md §25 says the
  verifier "detiene acciones posteriores" (stops downstream actions) — that
  is an orchestration decision made by the caller (future audit/API layer),
  not a runtime-internal exception. `postconditions_met` is reported, not
  enforced, here.

## Risks

- `Runtime`'s idempotency cache and handler registry are process-local
  in-memory dicts — matches FakeERP's own in-memory-only scope; a real
  registry/audit-store persistence layer is later, non-core work.
- Postcondition checks are trusted callables, not the string identifiers
  stored on `SkillDefinition.postconditions`; mapping those strings to
  callables is deferred to whichever layer registers handlers (keeps this
  unit's scope to the mechanism, not the mapping).

## Test strategy

`tests/test_policy.py`: role/state gating, R2 approval round-trip, R3
approval-still-simulates. `tests/test_runtime.py`: ALLOW mutates state,
DENY never calls the handler, unregistered handler raises, idempotency
replay via a call-counting handler, and a failing postcondition check
surfaces `False` without raising.
