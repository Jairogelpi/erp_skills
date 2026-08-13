"""Generate v2 from offline author-model responses; never self-labels cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from erp_agent_os.bench_v2 import (
    RecordedAuthor,
    generate_v2,
    v1_request_hashes,
    validate_v2,
)

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--author-provider", required=True)
    parser.add_argument("--author-model", required=True)
    parser.add_argument("--selector-provider", required=True)
    parser.add_argument("--selector-model", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "bench_v2.jsonl")
    parser.add_argument(
        "--provenance", type=Path, default=ROOT / "data" / "bench_v2_provenance.json"
    )
    args = parser.parse_args(argv)
    try:
        responses = json.loads(args.responses.read_text(encoding="utf-8"))
        if not isinstance(responses, list) or not all(
            isinstance(x, str) for x in responses
        ):
            raise ValueError
        cases, provenance = generate_v2(
            author=RecordedAuthor(
                provider=args.author_provider, model=args.author_model, texts=responses
            ),
            selector_provider=args.selector_provider,
            selector_model=args.selector_model,
        )
        validate_v2(
            cases,
            provenance,
            v1_hashes=v1_request_hashes(ROOT / "data" / "bench_v1.jsonl"),
        )
        case_payload = "".join(case.model_dump_json() + "\n" for case in cases)
        provenance_payload = provenance.model_dump_json(indent=2) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.provenance.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(case_payload, encoding="utf-8")
        args.provenance.write_text(provenance_payload, encoding="utf-8")
    except Exception:
        print("BENCH V2 GENERATION FAILED; no valid dataset produced", file=sys.stderr)
        return 1
    print("bench v2 generated and validated: 120 cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
