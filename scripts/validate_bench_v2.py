"""Validate the prospective v2 dataset and provenance without changing either."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from erp_agent_os.bench_v2 import (
    BenchV2Error,
    V2Case,
    V2Provenance,
    v1_request_hashes,
    validate_v2,
)

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data" / "bench_v2.jsonl"
    )
    parser.add_argument(
        "--provenance", type=Path, default=ROOT / "data" / "bench_v2_provenance.json"
    )
    args = parser.parse_args(argv)
    try:
        cases = [
            V2Case.model_validate_json(line)
            for line in args.dataset.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        provenance = V2Provenance.model_validate_json(
            args.provenance.read_text(encoding="utf-8")
        )
        validate_v2(
            cases,
            provenance,
            v1_hashes=v1_request_hashes(ROOT / "data" / "bench_v1.jsonl"),
        )
    except (OSError, ValueError, json.JSONDecodeError, BenchV2Error) as exc:
        print(f"BENCH V2 INVALID: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("BENCH V2 VALID: 120 new cases, 5 per frozen intent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
