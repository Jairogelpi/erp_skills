"""Observed FakeERP states kept separate from benchmark truth annotations."""

import hashlib
import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from erp_agent_os.dataset import DATASET_SCHEMA_VERSION, BenchmarkCase
from erp_agent_os.experiment import _run_system_c
from erp_agent_os.freeze import load_manifest
from erp_agent_os.llm_client import DeterministicStubClient

OBSERVED_STATE_SCHEMA_VERSION = "1.0"


def build_observed_state_rows(
    cases: Sequence[BenchmarkCase],
) -> list[dict[str, Any]]:
    """Run deterministic System C once per case; these rows are not labels."""
    client = DeterministicStubClient()
    rows: list[dict[str, Any]] = []
    for case in cases:
        record = _run_system_c(case, client, repetition=0)
        rows.append(
            {
                "schema_version": OBSERVED_STATE_SCHEMA_VERSION,
                "request_id": case.request_id,
                "evidence_role": "system_observation_not_oracle",
                "oracle_status": "pending_independent_review",
                "system": "C",
                "selector": type(client).__name__,
                "initial_state_observed": record.initial_state,
                "final_state_observed": record.final_state,
                "decision_observed": record.decision,
                "selected_skill_observed": record.selected_skill_id,
                "postconditions_met_observed": record.postconditions_met,
                "state_unchanged_observed": record.state_unchanged,
            }
        )
    return rows


def _archive_bytes(rows: list[dict[str, Any]]) -> bytes:
    manifest = {
        "type": "manifest",
        "schema_version": OBSERVED_STATE_SCHEMA_VERSION,
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "evidence_role": "system_observation_not_oracle",
        "oracle_status": "pending_independent_review",
        "row_count": len(rows),
        "freeze_hashes": asdict(load_manifest()),
    }
    lines = [json.dumps(manifest, sort_keys=True, ensure_ascii=False)]
    lines.extend(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows)
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_observed_state_archive(
    cases: Sequence[BenchmarkCase], destination_dir: Path
) -> Path:
    rows = build_observed_state_rows(cases)
    content = _archive_bytes(rows)
    digest = hashlib.sha256(content).hexdigest()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"bench_v1_observed_states_{digest}.jsonl"
    if destination.exists():
        if destination.read_bytes() != content:
            raise FileExistsError(f"hash collision at {destination}")
        return destination

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination_dir
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination
