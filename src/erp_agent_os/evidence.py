"""Immutable, inspectable evidence archives for future experiment runs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from erp_agent_os.metrics import ExecutionRecord

OBSERVATION_SCHEMA_VERSION = "1.0"


def write_content_addressed(
    content: bytes, path_for_digest: Callable[[str], Path]
) -> tuple[Path, str]:
    """Shared, atomic, content-addressed write used by both the v1
    observation archive below and erp_agent_os.evidence_v2_1's archive.

    `path_for_digest` turns the content's own SHA-256 into the concrete
    destination path -- the caller decides the filename convention, this
    function only guarantees the write is atomic (temp file + os.replace)
    and that an existing file at that address is never silently
    overwritten with different bytes."""
    digest = hashlib.sha256(content).hexdigest()
    destination = path_for_digest(digest)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if destination.read_bytes() != content:
            raise FileExistsError(
                f"content-addressed archive has conflicting bytes: {destination}"
            )
        return destination, digest

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
    return destination, digest


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


def trace_from_execution_record(record: ExecutionRecord) -> dict[str, Any]:
    """Adapts a v1 ExecutionRecord into the flat trace shape
    erp_agent_os.audit_reconstruction.reconstruct() expects (v2.1 Task 6).

    v1's ExecutionRecord was never designed to carry every field H7's
    seven-fact reconstruction wants (it has no request_text, no explicit
    case_id, no approval_evidence) -- this adapter does not fabricate
    them. Facts that genuinely cannot be recovered from a v1 record
    correctly read as missing when reconstructed, which is itself
    accurate information about v1's audit trail, not a bug in the
    adapter to paper over.
    """
    _placeholder = {"not_available", ""}
    return {
        "correlation_id": record.request_id,
        "request_text": None,  # not carried by v1's ExecutionRecord
        "case_id": record.request_id,
        "case_id_matches_correlation": True,
        "intent": None,  # not carried by v1's ExecutionRecord
        "arguments": record.normalized_arguments or None,
        "selected_skill_id": record.selected_skill_id,
        "abstained": record.decision == "ABSTAIN",
        "policy_decision": record.decision,
        "role": None if record.role in _placeholder else record.role,
        "skill_version": record.selected_skill_version,
        "handler": None if record.handler_name in _placeholder else record.handler_name,
        "execution_output": record.final_state if record.final_state else None,
        "observed_state_delta": {
            "operation_kind": "no_change" if record.state_unchanged else "mutated"
        },
        "verification_status": (
            "passed"
            if record.postconditions_met is True
            else "failed"
            if record.postconditions_met is False
            else None
        ),
        "approval_evidence": None,  # not carried by v1's ExecutionRecord
        "final_decision_allowed": record.decision == "ALLOW",
    }


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
    destination, digest = write_content_addressed(
        content, lambda d: observations_path_for(report_path, d)
    )
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
