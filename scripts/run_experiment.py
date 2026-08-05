"""Run the paired A/B/C experiment and produce the statistical report.

    uv run python scripts/run_experiment.py

Writes data/experiment_results.json. Every number in it comes from the
1.080 executions this script performs; nothing is asserted that was not
measured.
"""

import json
from collections import defaultdict
from pathlib import Path

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.dataset import DatasetSplit
from erp_agent_os.experiment import run_experiment
from erp_agent_os.llm_client import DeterministicStubClient
from erp_agent_os.metrics import (
    retrieval_metrics,
    security_metrics,
    stability,
    stsr_breakdown,
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


def main() -> None:
    cases = generate_cases()
    test_cases = [c for c in cases if c.split is DatasetSplit.FINAL_TEST]
    by_id = {c.request_id: c for c in cases}

    records, manifest = run_experiment(cases, DeterministicStubClient())

    # Paired vectors: same (request_id, repetition) order for all systems.
    keyed: dict[str, dict[tuple[str, int], bool]] = defaultdict(dict)
    per_system_records = defaultdict(list)
    for record in records:
        success = stsr_breakdown(by_id[record.request_id], record).success
        keyed[record.system][(record.request_id, record.repetition)] = success
        per_system_records[record.system].append(record)

    units = sorted(keyed["C"])
    vectors = {system: [keyed[system][u] for u in units] for system in ("A", "B", "C")}

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
            "n_cases": manifest.n_cases,
            "n_repetitions": manifest.n_repetitions,
            "seed": manifest.seed,
            "caveat": (
                "Selector held constant across A/B/C, so this isolates the "
                "ARCHITECTURAL contribution. It is NOT the CLAUDE.md section 19 "
                "confirmatory protocol, which requires a real LLM provider."
            ),
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
        "H5_retrieval": {
            s: {
                "n": m.n,
                "top1": m.top1,
                "top3": m.top3,
                "mrr": m.mrr,
                "coverage": m.coverage,
                "abstention_rate": m.abstention_rate,
                "selective_accuracy": m.selective_accuracy,
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
