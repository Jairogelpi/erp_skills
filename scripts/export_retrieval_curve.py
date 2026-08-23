"""Export the fixed-grid H6 curve as explicitly post-freeze exploratory."""

import json
from dataclasses import asdict
from pathlib import Path

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.catalog import CATALOG
from erp_agent_os.dataset import DatasetSplit
from erp_agent_os.freeze import load_manifest
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.retrieval_analysis import (
    DEFAULT_MARGIN,
    THRESHOLD_GRID,
    curve_configuration_hash,
    precision_coverage_curve,
)


def main() -> None:
    cases = [case for case in generate_cases() if case.split is DatasetSplit.FINAL_TEST]
    points = precision_coverage_curve(
        cases,
        TfidfRetriever(CATALOG),
        thresholds=THRESHOLD_GRID,
        margin=DEFAULT_MARGIN,
    )
    payload = {
        "schema_version": "1.0",
        "epistemic_status": "post_freeze_exploratory",
        "confirmatory": False,
        "reason": (
            "The v1 test split had already been inspected before this curve "
            "was implemented. The grid is fixed and hashed, but the result is "
            "descriptive only."
        ),
        "freeze_hashes": asdict(load_manifest()),
        "thresholds": list(THRESHOLD_GRID),
        "margin": DEFAULT_MARGIN,
        "configuration_hash": curve_configuration_hash(),
        "points": [point.to_dict() for point in points],
    }
    destination = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "retrieval_precision_coverage_v1.json"
    )
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(destination)


if __name__ == "__main__":
    main()
