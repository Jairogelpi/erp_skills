#!/usr/bin/env python
"""Generate the v2.1 confirmatory report from raw JSONL only (Task 11).

    uv run python scripts/analyze_confirmatory_v2_1.py \\
        --archive data/protocol_v2_1/runs/confirmatory_observations_<hash>.jsonl \\
        --code-manifest-path data/protocol_v2_1/code_freeze_manifest.json \\
        --receipt-log data/protocol_v2_1/runs/receipts.jsonl \\
        --output data/protocol_v2_1/confirmatory_report.json

**Reads raw JSONL only.** Every number in the report is derived from
`ObservationV21` rows loaded through `erp_agent_os.evidence_v2_1.
load_observations_v21_jsonl` -- this module never imports
`erp_agent_os.evidence` (v1's schema) or reads any
`data/experiment_results*.json` legacy aggregate. That is not a
convention to remember; it is simply not possible to compute a v2.1
`AnalysisResult` from anything this module does not import.

**Every table carries its own source manifest.** `TableManifest`
(observation_archive_hash, analysis_code_hash, protocol_hash) is
attached to every generated table, so a reader can verify exactly which
archive, which version of this analysis code, and which frozen protocol
produced any given number -- three hashes, not a claim to trust.

Not executed as part of implementing this module: no real confirmatory
archive exists yet (Task 13, the actual campaign, has not run). Verified
instead against a synthetic archive built the same way Task 8/9's own
tests build one (see the module's own smoke path in
tests/test_claims_v2_1.py-adjacent fixtures), never by fabricating a
result and presenting it as the real campaign's output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from erp_agent_os.audit_reconstruction import reconstruct
from erp_agent_os.claims_v2_1 import (
    ClaimRecord,
    ConfirmatoryGateInputs,
    EvidenceState,
    build_claim_record,
    evidence_state_for_result,
)
from erp_agent_os.evidence_v2_1 import ObservationV21, load_observations_v21_jsonl
from erp_agent_os.freeze_v2_1 import (
    REPO_ROOT,
    CodeFreezeManifest,
    RunState,
    current_state,
    verify_code_freeze,
)
from erp_agent_os.statistics_v2_1 import (
    AnalysisResult,
    analyze_h1a,
    analyze_h1b,
    analyze_h2,
    analyze_h3a,
    analyze_h7,
    collapse_h3a_trio_consistency,
)

DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "protocol_v2_1" / "confirmatory_report.json"


class AnalyzeConfirmatoryError(RuntimeError):
    pass


# --------------------------------------------------------- raw extraction


def load_confirmatory_observations(
    archive_paths: Sequence[Path],
) -> list[ObservationV21]:
    """The ONLY way this module reads observation data -- every path
    goes through evidence_v2_1's own content-addressed loader, which
    already rejects a filename whose hash does not match its bytes."""
    observations: list[ObservationV21] = []
    for path in archive_paths:
        observations.extend(load_observations_v21_jsonl(path).observations)
    return observations


def stsr_success_by_scenario(
    observations: Sequence[ObservationV21], *, system: str, arm: str = "main"
) -> dict[str, bool]:
    return {
        o.scenario_id: bool(o.evaluator_components.get("success", False))
        for o in observations
        if o.system == system and o.arm == arm
    }


def total_tokens_by_scenario(
    observations: Sequence[ObservationV21], *, system: str, arm: str = "h2_tokens"
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for o in observations:
        if o.system != system or o.arm != arm:
            continue
        totals[o.scenario_id] = float(
            sum(e.prompt_tokens + e.completion_tokens for e in o.call_events)
        )
    return totals


def audit_all_facts_by_scenario(
    observations: Sequence[ObservationV21], *, system: str, arm: str = "main"
) -> dict[str, bool]:
    return {
        o.scenario_id: reconstruct(o.normalized_trace).all_facts_success
        for o in observations
        if o.system == system and o.arm == arm
    }


# ------------------------------------------------------------- manifests


@dataclass(frozen=True)
class TableManifest:
    table_name: str
    observation_archive_hash: str
    analysis_code_hash: str
    protocol_hash: str


ANALYSIS_CODE_FILES: tuple[str, ...] = (
    "src/erp_agent_os/statistics_v2_1.py",
    "src/erp_agent_os/claims_v2_1.py",
    "scripts/analyze_confirmatory_v2_1.py",
)


def compute_analysis_code_hash(*, repo_root: Path = REPO_ROOT) -> str:
    hasher = hashlib.sha256()
    for relative in ANALYSIS_CODE_FILES:
        hasher.update((repo_root / relative).read_bytes())
    return hasher.hexdigest()


def compute_archive_set_hash(archive_paths: Sequence[Path]) -> str:
    hasher = hashlib.sha256()
    for path in sorted(archive_paths):
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _table(
    name: str, *, archive_hash: str, analysis_code_hash: str, protocol_hash: str
) -> TableManifest:
    return TableManifest(name, archive_hash, analysis_code_hash, protocol_hash)


# ---------------------------------------------------------------- report


@dataclass(frozen=True)
class ReportEntry:
    result: AnalysisResult | None
    claim: ClaimRecord
    manifest: TableManifest


def _load_code_manifest(path: Path) -> CodeFreezeManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CodeFreezeManifest(**payload)


def _campaign_gate(
    receipt_log: Path, code_manifest: CodeFreezeManifest
) -> ConfirmatoryGateInputs:
    state = current_state(receipt_log)
    drift = verify_code_freeze(code_manifest)
    return ConfirmatoryGateInputs(
        run_completed=state is RunState.RUN_COMPLETED,
        hashes_valid=not drift,
        observations_complete=state is RunState.RUN_COMPLETED,
        registered_analysis_ran=True,
        no_open_protocol_violation=not drift,
    )


def _entry_for(
    hypothesis: str,
    result: AnalysisResult | None,
    *,
    gate: ConfirmatoryGateInputs,
    claim_text: str,
    archive_hash: str,
    analysis_code_hash: str,
    protocol_hash: str,
) -> ReportEntry:
    if result is None:
        evidence_state = EvidenceState.NOT_MEASURED
        text = f"{hypothesis}: no observations available for this population."
    else:
        evidence_state = evidence_state_for_result(result, gate)
        text = claim_text
    claim = build_claim_record(
        hypothesis=hypothesis,
        evidence_state=evidence_state,
        claim_text=text,
        observation_archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )
    manifest = _table(
        hypothesis,
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )
    return ReportEntry(result=result, claim=claim, manifest=manifest)


def generate_report(
    archive_paths: Sequence[Path],
    *,
    code_manifest: CodeFreezeManifest,
    receipt_log: Path,
    protocol_hash: str,
) -> dict[str, object]:
    observations = load_confirmatory_observations(archive_paths)
    gate = _campaign_gate(receipt_log, code_manifest)
    archive_hash = compute_archive_set_hash(archive_paths)
    analysis_code_hash = compute_analysis_code_hash()

    entries: dict[str, ReportEntry] = {}

    success_a = stsr_success_by_scenario(observations, system="A")
    success_b = stsr_success_by_scenario(observations, system="B")
    success_c = stsr_success_by_scenario(observations, system="C")

    h1a_result = analyze_h1a(success_a, success_c) if success_a and success_c else None
    entries["h1a"] = _entry_for(
        "h1a",
        h1a_result,
        gate=gate,
        claim_text=(
            f"H1a: verdict={h1a_result.verdict if h1a_result else 'n/a'}, "
            f"CI low={h1a_result.ci_low if h1a_result else 'n/a'}."
        ),
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    h1b_result = (
        analyze_h1b(success_c, success_b, comparator_name="B")
        if success_b and success_c
        else None
    )
    entries["h1b"] = _entry_for(
        "h1b",
        h1b_result,
        gate=gate,
        claim_text=(
            f"H1b: verdict={h1b_result.verdict if h1b_result else 'n/a'}, "
            f"CI low={h1b_result.ci_low if h1b_result else 'n/a'}."
        ),
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    tokens_a = total_tokens_by_scenario(observations, system="A")
    tokens_c = total_tokens_by_scenario(observations, system="C")
    h2_result = (
        analyze_h2(tokens_c, tokens_a, comparator_name="A")
        if tokens_a and tokens_c
        else None
    )
    entries["h2"] = _entry_for(
        "h2",
        h2_result,
        gate=gate,
        claim_text=f"H2: verdict={h2_result.verdict if h2_result else 'n/a'}.",
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    h3a_rows = [o for o in observations if o.arm == "h3a_stability"]
    h3a_result = None
    if h3a_rows:
        collapsed = collapse_h3a_trio_consistency(h3a_rows)
        consistency_a = {s: v for (s, sys_), v in collapsed.items() if sys_ == "A"}
        consistency_c = {s: v for (s, sys_), v in collapsed.items() if sys_ == "C"}
        if consistency_a and consistency_c:
            h3a_result = analyze_h3a(consistency_c, consistency_a, comparator_name="A")
    entries["h3a"] = _entry_for(
        "h3a",
        h3a_result,
        gate=gate,
        claim_text=f"H3a: verdict={h3a_result.verdict if h3a_result else 'n/a'}.",
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    facts_a = audit_all_facts_by_scenario(observations, system="A")
    facts_c = audit_all_facts_by_scenario(observations, system="C")
    h7_result = (
        analyze_h7(facts_c, facts_a, comparator_name="A")
        if facts_a and facts_c
        else None
    )
    entries["h7"] = _entry_for(
        "h7",
        h7_result,
        gate=gate,
        claim_text=f"H7: verdict={h7_result.verdict if h7_result else 'n/a'}.",
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    return {
        "campaign_state": current_state(receipt_log).value,
        "hypotheses": {
            name: {
                "result": asdict(entry.result) if entry.result else None,
                "claim": entry.claim.to_dict(),
                "table_manifest": asdict(entry.manifest),
            }
            for name, entry in entries.items()
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, action="append", required=True)
    parser.add_argument("--code-manifest-path", type=Path, required=True)
    parser.add_argument("--receipt-log", type=Path, required=True)
    parser.add_argument("--protocol-hash", type=str, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    code_manifest = _load_code_manifest(args.code_manifest_path)
    report = generate_report(
        args.archive,
        code_manifest=code_manifest,
        receipt_log=args.receipt_log,
        protocol_hash=args.protocol_hash,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
