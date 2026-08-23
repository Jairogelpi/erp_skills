"""Machine-checkable contract between evidence artifacts and public claims."""

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

EVIDENCE_MARKER = "EVIDENCE-STATUS: no-valid-confirmatory-conclusion"
REPORTING_DOCUMENTS = (
    "README.md",
    "docs/memoria.md",
    "docs/defensa.md",
    "docs/results.md",
    "docs/demo-explicada.md",
    "docs/product-viability.md",
    "docs/hypotheses-and-theses.md",
)
_DATA_REFERENCE = re.compile(r"data/[A-Za-z0-9_.-]+\.jsonl?")
_EXPECTED_HYPOTHESES = {f"H{index}" for index in range(1, 9)}


def validate_claim_contract(
    registry: Mapping[str, Any], documents: Mapping[str, str]
) -> list[str]:
    """Return all release-blocking inconsistencies without short-circuiting."""
    errors: list[str] = []
    if registry.get("global_status") != "no_valid_confirmatory_conclusion":
        errors.append("registry must declare no_valid_confirmatory_conclusion")

    hypotheses = registry.get("hypotheses", {})
    if set(hypotheses) != _EXPECTED_HYPOTHESES:
        errors.append("registry must contain exactly H1-H8")
    for hypothesis_id, entry in hypotheses.items():
        status = str(entry.get("status", "")).lower()
        if status in {"confirmed", "accepted", "supported_confirmatory"}:
            errors.append(f"{hypothesis_id} has forbidden confirmed status: {status}")

    artifacts = registry.get("artifacts", {})
    for hypothesis_id, entry in hypotheses.items():
        for artifact in entry.get("primary_artifacts", []):
            if artifact not in artifacts:
                errors.append(f"{hypothesis_id} cites unregistered artifact {artifact}")

    for name in REPORTING_DOCUMENTS:
        text = documents.get(name)
        if text is None:
            errors.append(f"missing reporting document {name}")
            continue
        if EVIDENCE_MARKER not in text:
            errors.append(f"{name} is missing {EVIDENCE_MARKER}")
        for reference in sorted(set(_DATA_REFERENCE.findall(text))):
            if reference == "data/evidence_registry.json":
                continue
            if reference not in artifacts:
                errors.append(f"{name} cites unregistered artifact {reference}")

    canonical = documents.get("docs/hypotheses-and-theses.md", "")
    for hypothesis_id in sorted(_EXPECTED_HYPOTHESES):
        if f"### {hypothesis_id} " not in canonical:
            errors.append(f"canonical hypothesis document is missing {hypothesis_id}")

    for artifact in (
        "data/experiment_results.json",
        "data/experiment_results_groq_given_args.json",
        "data/experiment_results_real_parser.json",
    ):
        metadata = artifacts.get(artifact, {})
        if metadata.get("legacy_confirmatory_label_invalidated") is not True:
            errors.append(
                f"legacy confirmatory label is not invalidated for {artifact}"
            )
        if metadata.get("raw_observations_available") is not False:
            errors.append(
                f"legacy raw-observation absence is not recorded for {artifact}"
            )
    return errors


def validate_claims(root: Path) -> list[str]:
    registry_path = root / "data" / "evidence_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    documents = {
        name: (root / name).read_text(encoding="utf-8")
        for name in REPORTING_DOCUMENTS
        if (root / name).exists()
    }
    errors = validate_claim_contract(registry, documents)
    for artifact in registry.get("artifacts", {}):
        if not (root / artifact).exists():
            errors.append(f"registered artifact does not exist: {artifact}")

    # Old summaries retain their original bytes for provenance, but a true
    # historic flag is allowed only when the registry explicitly invalidates it.
    for name, metadata in registry.get("artifacts", {}).items():
        if metadata.get("kind") != "legacy_aggregate_summary":
            continue
        payload = json.loads((root / name).read_text(encoding="utf-8"))
        historic_flag = payload.get("manifest", {}).get("is_confirmatory_run")
        if historic_flag is True and not metadata.get(
            "legacy_confirmatory_label_invalidated"
        ):
            errors.append(f"uninvalidated historic confirmatory flag in {name}")
    return errors
