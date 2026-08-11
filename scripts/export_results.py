"""Export experiment results to CSV/Parquet (RF-18).

RF-18 requires exporting results to CSV or Parquet. The experiment
writes JSON, which is right for a nested report but wrong for the
things RF-18 exists to enable: loading into pandas, into a notebook, or
into the §31 dashboard.

Two tables, because they answer different questions:

- **metrics**: one row per (run, system) with the headline numbers --
  STSR, false allow, tokens, traceability. This is the table a
  dashboard or a results chapter reads.
- **segments**: one row per (run, system, dimension, stratum) with the
  §21 segmented STSR, so per-module / per-risk / per-label breakdowns
  can be charted without re-deriving them.

Parquet is written too when `pandas`+`pyarrow` are importable; CSV is
always written, so the deliverable never depends on an optional
dependency.
"""

import csv
import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# (label, path) -- every experiment result file we know how to flatten.
_RUNS = (
    ("confirmatory", DATA_DIR / "experiment_results.json"),
    ("real_parser", DATA_DIR / "experiment_results_real_parser.json"),
)

_METRIC_COLUMNS = [
    "run",
    "selector",
    "real_parser",
    "system",
    "stsr",
    "false_allow_rate",
    "false_block_rate",
    "detection_recall",
    "mean_tokens_per_execution",
    "total_tokens",
    "traceability",
    "stability",
    "top1",
    "top3",
    "mrr",
    "coverage",
    "abstention_rate",
    "selective_accuracy",
    "false_reuse_risk",
]
_SEGMENT_COLUMNS = ["run", "system", "dimension", "stratum", "n", "successes", "stsr"]


def _metric_rows(run: str, report: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = report["manifest"]
    rows = []
    for system in ("A", "B", "C"):
        tokens = report.get("H2_tokens", {}).get("totals", {}).get(system, {})
        security = report["H4_security"][system]
        retrieval = report["H5_retrieval"][system]
        rows.append(
            {
                "run": run,
                "selector": manifest["selector"],
                "real_parser": manifest.get("real_parser", False),
                "system": system,
                "stsr": report["H1_stsr"]["stsr"][system],
                "false_allow_rate": security["false_allow_rate"],
                "false_block_rate": security["false_block_rate"],
                "detection_recall": security["detection_recall"],
                "mean_tokens_per_execution": tokens.get("mean_tokens_per_execution"),
                "total_tokens": tokens.get("total_tokens"),
                "traceability": report.get("H7_traceability", {})
                .get("mean_score", {})
                .get(system),
                "stability": report["H3_stability"][system],
                "top1": retrieval["top1"],
                "top3": retrieval["top3"],
                "mrr": retrieval["mrr"],
                "coverage": retrieval["coverage"],
                "abstention_rate": retrieval["abstention_rate"],
                "selective_accuracy": retrieval["selective_accuracy"],
                "false_reuse_risk": retrieval["false_reuse_risk"],
            }
        )
    return rows


def _segment_rows(run: str, report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for dimension, per_system in report.get("segmentation", {}).items():
        for system, strata in per_system.items():
            for stratum, values in strata.items():
                rows.append(
                    {
                        "run": run,
                        "system": system,
                        "dimension": dimension,
                        "stratum": stratum,
                        "n": values["n"],
                        "successes": values["successes"],
                        "stsr": values["stsr"],
                    }
                )
    return rows


def _write(name: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
    csv_path = DATA_DIR / f"{name}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {csv_path}")

    try:
        import pandas as pd
    except ImportError:
        print(f"  (pandas unavailable: skipped {name}.parquet, CSV is the deliverable)")
        return
    parquet_path = DATA_DIR / f"{name}.parquet"
    try:
        pd.DataFrame(rows, columns=columns).to_parquet(parquet_path, index=False)
    except Exception as exc:  # noqa: BLE001 - pyarrow/fastparquet may be absent
        print(f"  (parquet engine unavailable: {type(exc).__name__}; CSV written)")
        return
    print(f"wrote {len(rows)} rows to {parquet_path}")


def main() -> None:
    metric_rows: list[dict[str, Any]] = []
    segment_rows: list[dict[str, Any]] = []

    for run, path in _RUNS:
        if not path.exists():
            print(f"skipping {run}: {path.name} not present")
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        metric_rows += _metric_rows(run, report)
        segment_rows += _segment_rows(run, report)

    if not metric_rows:
        raise SystemExit("no experiment result files found; run the experiment first")

    _write("experiment_metrics", _METRIC_COLUMNS, metric_rows)
    _write("experiment_segments", _SEGMENT_COLUMNS, segment_rows)


if __name__ == "__main__":
    main()
