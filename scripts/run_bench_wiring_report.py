"""Run all 480 ERP-Skills-Bench v1 cases through real System C execution
and write a match-rate report to data/bench_v1_wiring_report.json.

Reports, does not hide, the gap between the dataset's ideally-correct
`expected_decision` and what the current policy/runtime actually produces
for several ADVERSARIAL categories (no prompt-injection/range/bulk-scope/
permission-text detection exists yet — see docs/dataset-card.md).
"""

import json
from collections import Counter
from pathlib import Path

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.bench_runner import run_all, summarize
from erp_agent_os.dataset import CaseLabel

OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "bench_v1_wiring_report.json"
)


def main() -> None:
    cases = generate_cases()
    outcomes = run_all(cases)
    summary = summarize(cases, outcomes)

    mismatch_by_error_type: Counter[str] = Counter()
    handler_errors = 0
    for case, outcome in zip(cases, outcomes, strict=True):
        if not outcome.matched:
            mismatch_by_error_type[case.error_type] += 1
        if outcome.handler_error is not None:
            handler_errors += 1

    report = {
        "total_cases": len(cases),
        "summary_by_label": summary,
        "mismatch_by_error_type": dict(mismatch_by_error_type),
        "handler_errors_count": handler_errors,
        "notes": (
            "validation.py adds lexical adversarial detection (prompt "
            "injection, bulk scope, irreversible framing, permission "
            "claims) and numeric range/type checks, and SystemC now "
            "distinguishes CLARIFY (missing required data) from ABSTAIN "
            "(no trustworthy candidate). Remaining mismatches are known "
            "and unfixed, not hidden: unknown_record_id needs a "
            "pre-execution existence check; conflicting_fields and some "
            "near_miss cases need semantic (not lexical) analysis; the "
            "residual 'none' mismatches are TF-IDF misrouting short "
            "queries. Detectors are lexical and tuned to this frozen "
            "benchmark's templated adversarial text -- they are NOT a "
            "general prompt-injection defence and must be reported with "
            "that ceiling stated (CLAUDE.md section 36)."
        ),
    }

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))

    normal_only = sum(1 for c in cases if c.labels == {CaseLabel.NORMAL})
    print(f"\n({normal_only} NORMAL-only-labeled cases in this run)")


if __name__ == "__main__":
    main()
