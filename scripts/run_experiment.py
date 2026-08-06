"""Run the paired A/B/C experiment and produce the statistical report.

    uv run python scripts/run_experiment.py              # architecture-only, stub
    uv run python scripts/run_experiment.py --real-llm   # confirmatory, real Groq calls

Writes data/experiment_results.json. Every number in it comes from the
1.080 executions this script performs; nothing is asserted that was not
measured.

--real-llm requires GROQ_API_KEY (see .env.example) and makes real network
calls billed against your free-tier quota (System A and B each call the
LLM once per case per repetition; System C's retrieval is TF-IDF, not
LLM-based, so it makes none). Not used by default or in CI.
"""

import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.dataset import DatasetSplit
from erp_agent_os.experiment import run_experiment
from erp_agent_os.llm_client import DeterministicStubClient
from erp_agent_os.metrics import (
    collapse_repetitions,
    retrieval_metrics,
    security_metrics,
    segment_success,
    stability,
)
from erp_agent_os.statistics import (
    cochran_q,
    holm_correction,
    mcnemar,
    odds_ratio,
    paired_proportion_difference,
)

OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "experiment_results.json"
)


def _select_llm(real_llm: bool):
    if not real_llm:
        return DeterministicStubClient()
    from erp_agent_os.groq_client import GroqClient  # local import: optional dep path

    print(
        "Real-LLM confirmatory run: this makes network calls against your "
        "Groq free-tier quota. System A and B each call the model once per "
        "case per repetition (up to 120 * 2 * 3 = 720 calls); System C's "
        "retrieval does not call the LLM.",
        file=sys.stderr,
    )
    return GroqClient()


def _manifest_caveat(is_confirmatory: bool) -> str:
    """The manifest's caveat text must match `is_confirmatory_run`.

    A prior version hardcoded the non-confirmatory text unconditionally,
    so a real-LLM run would publish "is_confirmatory_run: true" next to a
    caveat claiming it was NOT the confirmatory protocol -- a factual
    contradiction discovered by reading the output of the first real run.
    """
    if not is_confirmatory:
        return (
            "Selector held constant across A/B/C, so this isolates the "
            "ARCHITECTURAL contribution. It is NOT the CLAUDE.md section 19 "
            "confirmatory protocol, which requires a real LLM provider."
        )
    return (
        "Real LLM selector (Groq free tier) shared identically across "
        "A/B/C, per CLAUDE.md D-03. This IS the section 19 confirmatory "
        "protocol. Declared limitation: a free-tier model, not a "
        "frontier/production model -- see the memoria for the disclosure "
        "this requires."
    )


def _configure_logging(real_llm: bool) -> None:
    """Real-call visibility: one line per observation, per attempt, per
    retry, flushed immediately -- so `tail -f` on the log shows live
    progress instead of nothing until the final JSON dump."""
    if not real_llm:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )


def main() -> None:
    real_llm = "--real-llm" in sys.argv
    _configure_logging(real_llm)
    cases = generate_cases()
    test_cases = [c for c in cases if c.split is DatasetSplit.FINAL_TEST]

    records, manifest = run_experiment(cases, _select_llm(real_llm))

    per_system_records = defaultdict(list)
    for record in records:
        per_system_records[record.system].append(record)

    # Inference unit is the CASE, not (case, repetition): repetitions of
    # the same case are not independent, and treating them as such is
    # pseudo-replication that would narrow every CI by ~sqrt(3) and shrink
    # p-values by orders of magnitude. Repetitions feed H3 (stability).
    collapsed = collapse_repetitions(test_cases, records)
    units = sorted(collapsed["C"])
    vectors = {
        system: [collapsed[system][u] for u in units] for system in ("A", "B", "C")
    }

    stsr = {s: sum(v) / len(v) for s, v in vectors.items()}

    # H1: C non-inferior to A, margin -5 pp.
    h1_diff = paired_proportion_difference(vectors["C"], vectors["A"])
    h1_test = mcnemar(vectors["C"], vectors["A"])
    h1_non_inferior = h1_diff.low > -0.05

    cb_diff = paired_proportion_difference(vectors["C"], vectors["B"])
    cb_test = mcnemar(vectors["C"], vectors["B"])

    q_statistic, q_df = cochran_q(vectors["A"], vectors["B"], vectors["C"])
    adjusted = holm_correction([h1_test.p_value, cb_test.p_value])

    security = {
        s: security_metrics(test_cases, per_system_records[s]) for s in ("A", "B", "C")
    }
    retrieval = {
        s: retrieval_metrics(test_cases, per_system_records[s]) for s in ("A", "B", "C")
    }
    stab = {s: stability(per_system_records[s]) for s in ("A", "B", "C")}

    report = {
        "manifest": {
            "selector": manifest.selector,
            "is_confirmatory_run": manifest.is_confirmatory,
            "n_observations": len(records),
            "n_inference_units": len(units),
            "inference_note": (
                "Repetitions are collapsed per case before any paired test. "
                "Using all 1.080 executions as independent observations "
                "would be pseudo-replication."
            ),
            "n_cases": manifest.n_cases,
            "n_repetitions": manifest.n_repetitions,
            "seed": manifest.seed,
            "caveat": _manifest_caveat(manifest.is_confirmatory),
        },
        "H1_stsr": {
            "stsr": stsr,
            "C_minus_A": {
                "point": h1_diff.point,
                "ci95": [h1_diff.low, h1_diff.high],
                "mcnemar_p": h1_test.p_value,
                "holm_p": adjusted[0],
                "discordant_C_wins": h1_test.discordant_b,
                "discordant_A_wins": h1_test.discordant_c,
                "odds_ratio": odds_ratio(vectors["C"], vectors["A"]),
            },
            "C_minus_B": {
                "point": cb_diff.point,
                "ci95": [cb_diff.low, cb_diff.high],
                "mcnemar_p": cb_test.p_value,
                "holm_p": adjusted[1],
                "odds_ratio": odds_ratio(vectors["C"], vectors["B"]),
            },
            "cochran_q": {"statistic": q_statistic, "df": q_df},
            "non_inferiority_margin": -0.05,
            "H1_supported": h1_non_inferior,
        },
        "H3_stability": stab,
        "H4_security": {
            s: {
                "dangerous_total": m.dangerous_total,
                "false_allow": m.false_allow,
                "false_allow_rate": m.false_allow_rate,
                "false_block_rate": m.false_block_rate,
                "detection_recall": m.detection_recall,
                "detection_precision": m.detection_precision,
            }
            for s, m in security.items()
        },
        "segmentation": {
            dimension: {
                system: segment_success(
                    test_cases, per_system_records[system], dimension
                )
                for system in ("A", "B", "C")
            }
            for dimension in ("module", "risk_class", "label")
        },
        "H5_retrieval": {
            s: {
                "n": m.n,
                "top1": m.top1,
                "top3": m.top3,
                "mrr": m.mrr,
                "coverage": m.coverage,
                "abstention_rate": m.abstention_rate,
                "selective_accuracy": m.selective_accuracy,
                "false_reuse_risk": m.false_reuse_risk,
            }
            for s, m in retrieval.items()
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
