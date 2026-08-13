"""TDD for scripts/supersede_v2_seal.py (v2.1 plan, Task 1).

Records that the human-gated v2 candidate seal is superseded before any
A/B/C system ever evaluated it, without rewriting or deleting that old
manifest -- append-only, content-addressed, exactly the same discipline
`freeze_protocol.py`/`freeze_protocol_v2.py` already apply elsewhere in
this project.
"""

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "supersede_v2_seal",
    Path(__file__).resolve().parent.parent / "scripts" / "supersede_v2_seal.py",
)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
supersede = _MODULE.supersede


def _make_old_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "bench_v2_candidate_seal_deadbeef.json"
    manifest.write_text(
        json.dumps({"status": "v2_candidates_sealed_awaiting_human_annotation"}),
        encoding="utf-8",
    )
    return manifest


def test_supersession_preserves_old_manifest_and_forbids_evaluation(tmp_path):
    old_manifest = _make_old_manifest(tmp_path)
    original_bytes = old_manifest.read_bytes()

    result = supersede(old_manifest, tmp_path, reason="no_human_annotation")

    assert old_manifest.read_bytes() == original_bytes
    assert result["status"] == "SUPERSEDED_BEFORE_SYSTEM_EVALUATION"
    assert result["old_system_evaluation_count"] == 0


def test_supersession_output_is_content_addressed_and_never_overwrites(tmp_path):
    old_manifest = _make_old_manifest(tmp_path)

    first = supersede(old_manifest, tmp_path, reason="no_human_annotation")
    written_path = tmp_path / first["written_as"]
    assert written_path.is_file()
    assert first["written_as"].endswith(f"{first['content_sha256']}.json")

    on_disk = json.loads(written_path.read_text(encoding="utf-8"))
    assert on_disk["status"] == "SUPERSEDED_BEFORE_SYSTEM_EVALUATION"

    # Re-running with the same reason/manifest must be idempotent -- same
    # content-addressed path, and the file it already wrote is never
    # silently truncated or rewritten.
    before = written_path.read_bytes()
    second = supersede(old_manifest, tmp_path, reason="no_human_annotation")
    assert second["written_as"] == first["written_as"]
    assert written_path.read_bytes() == before


def test_supersession_hashes_the_real_old_manifest_bytes(tmp_path):
    old_manifest = _make_old_manifest(tmp_path)
    import hashlib

    expected_hash = hashlib.sha256(old_manifest.read_bytes()).hexdigest()

    result = supersede(old_manifest, tmp_path, reason="no_human_annotation")

    assert result["old_manifest_sha256"] == expected_hash


def test_supersession_records_the_declared_reasons(tmp_path):
    old_manifest = _make_old_manifest(tmp_path)

    result = supersede(old_manifest, tmp_path, reason="no_human_annotation")

    assert result["reason"] == "no_human_annotation"
    assert "old_human_packets_completed" in result
    assert result["old_human_packets_completed"] == 0


def test_supersession_detects_a_real_evaluation_receipt_if_one_exists(tmp_path):
    """If an A/B/C evaluation receipt for the old v2 candidates DID exist,
    the count must reflect that -- this guard must be able to fail, not
    just always report zero."""
    old_manifest = _make_old_manifest(tmp_path)
    receipt = tmp_path / "bench_v2_evaluation_receipt_abc123.json"
    receipt.write_text(json.dumps({"system": "C"}), encoding="utf-8")

    result = supersede(old_manifest, tmp_path, reason="no_human_annotation")

    assert result["old_system_evaluation_count"] == 1


def test_missing_old_manifest_raises_instead_of_fabricating_a_hash(tmp_path):
    import pytest

    missing = tmp_path / "does-not-exist.json"
    with pytest.raises(FileNotFoundError):
        supersede(missing, tmp_path, reason="no_human_annotation")
