"""Run frozen A/B/C units into an encrypted, non-reportable checkpoint."""

from __future__ import annotations

import argparse
import importlib
import inspect
import os
import sys
from pathlib import Path

from erp_agent_os.bench_v2 import V2Case
from erp_agent_os.experiment_v2 import run_protocol
from erp_agent_os.freeze_v2 import (
    FreezeManifestV2,
    load_run_config,
    sha256_file,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parent.parent


def _load_executor(path: str, manifest: FreezeManifestV2):
    module_name, function_name = path.split(":", 1)
    function = getattr(importlib.import_module(module_name), function_name)
    source = inspect.getsourcefile(function)
    if source is None:
        raise ValueError("executor has no frozen source file")
    source_path = Path(source).resolve()
    relative = source_path.relative_to(ROOT.resolve()).as_posix()
    if manifest.files.get(relative) != sha256_file(source_path):
        raise ValueError("executor source is not part of the verified freeze")
    return function


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executor", required=True, help="trusted module:function")
    parser.add_argument(
        "--checkpoint", type=Path, default=ROOT / ".v2-private" / "checkpoint.fernet"
    )
    args = parser.parse_args(argv)
    try:
        config = load_run_config(ROOT / "data" / "bench_v2_run_config.json")
        manifest = FreezeManifestV2.model_validate_json(
            (ROOT / "data" / "bench_v2_freeze_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        verify_manifest(ROOT, manifest, run_config=config, require_clean_tag=True)
        key = os.environ["ERP_AGENT_OS_V2_CHECKPOINT_KEY"].encode()
        cases = [
            V2Case.model_validate_json(line)
            for line in (ROOT / "data" / "bench_v2.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
        run_protocol(
            cases,
            config=config,
            execute=_load_executor(args.executor, manifest),
            checkpoint_path=args.checkpoint,
            checkpoint_key=key,
        )
    except Exception as exc:
        print(f"V2 RUN STOPPED: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("v2 run complete: encrypted checkpoint contains 1,080 observations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
