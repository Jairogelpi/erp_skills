# Design: append-only audit store

## Contract

```python
@dataclass(frozen=True)
class AuditEvent:
    correlation_id: str
    skill_id: str
    skill_version: str
    role: str
    decision: str
    risk_score: float
    reasons: tuple[str, ...]
    idempotency_key: str
    idempotent_replay: bool
    postconditions_met: bool | None
    output: Any
    recorded_at: datetime

class AuditStore:
    def __init__(self, *, redact_keys: frozenset[str] = frozenset(),
                 clock: Callable[[], datetime] = ...) -> None: ...
    def record(self, correlation_id, skill, role, outcome, execution,
               idempotency_key) -> AuditEvent: ...
    def events(self, correlation_id: str | None = None) -> tuple[AuditEvent, ...]: ...
```

## Alternatives considered

- **Expose a `delete`/`purge` method behind an internal flag check**:
  rejected. CLAUDE.md §14 requires append-only; the simplest correct
  enforcement is "the capability does not exist," not a runtime guard that
  could be bypassed or forgotten. No delete/update method is written at
  all.
- **Return a `list` from `events()`**: rejected. A `list` invites in-place
  mutation by the caller; returning a `tuple` copy makes independence a
  type-level guarantee, verified by the copy-independence test.
- **Take `AuditEvent` fields directly instead of `(skill, outcome,
  execution)` objects**: rejected. The store's job is to observe the
  runtime/policy engine's own outputs; accepting their result types keeps
  the call site (future API layer) from re-deriving fields runtime/policy
  already computed, and keeps this module decoupled from having its own
  parallel notion of "decision."
- **Redact via a fixed denylist constant**: rejected. `redact_keys` is a
  constructor parameter because what counts as sensitive is a deployment/
  skill-family decision (CLAUDE.md §30), not a constant this module should
  own.

## Risks

- In-memory only, matching `FakeERPAdapter`/`Runtime`'s scope; PostgreSQL
  persistence is later, non-core work (roadmap P6.2).
- Redaction is shallow-typed to `dict` inputs; `execution.output` values
  that are plain scalars or lists pass through unredacted by design (there
  is no key to match against).

## Test strategy

`tests/test_audit.py`: single record round-trip, correlation-id filtering,
redaction masking a configured key while preserving others, independence of
the returned tuple from later mutation, and append-order preservation
across multiple records.
