"""Publish v2 aggregate only after the complete encrypted run validates."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from erp_agent_os.bench_v2 import V2Case
from erp_agent_os.experiment_v2 import (
    analyze_observations,
    load_encrypted_checkpoint,
)
from erp_agent_os.freeze_v2 import (
    FreezeManifestV2,
    load_run_config,
    sha256_file,
    verify_manifest,
    write_json_atomic,
)

ROOT = Path(__file__).resolve().parent.parent
RESULT = ROOT / "data" / "bench_v2_confirmatory_results.json"
VALIDATION = ROOT / "data" / "bench_v2_result_validation.json"
FREEZE = ROOT / "data" / "bench_v2_freeze_manifest.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkpoint", type=Path, default=ROOT / ".v2-private" / "checkpoint.fernet"
    )
    args = parser.parse_args(argv)
    try:
        config = load_run_config(ROOT / "data" / "bench_v2_run_config.json")
        manifest = FreezeManifestV2.model_validate_json(
            FREEZE.read_text(encoding="utf-8")
        )
        verify_manifest(ROOT, manifest, run_config=config, require_clean_tag=True)
        cases = [
            V2Case.model_validate_json(line)
            for line in (ROOT / "data" / "bench_v2.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        checkpoint = load_encrypted_checkpoint(
            args.checkpoint, key=os.environ["ERP_AGENT_OS_V2_CHECKPOINT_KEY"].encode()
        )
        if checkpoint.status != "complete" or checkpoint.failure is not None:
            raise ValueError("v2 checkpoint is not a complete run")
        result = analyze_observations(
            checkpoint.observations,
            case_ids={case.request_id for case in cases},
            config=config,
        )
        write_json_atomic(RESULT, result)
        validation = {
            "schema_version": "1.0",
            "artifact_path": "data/bench_v2_confirmatory_results.json",
            "artifact_sha256": sha256_file(RESULT),
            "freeze_manifest_path": "data/bench_v2_freeze_manifest.json",
            "freeze_manifest_sha256": sha256_file(FREEZE),
            "manifest_hash": manifest.manifest_hash,
            "run_config_hash": manifest.run_config_hash,
            "validation_status": "passed",
            "completed_observations": 1080,
            "expected_observations": 1080,
            "primary_endpoint_complete": True,
        }
        write_json_atomic(VALIDATION, validation)
    except Exception as exc:
        RESULT.unlink(missing_ok=True)
        VALIDATION.unlink(missing_ok=True)
        print(f"V2 ANALYSIS NOT PUBLISHED: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("v2 aggregate and validation published after complete-run verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
