"""End-to-end tests for scripts/analyze_confirmatory_v2_1.py's report
generator (Task 11).

This script existed with zero test coverage before this file: its own
docstring claimed a "synthetic archive... see the module's own smoke
path in tests/test_claims_v2_1.py-adjacent fixtures" that did not
actually exist anywhere in the repository, and `generate_report` only
ever wired h1a/h1b/h2/h3a/h7 into its `entries` dict -- h3b/h4/h5/h6/h8
were silently absent despite h4/h5/h6/h8's own analysis functions
already being implemented and tested in statistics_v2_1.py/
cost_scenarios_v2_1.py. This file both closes that coverage gap and
is the regression test for the wiring fix.

Real scenario/security generation is used to build gold-consistent
synthetic ObservationV21 rows (never invented scenario_ids) because
`generate_report` regenerates gold via the SAME frozen seed/sample
sizes the real campaign would use (`gold_by_scenario_id`) -- a
made-up scenario_id would simply be absent from that lookup and
silently excluded from H5, masking exactly the kind of wiring bug
this file exists to catch.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

from erp_agent_os.claims_v2_1 import EvidenceState
from erp_agent_os.evidence_v2_1 import ModelCallEvent, ObservationV21
from erp_agent_os.freeze_v2_1 import (
    REPO_ROOT,
    CodeFreezeManifest,
    load_selected_sample_sizes,
)
from erp_agent_os.protocol_v2_1 import load_protocol
from erp_agent_os.scenarios_v2_1 import generate_scenarios
from erp_agent_os.security_scenarios_v2_1 import generate_security_population

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "scripts"
    / "analyze_confirmatory_v2_1.py"
)
_spec = importlib.util.spec_from_file_location(
    "analyze_confirmatory_v2_1", _SCRIPT_PATH
)
assert _spec is not None and _spec.loader is not None
analyze_confirmatory_v2_1 = importlib.util.module_from_spec(_spec)
# dataclass field resolution (this module has several @dataclass(frozen=True)
# classes under `from __future__ import annotations`) looks the module up in
# sys.modules by name -- register it before exec_module, or dataclass
# processing crashes with "NoneType has no attribute __dict__".
sys.modules[_spec.name] = analyze_confirmatory_v2_1
_spec.loader.exec_module(analyze_confirmatory_v2_1)

SEED = 20260814

# A manifest with empty component_hashes reports every current
# component as "drifted" -- that only affects each entry's
# evidence_state (PROTOCOL_VIOLATION), never the AnalysisResult itself,
# which is what these tests check. Building a real, drift-free
# manifest would require freezing an actual commit/tag, out of scope
# for testing the report generator's own wiring.
_DUMMY_CODE_MANIFEST = CodeFreezeManifest(
    schema_version="2.1",
    git_commit="0" * 40,
    git_tag="test-tag",
    component_hashes={},
    frozen_at="2026-08-15T00:00:00Z",
)


@pytest.fixture(scope="module")
def real_scenarios():
    sizes = load_selected_sample_sizes()
    main = generate_scenarios(seed=SEED, n_main=sizes["n_main"])
    dangerous, safe = generate_security_population(
        n_dangerous=sizes["n_security_dangerous"]
    )
    return main, dangerous, safe


@pytest.fixture(scope="module")
def protocol():
    return load_protocol(REPO_ROOT / "config" / "protocol_v2_1.json")


def _row(**overrides) -> ObservationV21:
    defaults: dict[str, object] = dict(
        protocol_version="2.1.0",
        frozen_commit="abc",
        dataset_hash="d",
        scenario_id="scn",
        surface_id="scn:S1",
        surface_kind="S1",
        security_pair_id=None,
        population="main",
        control_stratum=None,
        system="C",
        arm="main",
        repetition_index=0,
        provider="fake",
        model="fake-model",
        provider_config_hash="cfg",
        selection_prompt_hash=None,
        extraction_prompt_hash="ext",
        started_at="2026-08-15T00:00:00Z",
        completed_at="2026-08-15T00:00:01Z",
        correlation_id="scn",
        request_text="texto",
        extracted_arguments={},
        selected_skill_id=None,
        ranked_skill_ids=(),
        candidate_scores={},
        policy_decision="ALLOW",
        policy_reasons=(),
        call_events=(),
        latency_seconds=0.1,
        initial_state={},
        final_state={},
        observed_state_delta={"operation_kind": "no_change"},
        postcondition_evidence={},
        side_effects=(),
        raw_trace={"x": 1},
        normalized_trace={"x": 1},
        evaluator_components={},
        code_version_hash="code",
        dependency_lock_hash="lock",
    )
    defaults.update(overrides)
    return ObservationV21(**defaults)


def _stsr_components(*, correct: bool) -> dict[str, bool]:
    return {
        "action_correct": correct,
        "arguments_correct": correct,
        "policy_correct": True,
        "final_state_correct": correct,
        "no_duplicate_mutation": True,
        "no_unrelated_side_effect": True,
        "success": correct,
    }


def _build_full_archive(
    real_scenarios,
) -> list[ObservationV21]:
    main, dangerous, safe = real_scenarios
    scorable = [s for s in main if s.expected_skill is not None][:20]
    rows: list[ObservationV21] = []

    # ---- main arm: H1a/H1b/H7, and H5/H6's own coverage/false-reuse.
    for i, scenario in enumerate(scorable):
        # C correct on all but one (so H1a/H1b/H7 are not degenerate
        # ceilings); A wrong on roughly half.
        c_correct = i != 0
        a_correct = i % 2 == 0
        rows.append(
            _row(
                scenario_id=scenario.scenario_id,
                surface_id=f"{scenario.scenario_id}:S1",
                system="C",
                arm="main",
                selected_skill_id=(
                    scenario.expected_skill if c_correct else "some.other_skill"
                ),
                ranked_skill_ids=(scenario.expected_skill,)
                if c_correct
                else ("some.other_skill", scenario.expected_skill),
                policy_decision="ALLOW",
                evaluator_components=_stsr_components(correct=c_correct),
            )
        )
        rows.append(
            _row(
                scenario_id=scenario.scenario_id,
                surface_id=f"{scenario.scenario_id}:S1",
                system="A",
                arm="main",
                selected_skill_id=(
                    scenario.expected_skill if a_correct else "some.other_skill"
                ),
                policy_decision="ALLOW",
                evaluator_components=_stsr_components(correct=a_correct),
            )
        )
        rows.append(
            _row(
                scenario_id=scenario.scenario_id,
                surface_id=f"{scenario.scenario_id}:S1",
                system="B",
                arm="main",
                selected_skill_id=(
                    scenario.expected_skill if a_correct else "some.other_skill"
                ),
                policy_decision="ALLOW",
                evaluator_components=_stsr_components(correct=a_correct),
            )
        )
        # H6's ablation: same scenario, system=C_NO_ABSTENTION, slightly
        # worse false-reuse than C's own main-arm row above.
        ablation_correct = i > 2
        rows.append(
            _row(
                scenario_id=scenario.scenario_id,
                surface_id=f"{scenario.scenario_id}:S1",
                system="C_NO_ABSTENTION",
                arm="main",
                selected_skill_id=(
                    scenario.expected_skill if ablation_correct else "some.other_skill"
                ),
                policy_decision="ALLOW",
                evaluator_components=_stsr_components(correct=ablation_correct),
            )
        )

    # ---- h2_tokens: A and C only (per H2's own registered comparison).
    for scenario in scorable[:10]:
        for system, tokens in (("A", (120, 60)), ("C", (30, 10))):
            rows.append(
                _row(
                    scenario_id=scenario.scenario_id,
                    surface_id=f"{scenario.scenario_id}:S1",
                    system=system,
                    arm="h2_tokens",
                    call_events=(
                        ModelCallEvent(
                            purpose="argument_extraction",
                            attempt=1,
                            success=True,
                            error_class=None,
                            prompt_tokens=tokens[0],
                            completion_tokens=tokens[1],
                            latency_seconds=0.2,
                        ),
                    ),
                )
            )

    # ---- h3a_stability: A and C, three surfaces each.
    for scenario in scorable[:8]:
        for system in ("A", "C"):
            consistent = system == "C"
            for kind in ("S1", "S2", "S3"):
                rows.append(
                    _row(
                        scenario_id=scenario.scenario_id,
                        surface_id=f"{scenario.scenario_id}:{kind}",
                        surface_kind=kind,
                        system=system,
                        arm="h3a_stability",
                        evaluator_components=_stsr_components(correct=consistent),
                    )
                )

    # ---- h3b_repetition: C only, three repetitions.
    for scenario in scorable[:8]:
        for repetition in range(3):
            rows.append(
                _row(
                    scenario_id=scenario.scenario_id,
                    surface_id=f"{scenario.scenario_id}:S1",
                    system="C",
                    arm="h3b_repetition",
                    repetition_index=repetition,
                    evaluator_components=_stsr_components(correct=True),
                )
            )

    # ---- h4_security: dangerous + safe_control, A/B/C.
    for i, (danger, safe_scenario) in enumerate(
        zip(dangerous[:16], safe[:16], strict=True)
    ):
        pair_id = danger.scenario_id.rsplit("-", 1)[0]
        for system, denies in (("A", i % 3 == 0), ("B", i % 3 != 2), ("C", True)):
            rows.append(
                _row(
                    scenario_id=danger.scenario_id,
                    surface_id=f"{danger.scenario_id}:S1",
                    system=system,
                    arm="h4_security",
                    population="dangerous",
                    security_pair_id=pair_id,
                    control_stratum=danger.attack_category,
                    policy_decision="DENY" if denies else "ALLOW",
                    observed_state_delta={
                        "operation_kind": "no_change" if denies else "create"
                    },
                )
            )
            rows.append(
                _row(
                    scenario_id=safe_scenario.scenario_id,
                    surface_id=f"{safe_scenario.scenario_id}:S1",
                    system=system,
                    arm="h4_security",
                    population="safe_control",
                    security_pair_id=pair_id,
                    control_stratum=danger.attack_category,
                    policy_decision="ALLOW",
                    evaluator_components=_stsr_components(correct=True),
                )
            )
    return rows


EXPECTED_HYPOTHESIS_KEYS = frozenset(
    {
        "h1a",
        "h1b",
        "h2",
        "h3a",
        "h3b",
        "h4_false_allow_a",
        "h4_false_allow_b",
        "h4_detection_a",
        "h4_detection_b",
        "h4_unauthorized_mutation",
        "h5",
        "h6",
        "h7",
    }
)


def test_generate_report_produces_every_registered_hypothesis(
    real_scenarios, protocol, tmp_path
):
    """Regression test for the wiring gap: before this fix, only
    h1a/h1b/h2/h3a/h7 ever appeared, no matter how complete the
    archive was."""
    rows = _build_full_archive(real_scenarios)
    report = _generate_report_from_rows(
        rows,
        code_manifest=_DUMMY_CODE_MANIFEST,
        receipt_log=tmp_path / "receipts.jsonl",
        protocol=protocol,
        protocol_hash="test-protocol-hash",
        seed=SEED,
    )

    hypotheses = report["hypotheses"]
    assert EXPECTED_HYPOTHESIS_KEYS <= set(hypotheses)
    for name in EXPECTED_HYPOTHESIS_KEYS:
        assert hypotheses[name]["result"] is not None, f"{name} has no result"

    # H3b/H8 are descriptive -- OBSERVED_DESCRIPTIVE, never a
    # confirmatory state, even though real data was present.
    assert (
        hypotheses["h3b"]["claim"]["evidence_state"]
        == EvidenceState.OBSERVED_DESCRIPTIVE.value
    )
    assert report["h8_cost_sensitivity"]["breakdowns"]
    assert (
        report["h8_cost_sensitivity"]["claim"]["evidence_state"]
        == EvidenceState.OBSERVED_DESCRIPTIVE.value
    )


def test_generate_report_on_an_empty_archive_measures_nothing(protocol, tmp_path):
    report = _generate_report_from_rows(
        [],
        code_manifest=_DUMMY_CODE_MANIFEST,
        receipt_log=tmp_path / "receipts.jsonl",
        protocol=protocol,
        protocol_hash="test-protocol-hash",
        seed=SEED,
    )
    hypotheses = report["hypotheses"]
    for name in EXPECTED_HYPOTHESIS_KEYS:
        assert hypotheses[name]["result"] is None
        assert hypotheses[name]["claim"]["evidence_state"] == "not_measured"
    assert report["h8_cost_sensitivity"]["breakdowns"] == []
    assert report["h8_cost_sensitivity"]["claim"]["evidence_state"] == "not_measured"


def _generate_report_from_rows(
    rows: list[ObservationV21],
    *,
    code_manifest: CodeFreezeManifest,
    receipt_log,
    protocol,
    protocol_hash: str,
    seed: int,
) -> dict[str, object]:
    """Exercises the exact same body as `generate_report`, but from
    in-memory rows instead of archive files on disk -- avoids writing
    and re-reading a real content-addressed JSONL archive just to unit
    test the analysis wiring, which is already covered independently by
    `load_confirmatory_observations`'s own tests in test_evidence_v2_1.py."""
    module = analyze_confirmatory_v2_1
    original_loader = module.load_confirmatory_observations
    original_archive_hash = module.compute_archive_set_hash
    try:
        module.load_confirmatory_observations = lambda _paths: rows
        module.compute_archive_set_hash = lambda _paths: "test-archive-hash"
        return module.generate_report(
            [pathlib.Path("unused.jsonl")],
            code_manifest=code_manifest,
            receipt_log=receipt_log,
            protocol=protocol,
            protocol_hash=protocol_hash,
            seed=seed,
        )
    finally:
        module.load_confirmatory_observations = original_loader
        module.compute_archive_set_hash = original_archive_hash
