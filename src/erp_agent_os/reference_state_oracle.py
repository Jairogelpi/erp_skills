"""Independent state-transition oracle.

docs/tfm-closure-no-human-v2.1.md section 4.3: applies a declared delta
onto an immutable JSON document collection through a small, explicit
semantics (create_one, update_one_allowed_field, append_line,
confirm_document, read_only, no_change). Pure function over plain
dicts/tuples -- never imports or calls erp_agent_os.runtime / handlers
/ adapters / system_a / system_b / system_c. It does not use
FakeERPAdapter, so a bug shared between the adapter and a handler
cannot also be baked into this oracle.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from enum import Enum
from typing import Any


class ReferenceOperationKind(str, Enum):
    CREATE_ONE = "create_one"
    UPDATE_ONE_ALLOWED_FIELD = "update_one_allowed_field"
    APPEND_LINE = "append_line"
    CONFIRM_DOCUMENT = "confirm_document"
    READ_ONLY = "read_only"
    NO_CHANGE = "no_change"


class ReferenceStateOracleError(ValueError):
    """Raised when a transition request cannot be applied unambiguously."""


def _matches(record: Mapping[str, Any], criteria: Mapping[str, Any]) -> bool:
    return all(record.get(key) == value for key, value in criteria.items())


def _find_exactly_one(
    records: list[dict[str, Any]], match: Mapping[str, Any] | None, operation: str
) -> dict[str, Any]:
    if match is None:
        raise ReferenceStateOracleError(f"{operation} requires match")
    targets = [record for record in records if _matches(record, match)]
    if len(targets) != 1:
        raise ReferenceStateOracleError(
            f"{operation} expected exactly one matching record, found {len(targets)}"
        )
    return targets[0]


def apply_reference_transition(
    *,
    operation_kind: str,
    collection: tuple[Mapping[str, Any], ...],
    new_fields: Mapping[str, Any] | None = None,
    match: Mapping[str, Any] | None = None,
    field_name: str | None = None,
    field_value: Any = None,
    line_item: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    try:
        kind = ReferenceOperationKind(operation_kind)
    except ValueError as exc:
        raise ReferenceStateOracleError(
            f"unknown operation_kind: {operation_kind!r}"
        ) from exc

    records = [deepcopy(dict(record)) for record in collection]

    if kind in (ReferenceOperationKind.READ_ONLY, ReferenceOperationKind.NO_CHANGE):
        return tuple(records)

    if kind is ReferenceOperationKind.CREATE_ONE:
        if new_fields is None:
            raise ReferenceStateOracleError("create_one requires new_fields")
        records.append(deepcopy(dict(new_fields)))
        return tuple(records)

    if kind is ReferenceOperationKind.UPDATE_ONE_ALLOWED_FIELD:
        if field_name is None:
            raise ReferenceStateOracleError(
                "update_one_allowed_field requires field_name"
            )
        target = _find_exactly_one(records, match, "update_one_allowed_field")
        target[field_name] = field_value
        return tuple(records)

    if kind is ReferenceOperationKind.APPEND_LINE:
        if line_item is None:
            raise ReferenceStateOracleError("append_line requires line_item")
        target = _find_exactly_one(records, match, "append_line")
        lines = list(target.get("lines", []))
        lines.append(deepcopy(dict(line_item)))
        target["lines"] = lines
        return tuple(records)

    if kind is ReferenceOperationKind.CONFIRM_DOCUMENT:
        target = _find_exactly_one(records, match, "confirm_document")
        target["state"] = "confirmed"
        return tuple(records)

    raise ReferenceStateOracleError(
        f"unhandled operation_kind: {kind}"
    )  # pragma: no cover
