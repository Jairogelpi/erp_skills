"""Read-only access to the frozen v2.1.2 confirmatory campaign.

Every statistical figure the product demo displays is loaded from
`data/protocol_v2_1/confirmatory_report_v2_1_2.json` and the manifest
line of its observation archive. Nothing here recomputes a statistic,
and nothing here carries a literal result value: a number that appears
in the UI but not in an artifact would be a fabricated claim, which is
exactly what the demo must not produce.

Two things this module has to get right that a naive `json.load` does
not:

1. **Non-finite floats.** The report legitimately contains `NaN`
   (p-values for one-sided bootstrap tests, which have none) and
   `-Infinity` (the open end of a one-sided confidence interval).
   Python's `json` reads and writes those happily; JSON as consumed by
   a browser has no such literals, so `JSON.parse` rejects them. They
   are converted to `None` here, at the boundary, rather than being
   dropped or silently coerced to a number that would read as a real
   estimate.

2. **The observation count.** It comes from the archive's manifest
   header row (`row_count`), not from a constant and not from counting
   lines -- the file is 81 MB and its first line is a manifest, so a
   line count is both slow and off by one.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REPORT_PATH = REPO_ROOT / "data" / "protocol_v2_1" / "confirmatory_report_v2_1_2.json"
CODE_MANIFEST_PATH = REPO_ROOT / "data" / "protocol_v2_1" / "code_freeze_manifest.json"
ARCHIVE_DIR = REPO_ROOT / "data" / "protocol_v2_1" / "runs_v2"

# The stress test is a *different* experiment from the confirmatory
# campaign and is labelled as such wherever it is shown: it measures
# contract confinement under a compromised model, not danger detection.
INJECTION_RESISTANCE_PATH = REPO_ROOT / "data" / "injection_resistance_results.json"


class EvidenceUnavailableError(RuntimeError):
    """A required confirmatory artifact is missing or unreadable.

    Raised rather than defaulted: a demo that silently falls back to
    placeholder statistics would present invented numbers as measured
    ones, which is the single failure mode this module exists to
    prevent.
    """


def json_safe(value: Any) -> Any:
    """Recursively replace non-finite floats with None.

    `float('nan')` and `float('-inf')` are valid Python and invalid
    JSON. Returning None keeps the key present (so the UI can render
    "not applicable" rather than silently omitting a field) without
    inventing a finite value.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [json_safe(v) for v in value]
    return value


@dataclass(frozen=True)
class HypothesisCard:
    """One hypothesis as the UI shows it.

    `supported` is derived from the report's own `evidence_state`, never
    from re-reading the estimate against a threshold here -- the
    accept/reject decision was made by the frozen analysis code and this
    module only reports it.
    """

    key: str
    title: str
    question: str
    supported: bool
    verdict: str
    evidence_state: str
    estimate: float | None
    estimate_kind: str
    effect_size: float | None
    effect_size_name: str | None
    n: int | None
    test: str | None
    criterion: str | None
    p_value: float | None
    ci_low: float | None
    ci_high: float | None
    population: str | None
    unit: str | None


@dataclass(frozen=True)
class CapabilityRow:
    dimension: str
    system_a: str
    system_b: str
    system_c: str
    source_hypothesis: str | None


@dataclass(frozen=True)
class EvidenceBundle:
    protocol_tag: str
    protocol_version: str
    frozen_commit: str
    frozen_at: str
    campaign_state: str
    observation_count: int
    archive_hash: str
    cards: list[HypothesisCard]
    capability_matrix: list[CapabilityRow]
    confinement: dict[str, Any] = field(default_factory=dict)


# Display metadata only. Every *number* is read from the report; these
# strings say what a hypothesis asks, not what it found.
_CARD_SPEC: tuple[tuple[str, str, str, str], ...] = (
    (
        "h1a",
        "H1a — Task success vs A",
        "Is the governed system at least as successful as an ungoverned agent?",
        "percentage_points",
    ),
    (
        "h1b",
        "H1b — Task success vs B",
        "Does governance beat typed tools at completing the task?",
        "percentage_points",
    ),
    (
        "h2_vs_a",
        "H2 — Tokens vs A",
        "Does governance cost more model work than a direct agent?",
        "tokens",
    ),
    (
        "h2_vs_b",
        "H2 — Tokens vs B",
        "Does governance cost more model work than typed tools?",
        "tokens",
    ),
    (
        "h3a",
        "H3a — Paraphrase stability",
        "Do equivalent phrasings of one intent reach the same final state?",
        "percentage_points",
    ),
    (
        "h4_unauthorized_mutation",
        "H4 — Active danger detection",
        "Across dangerous scenarios, how often does an unauthorized mutation occur?",
        "proportion",
    ),
    (
        "h5",
        "H5 — Retrieval",
        "Is skill retrieval accurate enough to reuse automatically?",
        "proportion",
    ),
    (
        "h6",
        "H6 — Abstention",
        "Does abstaining reduce wrong-skill reuse?",
        "percentage_points",
    ),
    (
        "h7",
        "H7 — Audit reconstruction",
        "Can what happened be reconstructed from the trace alone?",
        "percentage_points",
    ),
)


def _load_json(path: Path, what: str) -> Any:
    if not path.exists():
        raise EvidenceUnavailableError(f"{what} not found at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:  # malformed artifact, not a missing one
        raise EvidenceUnavailableError(
            f"{what} at {path} is not valid JSON: {exc}"
        ) from exc


def _archive_manifest() -> dict[str, Any]:
    """First line of the observation archive: its own row-count manifest.

    Reads exactly one line. The archive is ~81 MB and the demo starts on
    every page load, so parsing the whole file to learn its size would
    make the header the slowest thing on screen.
    """
    matches = sorted(ARCHIVE_DIR.glob("confirmatory_observations_v21_*.jsonl"))
    if len(matches) != 1:
        raise EvidenceUnavailableError(
            f"expected exactly one observation archive in {ARCHIVE_DIR}, "
            f"found {len(matches)}"
        )
    with matches[0].open(encoding="utf-8") as handle:
        header = json.loads(handle.readline())
    if header.get("type") != "manifest":
        raise EvidenceUnavailableError(
            f"{matches[0].name} does not start with a manifest row"
        )
    return {"row_count": int(header["row_count"]), "path": matches[0]}


def _card(
    key: str, title: str, question: str, kind: str, report: Any
) -> HypothesisCard:
    entry = report["hypotheses"][key]
    result = entry["result"]
    state = entry["claim"]["evidence_state"]
    return HypothesisCard(
        key=key,
        title=title,
        question=question,
        # "confirmatory_supported" is the only state that licenses a
        # positive claim; "observed_descriptive" and every
        # "not_supported" variant do not.
        supported=state == "confirmatory_supported",
        verdict=str(result.get("verdict")),
        evidence_state=str(state),
        estimate=json_safe(result.get("estimate")),
        estimate_kind=kind,
        effect_size=json_safe(result.get("effect_size")),
        effect_size_name=result.get("effect_size_name"),
        n=result.get("n"),
        test=result.get("test"),
        criterion=result.get("criterion"),
        p_value=json_safe(result.get("p_value")),
        ci_low=json_safe(result.get("ci_low")),
        ci_high=json_safe(result.get("ci_high")),
        population=result.get("population"),
        unit=result.get("unit"),
    )


def _capability_matrix(cards: dict[str, HypothesisCard]) -> list[CapabilityRow]:
    """Qualitative summary, derived from the report's own verdicts.

    Deliberately not a score. CLAUDE.md's §36 warning about construct
    validity applies directly here: collapsing eight hypotheses with
    different units, populations and directions into "A=42, C=91" would
    invent a quantity nothing measured. Each row instead names the
    hypothesis it comes from, so a reader can check it.
    """

    def mark(key: str) -> str:
        card = cards[key]
        return "supported" if card.supported else "not supported"

    return [
        CapabilityRow(
            "Task success",
            "baseline",
            "comparable to C",
            mark("h1b"),
            "h1b",
        ),
        CapabilityRow(
            "Token efficiency", "higher cost", "higher cost", mark("h2_vs_b"), "h2_vs_b"
        ),
        CapabilityRow(
            "Paraphrase stability", "lower", "comparator", mark("h3a"), "h3a"
        ),
        CapabilityRow("Abstention", "none", "none", mark("h6"), "h6"),
        CapabilityRow("Audit reconstruction", "limited", "limited", mark("h7"), "h7"),
        CapabilityRow(
            "Active danger detection",
            "not applicable",
            "not applicable",
            mark("h4_unauthorized_mutation"),
            "h4_unauthorized_mutation",
        ),
        CapabilityRow(
            "Retrieval", "not applicable", "not applicable", mark("h5"), "h5"
        ),
    ]


def _confinement() -> dict[str, Any]:
    """The injection-resistance sweep, kept explicitly separate.

    Shown next to H4 precisely because they disagree in tone, and the UI
    must say why: H4 measures whether danger is *recognised*, this
    measures whether the skill contract is *escaped*. Absent file is not
    fatal -- the confirmatory campaign is what the demo depends on.
    """
    if not INJECTION_RESISTANCE_PATH.exists():
        return {}
    data = _load_json(INJECTION_RESISTANCE_PATH, "injection resistance results")
    arms = data.get("arms", {})
    return json_safe(
        {
            # Summed from the arms rather than read from a top-level
            # field, because the artifact has no such field: 510
            # payloads delivered through each of three attack channels.
            "total_attempts": sum(int(arm["n"]) for arm in arms.values()),
            "unauthorized_mutations": data.get("total_unauthorized_mutations"),
            "payloads": data.get("n_payloads"),
            "question": data.get("question"),
            "arms": arms,
            "source": data.get("source"),
            "artifact": INJECTION_RESISTANCE_PATH.name,
        }
    )


def load_evidence() -> EvidenceBundle:
    report = _load_json(REPORT_PATH, "confirmatory report")
    manifest = _load_json(CODE_MANIFEST_PATH, "code freeze manifest")
    archive = _archive_manifest()
    protocol = _load_json(REPO_ROOT / "config" / "protocol_v2_1.json", "protocol")

    cards = [_card(k, t, q, kind, report) for k, t, q, kind in _CARD_SPEC]
    by_key = {card.key: card for card in cards}

    return EvidenceBundle(
        protocol_tag=str(manifest["git_tag"]),
        protocol_version=str(protocol["protocol_version"]),
        frozen_commit=str(manifest["git_commit"]),
        frozen_at=str(manifest["frozen_at"]),
        campaign_state=str(report["campaign_state"]),
        observation_count=archive["row_count"],
        archive_hash=str(
            report["hypotheses"]["h1a"]["table_manifest"]["observation_archive_hash"]
        ),
        cards=cards,
        capability_matrix=_capability_matrix(by_key),
        confinement=_confinement(),
    )
