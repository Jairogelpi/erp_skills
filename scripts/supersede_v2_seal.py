#!/usr/bin/env python
"""Record that the human-gated v2 candidate seal is superseded.

TFM Closure Without Human Annotation v2.1, Task 1
(docs/tfm-closure-no-human-v2.1.md section 2, "v2 sellado el 13-08-2026").

The 2026-08-13 candidate seal (data/prospective_v2/bench_v2_candidate_seal_
*.json) declared 120 candidates sealed and awaiting two human annotators
and two human state reviewers. No annotator is available, and this project
will not fabricate that review. This script does not delete or edit that
manifest -- it is kept byte-for-byte, for provenance -- it writes a
separate, append-only, content-addressed supersession receipt recording
that no A/B/C system ever evaluated those candidates before the decision
to redesign H1/H2/H3/H4/H7 as the no-human v2.1 protocol.

    uv run python scripts/supersede_v2_seal.py \
        --old-manifest data/prospective_v2/bench_v2_candidate_seal_<hash>.json \
        --output-dir data/protocol_v2_1
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SPEC_PATH = Path("docs/tfm-closure-no-human-v2.1.md")

REASONS = (
    "human_annotators_unavailable",
    "h1_h2_h3_h4_h7_redesigned_before_v2_results",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _count_system_evaluation_receipts(search_dir: Path) -> int:
    """A real A/B/C evaluation of the old v2 candidates would have left a
    receipt named bench_v2_evaluation_receipt_*.json next to the seal.
    None should exist; this must be able to detect one if it did, not
    just always report zero (see test_supersession_detects_a_real_
    evaluation_receipt_if_one_exists)."""
    return len(list(search_dir.glob("bench_v2_evaluation_receipt_*.json")))


def _count_completed_human_packets(search_dir: Path) -> int:
    """A completed annotation packet would have every row's decision
    column filled. The retired templates in data/prospective_v2 are
    header-plus-request-text-only; this counts genuinely completed ones
    so the claim 'zero human packets were completed' is checked, not
    assumed."""
    completed = 0
    for packet in search_dir.glob("*annotation*.csv"):
        import csv

        with packet.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if rows and all((row.get("annotated_decision") or "").strip() for row in rows):
            completed += 1
    return completed


def supersede(old_manifest: Path, output_dir: Path, *, reason: str) -> dict[str, Any]:
    if not old_manifest.is_file():
        raise FileNotFoundError(f"old manifest not found: {old_manifest}")

    old_bytes = old_manifest.read_bytes()
    old_hash = _sha256_bytes(old_bytes)
    search_dir = old_manifest.parent

    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "SUPERSEDED_BEFORE_SYSTEM_EVALUATION",
        "reason": reason,
        "reasons": list(REASONS),
        "old_manifest_path": old_manifest.name,
        "old_manifest_sha256": old_hash,
        "old_system_evaluation_count": _count_system_evaluation_receipts(search_dir),
        "old_human_packets_completed": _count_completed_human_packets(search_dir),
        "spec_path": str(SPEC_PATH).replace("\\", "/"),
        "spec_sha256": _sha256_file(SPEC_PATH) if SPEC_PATH.is_file() else None,
        "new_protocol_name": "ERP-Skills-Bench-Proc v2.1",
    }

    # content_sha256 is never written *inside* the file: a manifest cannot
    # hash itself without either a placeholder or an inconsistency between
    # the filename hash and the bytes actually on disk (the same trap
    # freeze_v2.py's own docstring warns against). The hash lives only in
    # the filename and in the value this function returns; a reader
    # verifies the artifact by hashing the file bytes and comparing them
    # to the name.
    canonical = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    content_hash = _sha256_bytes(canonical.encode("utf-8"))
    filename = f"v2_supersession_{content_hash}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / filename
    if not target.exists():
        target.write_text(canonical, encoding="utf-8")

    receipt["content_sha256"] = content_hash
    receipt["written_as"] = filename
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--old-manifest",
        type=Path,
        default=Path(
            "data/prospective_v2/"
            "bench_v2_candidate_seal_"
            "386fdf8b16f8283280d4f7127b1613fff5e0917e37a8bb11132896a06c63f037.json"
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/protocol_v2_1"))
    parser.add_argument("--reason", default="no_human_annotation")
    args = parser.parse_args(argv)

    result = supersede(args.old_manifest, args.output_dir, reason=args.reason)
    print(f"wrote {args.output_dir / result['written_as']}")
    print(f"status: {result['status']}")
    print(f"old_system_evaluation_count: {result['old_system_evaluation_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
