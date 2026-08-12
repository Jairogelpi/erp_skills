"""Evaluate the fixed catalog-aware exploratory threat suite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from erp_agent_os.adversarial import RecordedThreatCase, evaluate_suite
from erp_agent_os.evidence import EvidenceRegistry

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CASES = ROOT / "data" / "catalog_aware_stress_cases.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_aware_stress_results.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        if args.output.resolve() != DEFAULT_OUTPUT.resolve():
            raise ValueError("reportable stress output must use the registered path")
        EvidenceRegistry.load(ROOT / "data" / "evidence_registry.json").status_for(
            "data/catalog_aware_stress_results.json"
        )
        raw = json.loads(args.cases.read_text(encoding="utf-8"))
        cases = TypeAdapter(list[RecordedThreatCase]).validate_python(raw)
        report = evaluate_suite(cases)
        args.output.write_text(
            report.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(
            f"CATALOG-AWARE STRESS HARNESS INVALID: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 2
    print(
        f"exploratory cases={report.n}, passed={report.passed}, "
        f"findings={report.findings}, unsupported={report.unsupported_policy}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
