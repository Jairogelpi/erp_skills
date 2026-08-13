"""Write or verify the prospective v2 protocol manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from erp_agent_os.freeze_v2 import (
    FreezeManifestV2,
    build_manifest,
    git_output,
    load_run_config,
    verify_manifest,
    write_json_atomic,
)

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "bench_v2_freeze_manifest.json"
RUN_CONFIG = ROOT / "data" / "bench_v2_run_config.json"
REQUIRED = [
    "data/bench_v2.jsonl",
    "data/bench_v2_provenance.json",
    "data/bench_v2_run_config.json",
    "src/erp_agent_os/catalog.py",
    "src/erp_agent_os/policy.py",
    "src/erp_agent_os/metrics.py",
    "src/erp_agent_os/experiment_v2.py",
    "src/erp_agent_os/experiment.py",
    "src/erp_agent_os/system_a.py",
    "src/erp_agent_os/system_b.py",
    "src/erp_agent_os/system_c.py",
    "docs/experiment-protocol.md",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = load_run_config(RUN_CONFIG)
        if args.write:
            if git_output(ROOT, "status", "--porcelain"):
                raise ValueError("write freeze only from a clean pre-freeze worktree")
            manifest = build_manifest(
                ROOT,
                run_config=config,
                required_files=REQUIRED,
                git_commit=git_output(ROOT, "rev-parse", "HEAD"),
            )
            write_json_atomic(MANIFEST, manifest)
            print("v2 manifest written; commit and tag it before any execution")
        else:
            manifest = FreezeManifestV2.model_validate_json(
                MANIFEST.read_text(encoding="utf-8")
            )
            verify_manifest(ROOT, manifest, run_config=config, require_clean_tag=True)
            print("v2 freeze verified at tagged clean commit")
    except Exception as exc:
        print(f"V2 FREEZE INVALID: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
