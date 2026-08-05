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
            "ADVERSARIAL match rate is low by design of this discovery run: "
            "policy.py/runtime.py implement deny-by-default on role/state/"
            "risk only. Prompt-injection, argument-range, disguised-bulk-"
            "scope, irreversible-operation-framing, and permission-text "
            "detection are not yet implemented, so those adversarial "
            "categories legitimately execute as ALLOW/REQUIRE_APPROVAL "
            "instead of the dataset's ideally-correct DENY. This is a "
            "known gap for H4, not a bug in the wiring itself."
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
