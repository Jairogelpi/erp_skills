"""Freeze manifest for the confirmatory protocol (CLAUDE.md §19, P9.1).

§19 requires the test split, annotations, the 12-skill catalog, prompts,
configuration and the analysis plan to be frozen before the final run,
and any later change to be labelled exploratory. A prose promise cannot
enforce that; this module hashes the artefacts so a drift is *detected*
rather than trusted.

`verify_freeze` compares the current state against a recorded manifest
and reports exactly which component moved.

Schema 1.1 adds the two components §19 names that schema 1.0 left out:
the **prompts** and the **provider configuration** (model, temperature,
retry budget, timeout, token cap). Those were the difference between "we
promise A/B/C shared a configuration" and being able to detect that they
did not. The dataset, catalog and seed hashes are computed exactly as in
1.0 and are unchanged by the addition, so results published against the
1.0 manifest remain comparable — verified by re-freezing and diffing
those three fields.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from dataclasses import fields as dataclass_fields
from pathlib import Path
from typing import Any

from erp_agent_os.bench_generator import SEED, generate_cases
from erp_agent_os.catalog import CATALOG
from erp_agent_os.dataset import DatasetSplit
from erp_agent_os.llm_client import (
    EXTRACTION_SYSTEM_PROMPT,
    SELECTION_SYSTEM_PROMPT,
    build_extraction_prompt,
)

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
    # Schema 1.1. Default None so a 1.0 manifest still loads: verify then
    # reports the component as un-frozen rather than crashing, which is
    # the honest state -- an old manifest genuinely did not freeze these.
    prompt_hash: str | None = None
    provider_config_hash: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def _prompt_payload() -> str:
    """Every prompt string a real run sends, including the user template.

    The template is rendered with placeholders rather than hashed as
    source: an edit to the f-string that changes what the model actually
    receives must move the hash, and reading the function's source would
    also move it for a comment change that does not.
    """
    return "\n".join(
        (
            f"selection_system|{SELECTION_SYSTEM_PROMPT}",
            f"extraction_system|{EXTRACTION_SYSTEM_PROMPT}",
            "extraction_user|"
            + build_extraction_prompt("<QUERY>", ["<FIELD_A>", "<FIELD_B>"]),
        )
    )


def _provider_payload() -> str:
    """Default generation config of every real client, hashed together.

    Imported here rather than at module scope so `verify_freeze` does not
    drag three provider SDKs into every import of this module.
    """
    from erp_agent_os.gemini_client import GeminiConfig
    from erp_agent_os.groq_client import GroqConfig
    from erp_agent_os.openrouter_client import OpenRouterConfig

    lines = []
    for name, config in (
        ("gemini", GeminiConfig()),
        ("groq", GroqConfig()),
        ("openrouter", OpenRouterConfig()),
    ):
        settings = ";".join(
            f"{f.name}={getattr(config, f.name)}"
            for f in sorted(dataclass_fields(config), key=lambda f: f.name)
        )
        lines.append(f"{name}|{settings}")
    return "\n".join(lines)


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
        schema_version="1.1",
        seed=SEED,
        test_split_hash=_sha256(case_payload(test_cases)),
        full_dataset_hash=_sha256(case_payload(cases)),
        catalog_hash=_sha256(catalog_payload),
        n_test_cases=len(test_cases),
        n_total_cases=len(cases),
        prompt_hash=_sha256(_prompt_payload()),
        provider_config_hash=_sha256(_provider_payload()),
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

    drift = []
    for name in (
        "seed",
        "test_split_hash",
        "full_dataset_hash",
        "catalog_hash",
        "n_test_cases",
        "n_total_cases",
        "prompt_hash",
        "provider_config_hash",
    ):
        recorded_value = getattr(recorded, name)
        if recorded_value is None:
            # Schema 1.0 manifest: the component was never frozen. Say so
            # rather than passing silently, which would let a prompt or a
            # model change ride along unnoticed under an old manifest.
            drift.append(f"{name} (not frozen by schema {recorded.schema_version})")
        elif recorded_value != getattr(current, name):
            drift.append(name)
    return drift
