"""Compare the three retrievers CLAUDE.md §22 mandates.

§22 specifies a lexical baseline (TF-IDF), a sentence-embedding
retriever, and a hybrid ranker, and says the comparison is between all
three. The confirmatory experiment has always used TF-IDF only, so this
comparison had never been run -- `embeddings.py` and `HybridRetriever`
were implemented and tested but never evaluated against each other.

**Tuning discipline (§19, §22).** §22 states plainly: "Los pesos se
ajustarán solamente con los conjuntos de desarrollo y validación". This
script therefore reports on DEVELOPMENT and VALIDATION by default.
Touching FINAL_TEST requires `--test`, which exists so the chosen
configuration can be reported once, after it was selected elsewhere --
not so alternatives can be compared on the frozen split until one wins.
Choosing a retriever by its test score would be tuning on test, which
invalidates the confirmatory result (§19).

Retrieval is measured on its own terms here (Top-1/Top-3/MRR/coverage/
selective accuracy/false-reuse risk, §20), without executing anything:
no policy engine, no runtime, no ERP writes.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.catalog import CATALOG
from erp_agent_os.dataset import BenchmarkCase, DatasetSplit
from erp_agent_os.retrieval import (
    HybridRetriever,
    HybridWeights,
    TfidfRetriever,
    should_abstain,
)

ROLE = "erp_user"
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "retriever_comparison.json"
)


def _rank_all(retriever: Any, cases: list[BenchmarkCase]) -> list[Any]:
    """Rank every case once.

    Rankings do not depend on the abstention thresholds -- only the
    decision to commit does -- so the threshold sweep reuses these
    instead of re-embedding every query 42 times.
    """
    return [retriever.rank(case.request_text, role=ROLE) for case in cases]


def _evaluate(
    rankings: list[Any],
    cases: list[BenchmarkCase],
    threshold: float = 0.15,
    margin: float = 0.05,
) -> dict[str, float | int]:
    """Retrieval metrics for one retriever over one split.

    `threshold`/`margin` are parameters, not constants, because the
    defaults are calibrated to TF-IDF's score scale. Cosine similarities
    from a sentence-embedding model live in a different, much narrower
    range, so applying TF-IDF's margin to them makes the embedding and
    hybrid retrievers abstain on most queries -- comparing them under
    one fixed rule measures the rule, not the retrievers.
    """
    top1 = top3 = reciprocal = 0.0
    committed = wrong_reuse = abstained = 0

    for case, ranked in zip(cases, rankings, strict=True):
        ids = [c.skill.skill_id for c in ranked]

        # Same abstention rule the governed pipeline applies, so the
        # comparison reflects how each retriever would actually behave.
        if should_abstain(ranked, [], threshold=threshold, margin=margin):
            abstained += 1
            continue

        committed += 1
        expected = case.expected_skill
        if ids and ids[0] == expected:
            top1 += 1
        else:
            wrong_reuse += 1
        if expected in ids[:3]:
            top3 += 1
        if expected in ids:
            reciprocal += 1 / (ids.index(expected) + 1)

    n = len(cases)
    return {
        "n": n,
        "top1": top1 / n if n else 0.0,
        "top3": top3 / n if n else 0.0,
        "mrr": reciprocal / n if n else 0.0,
        "coverage": committed / n if n else 0.0,
        "abstention_rate": abstained / n if n else 0.0,
        "selective_accuracy": top1 / committed if committed else 0.0,
        "false_reuse_risk": wrong_reuse / committed if committed else 0.0,
    }


def _build_retrievers() -> dict[str, Any]:
    retrievers: dict[str, Any] = {"tfidf": TfidfRetriever(CATALOG)}
    try:
        from erp_agent_os.embeddings import EmbeddingRetriever

        embedder = EmbeddingRetriever(CATALOG)
        retrievers["embeddings"] = embedder
        retrievers["hybrid"] = HybridRetriever(CATALOG, embedder, HybridWeights())
    except Exception as exc:  # noqa: BLE001 - optional heavy dependency
        print(f"embeddings unavailable ({type(exc).__name__}: {exc})")
        print(
            "reporting TF-IDF only; install sentence-transformers for the full §22 set"
        )
    return retrievers


_THRESHOLD_GRID = (0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30)
_MARGIN_GRID = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10)


def _tune_abstention(
    rankings: list[Any], cases: list[BenchmarkCase]
) -> tuple[float, float, float]:
    """Pick (threshold, margin) per retriever on DEVELOPMENT only.

    CLAUDE.md §22: "Los pesos se ajustarán solamente con los conjuntos de
    desarrollo y validación". Tuning here is what makes the three-way
    comparison fair -- without it the embedding retrievers are judged
    under a rule calibrated for a different score scale.

    Objective is Top-1 over the whole split (not selective accuracy),
    because a retriever can trivially maximise selective accuracy by
    abstaining on everything hard. Ties break toward the more
    conservative (higher) threshold.
    """
    best = (0.0, 0.0, -1.0)
    for threshold in _THRESHOLD_GRID:
        for margin in _MARGIN_GRID:
            score = float(_evaluate(rankings, cases, threshold, margin)["top1"])
            if score > best[2] or (score == best[2] and threshold > best[0]):
                best = (threshold, margin, score)
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test",
        action="store_true",
        help=(
            "also evaluate on FINAL_TEST. Use ONLY to report an already-"
            "chosen configuration; selecting a retriever by its test score "
            "is tuning on test and invalidates the confirmatory result."
        ),
    )
    args = parser.parse_args()

    cases = generate_cases()
    splits = {
        "development": [c for c in cases if c.split is DatasetSplit.DEVELOPMENT],
        "validation": [c for c in cases if c.split is DatasetSplit.VALIDATION],
    }
    if args.test:
        splits["final_test"] = [c for c in cases if c.split is DatasetSplit.FINAL_TEST]

    retrievers = _build_retrievers()
    report: dict[str, Any] = {
        "tuning_discipline": (
            "CLAUDE.md §22: weights are tuned on development and validation "
            "only. FINAL_TEST is reported only for an already-chosen "
            "configuration (§19 freeze); selecting by test score would be "
            "tuning on test."
        ),
        "included_test_split": args.test,
        "results": {},
    }

    # Rank every split once per retriever; the threshold sweep reuses
    # these rankings instead of re-embedding each query 42 times.
    rankings = {
        name: {
            split_name: _rank_all(retriever, split_cases)
            for split_name, split_cases in splits.items()
        }
        for name, retriever in retrievers.items()
    }

    # Calibrate each retriever's abstention rule on DEVELOPMENT only,
    # then apply the frozen choice to every split.
    tuned = {
        name: _tune_abstention(rankings[name]["development"], splits["development"])
        for name in retrievers
    }
    report["tuned_abstention"] = {
        name: {"threshold": t, "margin": m, "development_top1": s}
        for name, (t, m, s) in tuned.items()
    }

    for split_name, split_cases in splits.items():
        report["results"][split_name] = {
            name: _evaluate(
                rankings[name][split_name],
                split_cases,
                tuned[name][0],
                tuned[name][1],
            )
            for name in retrievers
        }

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== abstención calibrada en DEVELOPMENT (§22) ===")
    for name, (t, m, s) in tuned.items():
        print(f"  {name:12} threshold={t:.3f} margin={m:.3f} (dev top1={s:.3f})")

    for split_name, per_retriever in report["results"].items():
        n = per_retriever[next(iter(per_retriever))]["n"]
        print(f"\n=== {split_name} ({n} casos) ===")
        print(
            f"{'retriever':12} {'top1':>7} {'top3':>7} {'mrr':>7} "
            f"{'cover':>7} {'selacc':>7} {'falsereuse':>11}"
        )
        for name, m in per_retriever.items():
            print(
                f"{name:12} {m['top1']:7.3f} {m['top3']:7.3f} {m['mrr']:7.3f} "
                f"{m['coverage']:7.3f} {m['selective_accuracy']:7.3f} "
                f"{m['false_reuse_risk']:11.3f}"
            )
    print(f"\nwritten to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
