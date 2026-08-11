"""Does retrieval survive contact with real user text? (product number 3)

`docs/retriever-comparison.md` shows TF-IDF beating embeddings and the
hybrid ranker on ERP-Skills-Bench. That corpus is **templated**: the
request and the skill description share a lot of vocabulary
("crea una oportunidad" / "Crea una oportunidad comercial..."), which is
exactly the signal TF-IDF exploits. Real users do not phrase things that
way, so that result may not transfer at all -- and if it does not, the
retriever is the wrong component and it is far cheaper to learn that now
than after building a product on it.

This script evaluates the same three retrievers over a CSV of **real**
requests, using the same metric code as the benchmark comparison so the
two numbers are directly comparable.

Input CSV (`data/real_requests.csv` by default), UTF-8, header row:

    request_text,expected_skill

  - `request_text`: what a person actually wrote or said, verbatim.
    Do not clean it up, do not translate it into catalog vocabulary --
    the typos and the vagueness ARE the measurement.
  - `expected_skill`: the catalog skill id that should handle it, or
    empty if no catalog skill fits and the system ought to abstain.

    uv run python scripts/eval_real_requests.py

Writes `data/real_requests_eval.json`. Reads nothing from the frozen
benchmark and writes nothing near it.
"""

import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

from erp_agent_os.catalog import CATALOG

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "real_requests.csv"
OUTPUT_PATH = ROOT / "data" / "real_requests_eval.json"

# Benchmark reference point (docs/retriever-comparison.md, VALIDATION
# split). The question this script answers is how far below these the
# real-text numbers land.
BENCHMARK_VALIDATION_TOP1 = {"tfidf": 0.733, "embeddings": 0.658, "hybrid": 0.675}

# Below this, the confidence interval is so wide that the answer is
# "we do not know yet", and reporting a point estimate would invite
# exactly the kind of over-reading this project keeps correcting.
MIN_USEFUL_SAMPLE = 30


class _Case:
    """Duck-typed stand-in for BenchmarkCase: the metric code needs
    `request_text` and `expected_skill` and nothing else."""

    def __init__(self, request_text: str, expected_skill: str | None) -> None:
        self.request_text = request_text
        self.expected_skill = expected_skill


def _load_comparison_module() -> Any:
    """Reuse the benchmark's own evaluation code, not a copy of it.

    A second implementation of the same metric would drift from the
    first, and then the two numbers would stop being comparable --
    which is the entire point of this script.
    """
    path = ROOT / "scripts" / "compare_retrievers.py"
    spec = importlib.util.spec_from_file_location("compare_retrievers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wilson(successes: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _load_cases(path: Path) -> list[_Case]:
    if not path.exists():
        raise SystemExit(
            f"no input at {path}. Create it with the header "
            "'request_text,expected_skill' and one real request per row. "
            "See data/real_requests.template.csv."
        )

    valid_ids = {s.skill_id for s in CATALOG}
    cases: list[_Case] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            text = (row.get("request_text") or "").strip()
            skill = (row.get("expected_skill") or "").strip()
            if not text:
                continue
            if skill and skill not in valid_ids:
                # Loudly, not silently: a typo'd skill id would count as
                # a retrieval miss forever and quietly depress the score.
                raise SystemExit(
                    f"row {row_number}: unknown skill id {skill!r}. "
                    f"Valid ids: {sorted(valid_ids)}"
                )
            cases.append(_Case(text, skill or None))
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.15,
        help="abstention score threshold (default: the governed pipeline's)",
    )
    parser.add_argument("--margin", type=float, default=0.05)
    args = parser.parse_args()

    comparison = _load_comparison_module()
    cases = _load_cases(args.input)

    if not cases:
        raise SystemExit(f"{args.input} has no usable rows")

    n_expected = sum(1 for c in cases if c.expected_skill)
    n_abstain = len(cases) - n_expected

    report: dict[str, Any] = {
        "source": str(args.input.name),
        "question": (
            "does retrieval survive real user text, or was the benchmark "
            "result an artefact of templated phrasing?"
        ),
        "n_requests": len(cases),
        "n_with_expected_skill": n_expected,
        "n_expected_abstention": n_abstain,
        "abstention_rule": {"threshold": args.threshold, "margin": args.margin},
        "benchmark_validation_top1": BENCHMARK_VALIDATION_TOP1,
        "retrievers": {},
    }

    # Two populations, measured separately. Mixing them was a real defect
    # in the first version of this script: requests that no skill covers
    # can never contribute to Top-1, so including them in its denominator
    # caps the metric at n_expected/n and makes the benchmark comparison
    # meaningless (the benchmark corpus is almost entirely answerable).
    answerable = [c for c in cases if c.expected_skill]
    out_of_catalog = [c for c in cases if not c.expected_skill]

    for name, retriever in comparison._build_retrievers().items():
        metrics = comparison._evaluate(
            comparison._rank_all(retriever, answerable),
            answerable,
            threshold=args.threshold,
            margin=args.margin,
        )
        top1 = float(metrics["top1"])
        low, high = _wilson(top1 * len(answerable), len(answerable))
        metrics["top1_ci95"] = [round(low, 3), round(high, 3)]
        baseline = BENCHMARK_VALIDATION_TOP1.get(name)
        if baseline is not None:
            metrics["top1_vs_benchmark"] = round(top1 - baseline, 3)

        # The failure that actually hurts in production: committing to
        # some skill when the right answer was "I do not handle this".
        if out_of_catalog:
            rankings = comparison._rank_all(retriever, out_of_catalog)
            abstained = sum(
                1
                for ranked in rankings
                if comparison.should_abstain(
                    ranked, [], threshold=args.threshold, margin=args.margin
                )
            )
            metrics["out_of_catalog_n"] = len(out_of_catalog)
            metrics["out_of_catalog_correct_abstention"] = round(
                abstained / len(out_of_catalog), 3
            )
        report["retrievers"][name] = metrics

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"{len(cases)} peticiones reales: {n_expected} contestables por el "
        f"catalogo, {n_abstain} fuera de el\n"
    )
    print("Sobre las CONTESTABLES (comparable con el benchmark):")
    header = f"  {'recuperador':12} {'Top-1':>7} {'IC95':>16}"
    print(f"{header} {'vs bench':>9} {'sel.acc':>8}")
    for name, m in report["retrievers"].items():
        ci = m["top1_ci95"]
        delta = m.get("top1_vs_benchmark")
        delta_text = f"{delta:+.3f}" if delta is not None else "--"
        print(
            f"  {name:12} {m['top1']:>7.3f} "
            f"[{ci[0]:.3f}, {ci[1]:.3f}] {delta_text:>9} "
            f"{m['selective_accuracy']:>8.3f}"
        )
    if n_abstain:
        print("\nSobre las FUERA DE CATALOGO (deberia abstenerse en todas):")
        for name, m in report["retrievers"].items():
            rate = m.get("out_of_catalog_correct_abstention", 0.0)
            print(f"  {name:12} se abstiene bien en {rate:.3f}")

    if len(cases) < MIN_USEFUL_SAMPLE:
        print(
            f"\nAVISO: {len(cases)} peticiones es una muestra demasiado pequeña. "
            f"El intervalo es tan ancho que la respuesta honesta es 'aún no se "
            f"sabe'. Reúne al menos {MIN_USEFUL_SAMPLE}, idealmente 100-200, "
            "antes de tomar cualquier decisión de producto con este número."
        )
    print(f"\nescrito en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
