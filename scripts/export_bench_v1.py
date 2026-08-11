"""Export the generated ERP-Skills-Bench v1 cases to data/bench_v1.jsonl.

One JSON object per line, `BenchmarkCase.model_dump(mode="json")`. Run:
    uv run python scripts/export_bench_v1.py
Deterministic: re-running overwrites the file with byte-identical content
(same seed, same generation order).
"""

import json
from pathlib import Path

from erp_agent_os.bench_generator import generate_cases

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "bench_v1.jsonl"


def main() -> None:
    cases = generate_cases()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case.model_dump(mode="json"), ensure_ascii=False) + "\n")
    print(f"wrote {len(cases)} cases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
