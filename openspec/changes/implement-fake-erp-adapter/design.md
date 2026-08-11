# Design: FakeERPAdapter

## Contract

```python
class FakeERPAdapter:
    def __init__(self, allowed_models: set[str]) -> None: ...
    def create(self, model: str, fields: dict) -> str: ...
    def get(self, model: str, record_id: str) -> dict: ...
    def update(self, model: str, record_id: str, fields: dict) -> None: ...
    def snapshot(self) -> dict: ...
    def restore(self, snapshot: dict) -> None: ...
```

## Alternatives considered

- **Hardcode the eight ERP-family models now** (res.partner, crm.lead,
  sale.order, ...): rejected. The skill contract (next change) is what
  defines which models/operations a skill may touch; baking model names into
  the adapter ahead of that contract risks mismatch and rework. The
  allowlist is a constructor parameter instead, so each caller (later: the
  runtime, informed by the skill contract) declares scope explicitly.
- **Copy-on-write / reference snapshot**: rejected. `deepcopy` on
  snapshot/restore is simplest and correct at benchmark scale (480 cases);
  aliasing bugs would silently break the "state restored per observation"
  guarantee that STSR depends on (CLAUDE.md §19).

## Risks

- `deepcopy` cost is irrelevant at this record volume; revisit only if
  profiling during the piloto (phase 8) shows otherwise.
- No thread-safety: FakeERP is single-threaded per confirmatory observation,
  matching the sequential restore-then-execute protocol in CLAUDE.md §19.

## Test strategy

Focused `tests/test_fake_erp.py`: allowlist rejection, unknown-record
rejection, snapshot/restore reverting a create, and snapshot/restore
reverting an update taken *after* the snapshot (proves independence from the
live store, not just from the initial empty state).
