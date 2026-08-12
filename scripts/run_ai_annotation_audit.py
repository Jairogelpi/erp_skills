"""Run the blinded annotation diagnostic from offline recorded responses."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from erp_agent_os.annotation_audit import (
    AnnotationAuditError,
    RecordedResponseReviewer,
    load_recorded_responses,
    load_review_rows,
    run_blinded_audit,
    write_report_atomic,
)
from erp_agent_os.evidence import EvidenceRegistry

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "annotation_review_sheet.csv"
DEFAULT_OUTPUT = ROOT / "data" / "annotation_ai_audit.json"
REGISTRY = ROOT / "data" / "evidence_registry.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        if output != DEFAULT_OUTPUT.resolve():
            raise AnnotationAuditError(
                "retained audit output must use the registered evidence path"
            )
        registry = EvidenceRegistry.load(REGISTRY)
        registry.status_for("data/annotation_ai_audit.json")
        before = args.input.read_bytes()
        items, canonical = load_review_rows(args.input)
        report = run_blinded_audit(
            items=items,
            canonical_labels=canonical,
            reviewer=RecordedResponseReviewer(load_recorded_responses(args.responses)),
            provider=args.provider,
            model=args.model,
            temperature=args.temperature,
        )
        if args.input.read_bytes() != before:
            raise AnnotationAuditError("canonical annotation input changed")
        write_report_atomic(report, output)
    except (AnnotationAuditError, OSError, ValueError) as exc:
        print(f"AI ANNOTATION AUDIT FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"AI consistency diagnostic written: {DEFAULT_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
