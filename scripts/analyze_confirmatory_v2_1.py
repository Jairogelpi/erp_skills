#!/usr/bin/env python
"""Generate the v2.1 confirmatory report from raw JSONL only (Task 11).

    uv run python scripts/analyze_confirmatory_v2_1.py \\
        --archive data/protocol_v2_1/runs/confirmatory_observations_v21_<hash>.jsonl \\
        --code-manifest-path data/protocol_v2_1/code_freeze_manifest.json \\
        --receipt-log data/protocol_v2_1/runs/receipts.jsonl \\
        --protocol-hash <code_freeze_manifest.json's component_hashes.protocol> \\
        --seed <the SAME --seed run_confirmatory_v2_1.py was launched with> \\
        --output data/protocol_v2_1/confirmatory_report.json

`--protocol-hash` is read straight out of the already-generated
`code_freeze_manifest.json`'s own `component_hashes.protocol` field --
never recomputed here, so this report and `verify_code_freeze` can
never silently disagree on what "the protocol" was.

`--seed` should match the seed the real run's `generate_holdout` used
(default 20260814 on both scripts). Verified empirically, not assumed:
`scenario_id` and `expected_skill` assignment are seed-INVARIANT
(section 5.1's ordinal/slot allocation depends only on n_main, never
the seed; only argument VALUES are seeded) -- `gold_by_scenario_id`'s
`expected_skill` lookup, the only gold field H5 reads, is therefore
robust to an accidental seed mismatch here. Still pass the real one:
it is what actually generated the campaign, and a future extension
that reads a seed-sensitive gold field (arguments, expected_state_delta)
would silently regress this guarantee if the value here were wrong.

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
from erp_agent_os.cost_scenarios_v2_1 import CostBreakdown, compute_cost_sensitivity
from erp_agent_os.evaluator_v2_1 import (
    ExecutionOutcome,
    evaluate_false_allow,
    evaluate_unauthorized_mutation,
)
from erp_agent_os.evidence_v2_1 import ObservationV21, load_observations_v21_jsonl
from erp_agent_os.freeze_v2_1 import (
    REPO_ROOT,
    CodeFreezeManifest,
    RunState,
    current_state,
    load_selected_sample_sizes,
    verify_code_freeze,
)
from erp_agent_os.protocol_v2_1 import ProtocolV21, load_protocol
from erp_agent_os.scenarios_v2_1 import build_gold, generate_scenarios
from erp_agent_os.security_scenarios_v2_1 import generate_security_population
from erp_agent_os.statistics_v2_1 import (
    AnalysisResult,
    RetrievalCase,
    analyze_h1a,
    analyze_h1b,
    analyze_h2,
    analyze_h3a,
    analyze_h3b,
    analyze_h4_binary_endpoint,
    analyze_h4_unauthorized_mutation,
    analyze_h5,
    analyze_h6,
    analyze_h7,
    apply_h4_holm_family,
    collapse_h3a_trio_consistency,
    collapse_h3b_trio_consistency,
    compute_retrieval_metrics,
)

DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "protocol_v2_1" / "confirmatory_report.json"

# H8 has no verdict field (section 8: "no una hipótesis de ahorro
# observado") -- it is reported as OBSERVED_DESCRIPTIVE unconditionally
# whenever the archive has data for a system, never gated through the
# confirmatory supported/not_supported machinery every other hypothesis
# in this file uses.
_DANGEROUS_GOLD: dict[str, str] = {"expected_decision": "DENY"}


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


def _outcome_from_observation(observation: ObservationV21) -> ExecutionOutcome:
    """The evaluator's only window into "what happened" (see
    erp_agent_os.evaluator_v2_1), built from a raw row's own recorded
    fields -- never from what a system claims about itself elsewhere."""
    return ExecutionOutcome(
        selected_skill_id=observation.selected_skill_id,
        arguments=dict(observation.extracted_arguments),
        decision=observation.policy_decision,
        final_state_delta=dict(observation.observed_state_delta),
    )


def false_allow_by_scenario(
    observations: Sequence[ObservationV21], *, system: str
) -> dict[str, bool]:
    """H4 false allow, over the dangerous population only. Gold is the
    constant {"expected_decision": "DENY"} -- every dangerous scenario's
    gold decision is DENY by construction (erp_agent_os.
    security_scenarios_v2_1), so no per-scenario gold lookup is needed
    here, unlike H5/H6 below."""
    return {
        o.scenario_id: evaluate_false_allow(
            _DANGEROUS_GOLD, _outcome_from_observation(o)
        )
        for o in observations
        if o.system == system and o.population == "dangerous"
    }


def detection_by_scenario(
    observations: Sequence[ObservationV21], *, system: str
) -> dict[str, bool]:
    """Pre-execution detection recall (section 8, H4) is exactly the
    complement of false allow for the dangerous population: a DENY
    decision. Derived from the same rows/oracle as false_allow_by_
    scenario rather than re-deriving policy_decision comparisons ad
    hoc, so the two endpoints cannot silently disagree on one row."""
    return {
        scenario_id: not false_allow
        for scenario_id, false_allow in false_allow_by_scenario(
            observations, system=system
        ).items()
    }


def unauthorized_mutation_by_scenario(
    observations: Sequence[ObservationV21], *, system: str
) -> dict[str, bool]:
    return {
        o.scenario_id: evaluate_unauthorized_mutation(
            _DANGEROUS_GOLD, _outcome_from_observation(o)
        )
        for o in observations
        if o.system == system and o.population == "dangerous"
    }


def gold_by_scenario_id(
    *, seed: int, n_main: int, n_security_dangerous: int
) -> dict[str, dict[str, object]]:
    """H5's Top-1/Top-3/MRR need the position of the EXPECTED skill
    within a system's own candidate ranking -- something no
    ObservationV21 row carries (gold is a property of the scenario,
    never a system's claim, so it is deliberately absent from the
    evidence contract). Scenario generation is a pure, deterministic
    function of (seed, n_main) -- docs/tfm-closure-no-human-v2.1.md
    section 5.2 -- so regenerating it here to look up gold reproduces
    the exact same ScenarioSpecs the real campaign used; it is not
    "trusting a system under test", and `build_gold` reads only latent
    fields, never a rendered surface's wording."""
    main = generate_scenarios(seed=seed, n_main=n_main)
    dangerous, safe = generate_security_population(n_dangerous=n_security_dangerous)
    return {s.scenario_id: build_gold(s) for s in (*main, *dangerous, *safe)}


def _committed_and_correct(observation: ObservationV21) -> tuple[bool, bool]:
    """(committed, correct) for H5/H6's coverage/false-reuse-risk pair,
    read from fields every main-arm row already carries -- policy_
    decision for "did the system commit to a skill at all" and the
    execution-time evaluator_components["action_correct"] (computed
    against the SAME gold at run time) for "was the committed skill the
    right one". Reused by both H5's RetrievalCase.abstained and H6's
    false-reuse indicator so the two hypotheses cannot silently
    disagree on what "committed" means for the same row."""
    committed = observation.policy_decision != "ABSTAIN"
    correct = bool(observation.evaluator_components.get("action_correct"))
    return committed, correct


def false_reuse_by_scenario(
    observations: Sequence[ObservationV21], *, system: str
) -> dict[str, bool]:
    """H6: true iff the system committed to a skill (did not abstain)
    and that skill was wrong -- an abstention is never counted as false
    reuse, no matter what it would have picked (section 20: coverage
    and false-reuse risk are always reported as a pair, one is never
    inflated by hiding behind the other)."""
    result: dict[str, bool] = {}
    for o in observations:
        if o.system != system or o.arm != "main":
            continue
        committed, correct = _committed_and_correct(o)
        result[o.scenario_id] = committed and not correct
    return result


def coverage_by_system(observations: Sequence[ObservationV21], *, system: str) -> float:
    rows = [o for o in observations if o.system == system and o.arm == "main"]
    if not rows:
        raise AnalyzeConfirmatoryError(f"no main-arm rows for system {system!r}")
    committed = sum(1 for o in rows if o.policy_decision != "ABSTAIN")
    return committed / len(rows)


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
    "src/erp_agent_os/cost_scenarios_v2_1.py",
    "src/erp_agent_os/audit_reconstruction.py",
    "src/erp_agent_os/evaluator_v2_1.py",
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


def _safe_claim_text(hypothesis: str, result: AnalysisResult | None) -> str:
    """Never embeds `result.verdict`'s raw string. Some verdict values
    (e.g. H1b's "superior") collide with claims_v2_1's own
    conditionally-forbidden vocabulary -- and `build_claim_record`
    enforces that even for a machine-generated echo of an internal
    label, not just free-written human prose. Found via the end-to-end
    report test: with this template, `generate_report` crashed entirely
    whenever H1b's verdict was "superior" and the campaign gate was not
    yet CONFIRMATORY_SUPPORTED (any report generated before
    RUN_COMPLETED, or with any hash drift -- a routine, expected case,
    not an edge case). The verdict itself is never lost: it remains
    present, unconstrained, in this same entry's structured `result`
    field of the report -- only the free-text claim avoids it."""
    if result is None:
        return f"{hypothesis}: no observations available for this population."
    return (
        f"{hypothesis}: n={result.n}, estimate={result.estimate}, "
        f"ci_low={result.ci_low}, ci_high={result.ci_high}."
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


def _descriptive_entry_for(
    hypothesis: str,
    result: AnalysisResult | None,
    *,
    claim_text: str,
    archive_hash: str,
    analysis_code_hash: str,
    protocol_hash: str,
) -> ReportEntry:
    """H3b/H8's own path (section 8/10: both are explicitly secondary/
    descriptive, no preregistered criterion) -- deliberately never calls
    `evidence_state_for_result`, which would run `result.verdict`
    through the confirmatory supported/not_supported gate and raise for
    verdicts like "observed" that are descriptive on purpose (see
    erp_agent_os.statistics_v2_1.analyze_h3b's own docstring)."""
    evidence_state = (
        EvidenceState.NOT_MEASURED
        if result is None
        else EvidenceState.OBSERVED_DESCRIPTIVE
    )
    text = (
        f"{hypothesis}: no observations available for this population."
        if result is None
        else claim_text
    )
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
    protocol: ProtocolV21,
    protocol_hash: str,
    seed: int,
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
        claim_text=_safe_claim_text("h1a", h1a_result),
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
        claim_text=_safe_claim_text("h1b", h1b_result),
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
        claim_text=_safe_claim_text("h2", h2_result),
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
        claim_text=_safe_claim_text("h3a", h3a_result),
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
        claim_text=_safe_claim_text("h7", h7_result),
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    # ------------------------------------------------------------- H3b

    h3b_rows = [o for o in observations if o.arm == "h3b_repetition"]
    h3b_result = None
    if h3b_rows:
        collapsed = collapse_h3b_trio_consistency(h3b_rows)
        consistency_c = {s: v for (s, sys_), v in collapsed.items() if sys_ == "C"}
        if consistency_c:
            h3b_result = analyze_h3b(consistency_c)
    entries["h3b"] = _descriptive_entry_for(
        "h3b",
        h3b_result,
        claim_text=_safe_claim_text("h3b", h3b_result),
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    # -------------------------------------------------------------- H4

    false_allow_c = false_allow_by_scenario(observations, system="C")
    false_allow_a = false_allow_by_scenario(observations, system="A")
    false_allow_b = false_allow_by_scenario(observations, system="B")
    detection_c = detection_by_scenario(observations, system="C")
    detection_a = detection_by_scenario(observations, system="A")
    detection_b = detection_by_scenario(observations, system="B")
    mutation_c = unauthorized_mutation_by_scenario(observations, system="C")

    fa_a_result = (
        analyze_h4_binary_endpoint(
            false_allow_c,
            false_allow_a,
            endpoint_name="false_allow",
            comparator_name="A",
            direction="lower_favors_c",
        )
        if false_allow_c and false_allow_a
        else None
    )
    fa_b_result = (
        analyze_h4_binary_endpoint(
            false_allow_c,
            false_allow_b,
            endpoint_name="false_allow",
            comparator_name="B",
            direction="lower_favors_c",
        )
        if false_allow_c and false_allow_b
        else None
    )
    det_a_result = (
        analyze_h4_binary_endpoint(
            detection_c,
            detection_a,
            endpoint_name="detection_recall",
            comparator_name="A",
            direction="higher_favors_c",
        )
        if detection_c and detection_a
        else None
    )
    det_b_result = (
        analyze_h4_binary_endpoint(
            detection_c,
            detection_b,
            endpoint_name="detection_recall",
            comparator_name="B",
            direction="higher_favors_c",
        )
        if detection_c and detection_b
        else None
    )
    # apply_h4_holm_family requires EXACTLY four comparisons -- only
    # apply it when all four actually computed, never a partial family
    # (a partial Holm correction over 2 or 3 of the 4 would understate
    # the multiplicity adjustment the other two still need).
    h4_family = [fa_a_result, fa_b_result, det_a_result, det_b_result]
    if all(r is not None for r in h4_family):
        fa_a_result, fa_b_result, det_a_result, det_b_result = apply_h4_holm_family(
            [r for r in h4_family if r is not None]
        )

    for name, result in (
        ("h4_false_allow_a", fa_a_result),
        ("h4_false_allow_b", fa_b_result),
        ("h4_detection_a", det_a_result),
        ("h4_detection_b", det_b_result),
    ):
        entries[name] = _entry_for(
            name,
            result,
            gate=gate,
            claim_text=_safe_claim_text(name, result),
            archive_hash=archive_hash,
            analysis_code_hash=analysis_code_hash,
            protocol_hash=protocol_hash,
        )

    mutation_result = (
        analyze_h4_unauthorized_mutation(list(mutation_c.values()))
        if mutation_c
        else None
    )
    entries["h4_unauthorized_mutation"] = _entry_for(
        "h4_unauthorized_mutation",
        mutation_result,
        gate=gate,
        claim_text=_safe_claim_text("h4_unauthorized_mutation", mutation_result),
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    # -------------------------------------------------------------- H5

    sample_sizes = load_selected_sample_sizes()
    gold = gold_by_scenario_id(
        seed=seed,
        n_main=sample_sizes["n_main"],
        n_security_dangerous=sample_sizes["n_security_dangerous"],
    )
    main_c_rows = [o for o in observations if o.system == "C" and o.arm == "main"]
    retrieval_cases = [
        RetrievalCase(
            scenario_id=o.scenario_id,
            expected_skill=gold[o.scenario_id].get("expected_skill"),
            ranked_skill_ids=o.ranked_skill_ids,
            selected_skill_id=o.selected_skill_id,
            abstained=o.policy_decision == "ABSTAIN",
        )
        for o in main_c_rows
        if o.scenario_id in gold
    ]
    h5_result = None
    if any(case.expected_skill is not None for case in retrieval_cases):
        retrieval_metrics = compute_retrieval_metrics(retrieval_cases)
        h5_result = analyze_h5(
            retrieval_metrics,
            thresholds={
                "selective_accuracy_min": protocol.h5.selective_accuracy_min,
                "false_reuse_max": protocol.h5.false_reuse_max,
                "coverage_min": protocol.h5.coverage_min,
            },
        )
    entries["h5"] = _entry_for(
        "h5",
        h5_result,
        gate=gate,
        claim_text=_safe_claim_text("h5", h5_result),
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    # -------------------------------------------------------------- H6

    false_reuse_c = false_reuse_by_scenario(observations, system="C")
    false_reuse_ablation = false_reuse_by_scenario(
        observations, system="C_NO_ABSTENTION"
    )
    h6_result = None
    if false_reuse_c and false_reuse_ablation:
        h6_result = analyze_h6(
            false_reuse_c,
            false_reuse_ablation,
            coverage_c=coverage_by_system(observations, system="C"),
            coverage_ablation=coverage_by_system(
                observations, system="C_NO_ABSTENTION"
            ),
        )
    entries["h6"] = _entry_for(
        "h6",
        h6_result,
        gate=gate,
        claim_text=_safe_claim_text("h6", h6_result),
        archive_hash=archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )

    # -------------------------------------------------------------- H8

    h8_breakdowns: tuple[CostBreakdown, ...] = ()
    systems_with_main_rows = sorted(
        {o.system for o in observations if o.arm == "main"} & {"A", "B", "C"}
    )
    if systems_with_main_rows:
        h8_breakdowns = compute_cost_sensitivity(
            observations, protocol.h8, systems=tuple(systems_with_main_rows)
        )
    h8_claim = build_claim_record(
        hypothesis="h8",
        evidence_state=(
            EvidenceState.OBSERVED_DESCRIPTIVE
            if h8_breakdowns
            else EvidenceState.NOT_MEASURED
        ),
        claim_text=(
            f"H8: {len(h8_breakdowns)} (system, grid point) cost breakdowns computed."
            if h8_breakdowns
            else "H8: no observations available for this population."
        ),
        observation_archive_hash=archive_hash,
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
        "h8_cost_sensitivity": {
            "claim": h8_claim.to_dict(),
            "breakdowns": [asdict(b) for b in h8_breakdowns],
        },
    }


DEFAULT_PROTOCOL_PATH = REPO_ROOT / "config" / "protocol_v2_1.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, action="append", required=True)
    parser.add_argument("--code-manifest-path", type=Path, required=True)
    parser.add_argument("--receipt-log", type=Path, required=True)
    parser.add_argument("--protocol-hash", type=str, required=True)
    parser.add_argument("--protocol-path", type=Path, default=DEFAULT_PROTOCOL_PATH)
    parser.add_argument(
        "--seed",
        type=int,
        default=20260814,
        help=(
            "Same seed the real campaign generated its holdout with "
            "(erp_agent_os.freeze_v2_1.generate_holdout) -- required to "
            "regenerate gold for H5 (section 5.2: scenario generation is "
            "a pure function of this seed and n_main)."
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    code_manifest = _load_code_manifest(args.code_manifest_path)
    protocol = load_protocol(args.protocol_path)
    report = generate_report(
        args.archive,
        code_manifest=code_manifest,
        receipt_log=args.receipt_log,
        protocol=protocol,
        protocol_hash=args.protocol_hash,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
