"""Does the LLM router survive real text where TF-IDF did not?

`docs/product-viability.md` §7.2 measured TF-IDF collapsing from 0.733
(benchmark) to 0.381 on real colloquial requests. That leaves exactly
one question open, and it decides whether the thesis' C > B result
transfers outside the corpus:

  - if the LLM selector **also** collapses, the problem is the 12-skill
    catalog itself, and the C vs B comparison stands as measured;
  - if the LLM selector **holds up**, the problem is TF-IDF specifically,
    and C's advantage over B does not survive real text -- which must be
    said plainly in the memoria.

Uses System B's exact tool surface (`TYPED_TOOLS`: the same 12 skill ids,
descriptions and required fields the paired experiment gave it) and the
same `propose_action` prompt, so the two numbers are comparable to the
benchmark ones and to each other.

Requires a real provider key (GROQ_API_KEY by default). Reads
`data/real_requests.csv`, writes `data/real_requests_llm_eval.json`.

    uv run python scripts/eval_real_requests_llm.py
"""

import argparse
import csv
import json
import math
import time
from pathlib import Path
from typing import Any

from erp_agent_os.catalog import CATALOG_BY_ID
from erp_agent_os.llm_client import ToolSpec
from erp_agent_os.system_b import TYPED_TOOLS

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "real_requests.csv"
OUTPUT_PATH = ROOT / "data" / "real_requests_llm_eval.json"

# Measured on the same 84 answerable requests, so the comparison is
# like-for-like (docs/product-viability.md §7.2).
TFIDF_REAL_TOP1 = 0.381
TFIDF_REAL_OUT_OF_CATALOG_ABSTENTION = 0.389
# Benchmark reference for the LLM selector (docs/results.md, H5).
LLM_BENCHMARK_TOP1 = 0.898


def _wilson(successes: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _load(path: Path) -> list[tuple[str, str | None]]:
    valid = set(CATALOG_BY_ID)
    rows: list[tuple[str, str | None]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            text = (row.get("request_text") or "").strip()
            skill = (row.get("expected_skill") or "").strip()
            if not text:
                continue
            if skill and skill not in valid:
                raise SystemExit(f"row {line_number}: unknown skill id {skill!r}")
            rows.append((text, skill or None))
    return rows


def _client(provider: str) -> Any:
    if provider == "groq":
        from erp_agent_os.groq_client import GroqClient

        return GroqClient()
    if provider == "openrouter":
        from erp_agent_os.openrouter_client import OpenRouterClient

        return OpenRouterClient()
    if provider == "gemini":
        from erp_agent_os.gemini_client import GeminiClient

        return GeminiClient()
    raise SystemExit(f"unknown provider {provider!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--provider", default="groq", choices=("groq", "openrouter", "gemini")
    )
    args = parser.parse_args()

    rows = _load(args.input)
    llm = _client(args.provider)
    tools: list[ToolSpec] = TYPED_TOOLS

    answerable_hits = 0
    answerable_total = 0
    out_total = 0
    out_correctly_refused = 0
    details: list[dict[str, Any]] = []

    started = time.monotonic()
    for index, (text, expected) in enumerate(rows, start=1):
        call = llm.propose_action(text, tools)
        chosen = call.tool_name if call.tool_name in CATALOG_BY_ID else None

        if expected:
            answerable_total += 1
            hit = chosen == expected
            answerable_hits += int(hit)
        else:
            out_total += 1
            # The failure that hurts: committing to some skill when the
            # right answer was "no tool of mine handles this".
            out_correctly_refused += int(chosen is None)

        details.append({"expected": expected, "chosen": chosen})
        if index % 20 == 0:
            print(f"  {index}/{len(rows)} ({time.monotonic() - started:.0f}s)")

    top1 = answerable_hits / answerable_total if answerable_total else 0.0
    low, high = _wilson(answerable_hits, answerable_total)
    refusal = out_correctly_refused / out_total if out_total else 0.0

    report = {
        "source": args.input.name,
        "provider": type(llm).__name__,
        "question": (
            "does the LLM router survive real text where TF-IDF did not? "
            "If it also collapses, the catalog is the problem; if it holds, "
            "TF-IDF is, and C's edge over B does not transfer."
        ),
        "n_answerable": answerable_total,
        "n_out_of_catalog": out_total,
        "llm_top1": round(top1, 3),
        "llm_top1_ci95": [round(low, 3), round(high, 3)],
        "llm_out_of_catalog_correct_refusal": round(refusal, 3),
        "comparison": {
            "llm_benchmark_top1": LLM_BENCHMARK_TOP1,
            "llm_real_minus_benchmark": round(top1 - LLM_BENCHMARK_TOP1, 3),
            "tfidf_real_top1": TFIDF_REAL_TOP1,
            "llm_real_minus_tfidf_real": round(top1 - TFIDF_REAL_TOP1, 3),
            "tfidf_real_out_of_catalog_abstention": (
                TFIDF_REAL_OUT_OF_CATALOG_ABSTENTION
            ),
        },
        "details": details,
    }
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nselector LLM ({report['provider']}) sobre texto real\n")
    print(f"  Top-1 contestables : {top1:.3f}  IC95 [{low:.3f}, {high:.3f}]")
    print(f"    vs benchmark     : {top1 - LLM_BENCHMARK_TOP1:+.3f}")
    print(f"    vs TF-IDF real   : {top1 - TFIDF_REAL_TOP1:+.3f}")
    print(
        f"  Rechaza bien fuera de catalogo: {refusal:.3f} "
        f"(TF-IDF: {TFIDF_REAL_OUT_OF_CATALOG_ABSTENTION:.3f})"
    )
    print(f"\nescrito en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
