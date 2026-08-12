"""Validate the evidence registry, completeness, and linked reporting claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from erp_agent_os.evidence import (
    EvidenceRegistry,
    audit_reporting_documents,
    reporting_document_paths,
)

ROOT = Path(__file__).resolve().parent.parent


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    registry_path = args.registry or root / "data" / "evidence_registry.json"

    try:
        registry = EvidenceRegistry.load(registry_path)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"INVALID REGISTRY {registry_path}: {exc}")
        return 1

    failures: list[str] = []
    failures.extend(
        f"UNREGISTERED ARTIFACT {path}"
        for path in registry.unregistered_reportable_paths(root)
    )
    documents = (
        tuple(path.resolve() for path in args.documents)
        if args.documents
        else reporting_document_paths(root)
    )
    violations = audit_reporting_documents(
        registry,
        documents,
        annotation_sheet=root / "data" / "annotation_review_sheet.csv",
    )
    failures.extend(str(violation) for violation in violations)

    if failures:
        for failure in failures:
            print(failure)
        return 1
    print(f"Evidence registry valid: {len(registry.entries)} artefacts governed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
