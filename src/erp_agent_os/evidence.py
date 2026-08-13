"""Immutable, inspectable evidence archives for future experiment runs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from erp_agent_os.metrics import ExecutionRecord

OBSERVATION_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ObservationArchive:
    path: Path
    sha256: str
    row_count: int


@dataclass(frozen=True)
class LoadedObservations:
    schema_version: str
    provenance: dict[str, Any]
    records: list[ExecutionRecord]


def execution_record_to_dict(record: ExecutionRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["ranked_skill_ids"] = list(record.ranked_skill_ids)
    payload["policy_reasons"] = list(record.policy_reasons)
    return payload


def execution_record_from_dict(payload: dict[str, Any]) -> ExecutionRecord:
    normalized = dict(payload)
    normalized["ranked_skill_ids"] = tuple(normalized.get("ranked_skill_ids", ()))
    normalized["policy_reasons"] = tuple(normalized.get("policy_reasons", ()))
    return ExecutionRecord(**normalized)


def _archive_bytes(records: list[ExecutionRecord], provenance: dict[str, Any]) -> bytes:
    header = {
        "type": "manifest",
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "provenance": provenance,
        "row_count": len(records),
    }
    rows = [json.dumps(header, sort_keys=True, ensure_ascii=False)]
    rows.extend(
        json.dumps(
            {"type": "observation", "record": execution_record_to_dict(record)},
            sort_keys=True,
            ensure_ascii=False,
        )
        for record in records
    )
    return ("\n".join(rows) + "\n").encode("utf-8")


def observations_path_for(report_path: Path, sha256: str) -> Path:
    return report_path.with_name(f"{report_path.stem}_observations_{sha256}.jsonl")


def write_observations_jsonl(
    records: list[ExecutionRecord],
    report_path: Path,
    *,
    provenance: dict[str, Any],
) -> ObservationArchive:
    """Write an atomic, content-addressed archive without silent overwrite."""
    content = _archive_bytes(records, provenance)
    digest = hashlib.sha256(content).hexdigest()
    destination = observations_path_for(report_path, digest)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if destination.read_bytes() != content:
            raise FileExistsError(
                f"content-addressed archive has conflicting bytes: {destination}"
            )
        return ObservationArchive(destination, digest, len(records))

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(destination)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return ObservationArchive(destination, digest, len(records))


def load_observations_jsonl(path: Path) -> LoadedObservations:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows or rows[0].get("type") != "manifest":
        raise ValueError("observation archive is missing its manifest row")
    header = rows[0]
    records = [
        execution_record_from_dict(row["record"])
        for row in rows[1:]
        if row.get("type") == "observation"
    ]
    if header.get("row_count") != len(records):
        raise ValueError("observation archive row count does not match manifest")
    return LoadedObservations(
        schema_version=header["schema_version"],
        provenance=dict(header.get("provenance", {})),
        records=records,
    )


def validate_observation_units(
    records: list[ExecutionRecord],
    *,
    request_ids: set[str],
    systems: set[str],
    repetitions: int,
) -> None:
    actual = [(r.request_id, r.system, r.repetition) for r in records]
    unique = set(actual)
    if len(unique) != len(actual):
        raise ValueError("duplicate observation unit")
    expected = {
        (request_id, system, repetition)
        for request_id in request_ids
        for system in systems
        for repetition in range(repetitions)
    }
    missing = expected - unique
    extra = unique - expected
    if missing:
        raise ValueError(f"missing observation units: {len(missing)}")
    if extra:
        raise ValueError(f"unexpected observation units: {len(extra)}")
