"""Freeze manifest for the confirmatory protocol (CLAUDE.md §19, P9.1).

§19 requires the test split, annotations, the 12-skill catalog, prompts,
configuration and the analysis plan to be frozen before the final run,
and any later change to be labelled exploratory. A prose promise cannot
enforce that; this module hashes the artefacts so a drift is *detected*
rather than trusted.

`verify_freeze` compares the current state against a recorded manifest
and reports exactly which component moved.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from erp_agent_os.bench_generator import SEED, generate_cases
from erp_agent_os.catalog import CATALOG
from erp_agent_os.dataset import DatasetSplit

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "freeze_manifest.json"


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FreezeManifest:
    schema_version: str
    seed: int
    test_split_hash: str
    full_dataset_hash: str
    catalog_hash: str
    n_test_cases: int
    n_total_cases: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def compute_manifest() -> FreezeManifest:
    cases = generate_cases()
    test_cases = [c for c in cases if c.split is DatasetSplit.FINAL_TEST]

    def case_payload(items: list[Any]) -> str:
        return "\n".join(
            f"{c.request_id}|{c.request_text}|{c.canonical_intent}|"
            f"{c.expected_skill}|{c.expected_decision.value}|{c.split.value}"
            for c in sorted(items, key=lambda c: c.request_id)
        )

    catalog_payload = "\n".join(
        f"{s.skill_id}|{s.version}|{s.risk_class.value}|"
        f"{','.join(s.postconditions)}|{','.join(s.permissions.allowed_roles)}"
        for s in sorted(CATALOG, key=lambda s: s.skill_id)
    )

    return FreezeManifest(
        schema_version="1.0",
        seed=SEED,
        test_split_hash=_sha256(case_payload(test_cases)),
        full_dataset_hash=_sha256(case_payload(cases)),
        catalog_hash=_sha256(catalog_payload),
        n_test_cases=len(test_cases),
        n_total_cases=len(cases),
    )


def write_manifest(path: Path = MANIFEST_PATH) -> FreezeManifest:
    manifest = compute_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.to_json(), encoding="utf-8")
    return manifest


def load_manifest(path: Path = MANIFEST_PATH) -> FreezeManifest:
    return FreezeManifest(**json.loads(path.read_text(encoding="utf-8")))


def verify_freeze(path: Path = MANIFEST_PATH) -> list[str]:
    """Return the names of components that drifted since the freeze.

    Empty list means the frozen artefacts are intact. Any non-empty result
    means results computed now are NOT comparable to the frozen protocol
    and must be labelled exploratory (§19).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"no freeze manifest at {path}; run scripts/freeze_protocol.py"
        )

    recorded = load_manifest(path)
    current = compute_manifest()

    drift = [
        name
        for name in (
            "seed",
            "test_split_hash",
            "full_dataset_hash",
            "catalog_hash",
            "n_test_cases",
            "n_total_cases",
        )
        if getattr(recorded, name) != getattr(current, name)
    ]
    return drift
