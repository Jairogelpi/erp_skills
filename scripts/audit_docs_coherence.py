"""Contrast published documentation with result data and evidence boundaries."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Sequence

from erp_agent_os.evidence import (
    EvidenceRegistry,
    audit_reporting_documents,
    reporting_document_paths,
)

ROOT = Path(__file__).resolve().parent.parent

OBSOLETAS = {
    "0,558": "STSR de C en la ejecucion 3 (superada por 0,633)",
    "+0,075": "C-B no significativo de la ejecucion 3 (superado por +0,150)",
    "0,212": "p de la ejecucion 3",
    "trece defectos": "son quince",
    "catorce defectos": "son quince",
    "384 tests": "recuento historico de tests",
    "274 passed": "recuento historico de tests",
    "298 passed": "recuento historico de tests",
    "305 passed": "recuento historico de tests",
    "342 passed": "recuento historico de tests",
    "386 passed": "recuento historico de tests",
    "391 passed": "recuento historico de tests",
    "cuatro corridas": "son cinco",
    "las tres ejecuciones": "son cinco",
}

CONTEXTO_OK = (
    "superad",
    "ejecución 3",
    "ejecucion 3",
    "anterior",
    "previa",
    "histórica",
    "historica",
    "quedan superados",
    "bitácora",
    "bitacora",
    "explorator",
)


def load(name: str, *, root: Path = ROOT) -> object:
    return json.loads((root / "data" / name).read_text(encoding="utf-8"))


def find_obsolete_claims(documents: Sequence[Path]) -> tuple[str, ...]:
    findings: list[str] = []
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for needle, reason in OBSOLETAS.items():
            for match in re.finditer(re.escape(needle), text):
                start = max(0, match.start() - 260)
                context = text[start : match.end() + 160].lower()
                if any(marker.lower() in context for marker in CONTEXTO_OK):
                    continue
                line = text[: match.start()].count("\n") + 1
                findings.append(f"{document}:{line}: '{needle}' -> {reason}")
    return tuple(sorted(set(findings)))


def find_claim_violations(
    registry: EvidenceRegistry,
    documents: Sequence[Path],
    *,
    annotation_sheet: Path,
) -> tuple[str, ...]:
    """Return evidence-boundary violations in a stable printable form."""

    violations = audit_reporting_documents(
        registry,
        tuple(documents),
        annotation_sheet=annotation_sheet,
    )
    return tuple(str(violation) for violation in violations)


def _print_result_summary(root: Path) -> None:
    vigente = load("experiment_results_real_parser.json", root=root)
    openrouter = load("experiment_results.json", root=root)
    groq_dados = load("experiment_results_groq_given_args.json", root=root)
    inject = load("injection_resistance_results.json", root=root)
    assert isinstance(vigente, dict)
    assert isinstance(openrouter, dict)
    assert isinstance(groq_dados, dict)
    assert isinstance(inject, dict)

    print("=" * 70)
    print("VERDAD (data/*.json; el registro gobierna su estatus protocolario)")
    print("=" * 70)
    print("REFERENCIA EXPLORATORIA V1 (Groq, parseo real + normalizacion):")
    print(
        "  STSR         :",
        {key: round(value, 3) for key, value in vigente["H1_stsr"]["stsr"].items()},
    )
    cb = vigente["H1_stsr"]["C_minus_B"]
    interval = [round(value, 3) for value in cb["ci95"]]
    print(f"  C-B          : {cb['point']:.3f} IC{interval} p={cb['holm_p']:.4f}")
    print(
        "  false allow  :",
        {
            key: round(value["false_allow_rate"], 3)
            for key, value in vigente["H4_security"].items()
        },
    )
    print(
        "  tokens/ejec  :",
        {
            key: round(value["mean_tokens_per_execution"], 1)
            for key, value in vigente["H2_tokens"]["totals"].items()
        },
    )
    print(
        "  trazabilidad :",
        {
            key: round(value, 3)
            for key, value in vigente["H7_traceability"]["mean_score"].items()
        },
    )
    print(
        "  H5 C top1    :",
        round(vigente["H5_retrieval"]["C"]["top1"], 3),
        "| abstencion:",
        round(vigente["H5_retrieval"]["C"]["abstention_rate"], 3),
    )
    print()
    print(
        "OpenRouter (parseo regalado):",
        {key: round(value, 3) for key, value in openrouter["H1_stsr"]["stsr"].items()},
        "| false allow A:",
        round(openrouter["H4_security"]["A"]["false_allow_rate"], 3),
    )
    print(
        "Groq argumentos dados      :",
        {key: round(value, 3) for key, value in groq_dados["H1_stsr"]["stsr"].items()},
        "| false allow A:",
        round(groq_dados["H4_security"]["A"]["false_allow_rate"], 3),
    )
    print(
        "Confinamiento exploratorio (3 canales):",
        inject["total_unauthorized_mutations"],
        "/ 1530",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    registry_path = args.registry or root / "data" / "evidence_registry.json"
    registry = EvidenceRegistry.load(registry_path)

    _print_result_summary(root)
    print()
    print("=" * 70)
    print("AFIRMACIONES SOSPECHOSAS EN LA DOCUMENTACION")
    print("=" * 70)

    reporting_docs = reporting_document_paths(root)
    active_docs = tuple(
        path for path in reporting_docs if path.name not in {"audit.md"}
    )
    obsolete = find_obsolete_claims(
        tuple(path for path in active_docs if path.is_file())
    )
    historical_obsolete = find_obsolete_claims(
        tuple(
            path
            for path in (root / "CLAUDE.md", root / "docs" / "audit.md")
            if path.is_file()
        )
    )
    claim_violations = find_claim_violations(
        registry,
        reporting_docs,
        annotation_sheet=root / "data" / "annotation_review_sheet.csv",
    )
    for finding in (*obsolete, *claim_violations):
        print(finding)

    if historical_obsolete:
        print()
        print("REFERENCIAS HISTÓRICAS (informativas; no bloquean la auditoría)")
        for finding in historical_obsolete:
            print(finding)

    print()
    print(
        "(CLAUDE.md es bitacora append-only; sus entradas antiguas se revisan aparte.)"
    )
    return 1 if obsolete or claim_violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
