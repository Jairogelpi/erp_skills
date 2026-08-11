"""Compute Cohen's kappa from a completed review sheet (roadmap P3.4).

Reads data/annotation_review_sheet.csv. Exits with a clear message (not a
fabricated number) if the second annotator's column is still empty.
"""

import csv
import sys
from pathlib import Path

from erp_agent_os.agreement import cohens_kappa

SHEET_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "annotation_review_sheet.csv"
)


def main() -> int:
    if not SHEET_PATH.exists():
        print(f"no review sheet at {SHEET_PATH}", file=sys.stderr)
        print("run: uv run python scripts/build_annotation_sample.py", file=sys.stderr)
        return 1

    with SHEET_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    completed = [r for r in rows if (r.get("annotator2_decision") or "").strip()]
    if not completed:
        print(
            f"review sheet has {len(rows)} rows but no second-annotator labels yet.",
            file=sys.stderr,
        )
        print(
            "Cohen's kappa cannot be computed until a human completes it. "
            "This step is pending, not skipped.",
            file=sys.stderr,
        )
        return 1

    if len(completed) < len(rows):
        print(
            f"warning: {len(completed)}/{len(rows)} rows completed; "
            "kappa below is over the completed subset only."
        )

    result = cohens_kappa(
        [r["annotator1_decision"].strip() for r in completed],
        [r["annotator2_decision"].strip() for r in completed],
    )

    print(f"n                  = {result.n}")
    print(f"observed agreement = {result.observed_agreement:.3f}")
    print(f"expected agreement = {result.expected_agreement:.3f}")
    print(f"Cohen's kappa      = {result.kappa:.3f} ({result.interpretation()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
