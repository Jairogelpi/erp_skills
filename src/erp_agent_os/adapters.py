"""Deterministic, restorable synthetic ERP adapter (FakeERP).

Scope per CLAUDE.md §14/§19 and openspec project-context: allowlisted
create/read/update on in-memory records, plus exact snapshot/restore so a
confirmatory observation can reset state between repetitions. No delete, no
external I/O, no policy/runtime/skill behavior.
"""

from copy import deepcopy
from typing import Any, Protocol, runtime_checkable


class UnknownModelError(ValueError):
    """Raised when an operation targets a model outside the allowlist."""


class UnknownRecordError(KeyError):
    """Raised when an operation targets a record id that does not exist."""


class DuplicateRecordError(ValueError):
    """Raised when `create` is given a `record_id` that already exists."""


@runtime_checkable
class ErpAdapter(Protocol):
    """The subset of adapter behaviour handlers/Runtime actually call.

    Both `FakeERPAdapter` and `Odoo19Adapter` satisfy this structurally
    (PEP 544, no inheritance needed): the point is that `Runtime`,
    `postconditions.py` and every skill handler can be typed against
    this Protocol instead of the concrete `FakeERPAdapter`, so a real
    adapter is a genuine, statically-typed drop-in, not just something
    that happens to work at runtime via duck typing. `create`'s
    `record_id` kwarg is FakeERPAdapter-specific (used only to seed
    confirmatory-experiment state, CLAUDE.md §19) and deliberately not
    part of this Protocol -- no handler calls it.
    """

    def create(self, model: str, fields: dict[str, Any]) -> str: ...
    def get(self, model: str, record_id: str) -> dict[str, Any]: ...
    def list(self, model: str) -> dict[str, dict[str, Any]]: ...
    def update(self, model: str, record_id: str, fields: dict[str, Any]) -> None: ...


class FakeERPAdapter:
    """In-memory ERP state, restricted to an explicit model allowlist."""

    def __init__(self, allowed_models: set[str]) -> None:
        self._allowed_models = frozenset(allowed_models)
        self._records: dict[str, dict[str, dict[str, Any]]] = {
            model: {} for model in self._allowed_models
        }
        self._next_id = 1

    def _require_model(self, model: str) -> dict[str, dict[str, Any]]:
        if model not in self._allowed_models:
            raise UnknownModelError(model)
        return self._records[model]

    def create(
        self, model: str, fields: dict[str, Any], record_id: str | None = None
    ) -> str:
        table = self._require_model(model)
        if record_id is not None:
            if record_id in table:
                raise DuplicateRecordError(record_id)
        else:
            record_id = str(self._next_id)
            self._next_id += 1
        table[record_id] = deepcopy(fields)
        return record_id

    def get(self, model: str, record_id: str) -> dict[str, Any]:
        table = self._require_model(model)
        if record_id not in table:
            raise UnknownRecordError(record_id)
        return deepcopy(table[record_id])

    def list(self, model: str) -> dict[str, dict[str, Any]]:
        return deepcopy(self._require_model(model))

    def update(self, model: str, record_id: str, fields: dict[str, Any]) -> None:
        table = self._require_model(model)
        if record_id not in table:
            raise UnknownRecordError(record_id)
        table[record_id].update(deepcopy(fields))

    def snapshot(self) -> dict[str, Any]:
        return {
            "records": deepcopy(self._records),
            "next_id": self._next_id,
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._records = deepcopy(snapshot["records"])
        self._next_id = snapshot["next_id"]
