"""Emit a blank second-annotator review sheet (roadmap P3.4).

Writes data/annotation_review_sheet.csv with one row per sampled case and
an empty `annotator2_decision` column for a human to fill in. Once
completed, compute agreement with:

    uv run python scripts/compute_agreement.py

This script deliberately cannot produce the second annotator's labels.
"""

import csv
from pathlib import Path

from erp_agent_os.agreement import stratified_review_sample
from erp_agent_os.bench_generator import generate_cases

OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "annotation_review_sheet.csv"
)

VALID_DECISIONS = "ALLOW | SIMULATE | REQUIRE_APPROVAL | DENY | CLARIFY | ABSTAIN"


def main() -> None:
    sample = stratified_review_sample(generate_cases())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "request_id",
                "request_text",
                "canonical_intent",
                "risk_class",
                "labels",
                "annotator1_decision",
                "annotator2_decision",
                "notes",
            ]
        )
        for case in sample:
            writer.writerow(
                [
                    case.request_id,
                    case.request_text,
                    case.canonical_intent,
                    case.risk_class.value,
                    "|".join(sorted(label.value for label in case.labels)),
                    case.expected_decision.value,
                    "",  # human fills this in; valid values below
                    "",
                ]
            )

    print(f"wrote {len(sample)} cases to {OUTPUT_PATH}")
    print(f"fill `annotator2_decision` with one of: {VALID_DECISIONS}")
    print("then run: uv run python scripts/compute_agreement.py")


if __name__ == "__main__":
    main()
