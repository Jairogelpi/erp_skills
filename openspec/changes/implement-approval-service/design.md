# Design: approval service

## Contract

```python
@dataclass(frozen=True)
class Approval:
    actor: str; scope: str; granted_at: datetime; expires_at: datetime

class ApprovalService:
    def __init__(self, *, clock: Callable[[], datetime] = ...) -> None: ...
    def grant(self, actor: str, scope: str, ttl_seconds: int) -> Approval: ...
    def is_valid(self, scope: str) -> bool: ...
```

## Alternatives considered

- **Store only the latest approval per scope**: rejected. A `list` keeps
  history (useful for the audit trail this feeds) at negligible cost for
  the 12-skill catalog scale; `is_valid` still just needs any matching,
  unexpired entry.
- **Wire `grant`/`is_valid` directly into `policy.decide`**: rejected.
  `policy.decide` takes `approval_granted: bool` as an explicit input
  (work unit 4's design choice) precisely so it stays a pure function;
  the API layer (P6.1) is what will call `is_valid` and pass its result
  in.

## Risks

- In-memory only, matching every other core module's scope in this
  foundation; persistence is later, non-core work (P6.2).

## Test strategy

`tests/test_approval.py`: valid-before-expiry and invalid-after-expiry
(via a mutable clock closure), scope isolation, non-positive TTL rejection,
and no-approval-ever-granted stays invalid.
