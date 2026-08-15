"""TDD for erp_agent_os.experiment_v2_1 (v2.1 plan, Task 8, steps 1-2)."""

from __future__ import annotations

from typing import Any

import pytest

from erp_agent_os.evidence_v2_1 import ObservationV21, validate_arm_semantics
from erp_agent_os.experiment_v2_1 import (
    AllAttemptsFailedError,
    ArmRunContext,
    RecordingLLMClient,
    _observe_delta,
    _side_effects,
    build_h2_arm_plan,
    build_h3a_arm_plan,
    build_h3b_arm_plan,
    build_h4_arm_plan,
    build_h6_ablation_plan,
    build_main_arm_plan,
    run_a,
    run_b,
    run_c,
    run_h2_arm,
    run_h3a_arm,
    run_h3b_arm,
    run_h4_arm,
    run_h6_ablation,
    run_main_arm,
)
from erp_agent_os.llm_client import ArgumentExtraction, ToolCall
from erp_agent_os.scenarios_v2_1 import CASE_KIND_NORMAL, generate_scenarios
from erp_agent_os.security_scenarios_v2_1 import generate_security_population
from erp_agent_os.surfaces_v2_1 import SurfaceKind, render_surface


class _CountingFakeLLM:
    """A fake LLMClient (not a real provider) whose first `fail_times`
    calls of each kind raise before succeeding -- used to prove
    RecordingLLMClient's own retry loop, not any real provider's."""

    def __init__(
        self,
        *,
        extraction: dict[str, Any] | None = None,
        tool_name: str | None = None,
        fail_times: int = 0,
    ) -> None:
        self.propose_calls = 0
        self.extract_calls = 0
        self._extraction = extraction or {}
        self._tool_name = tool_name
        self._fail_times = fail_times
        self._propose_failures = 0
        self._extract_failures = 0

    def propose_action(self, query_text: str, tools: list) -> ToolCall:
        self.propose_calls += 1
        if self._propose_failures < self._fail_times:
            self._propose_failures += 1
            raise RuntimeError("transient failure")
        return ToolCall(self._tool_name, {}, prompt_tokens=10, completion_tokens=5)

    def extract_arguments(
        self, query_text: str, fields: list[str]
    ) -> ArgumentExtraction:
        self.extract_calls += 1
        if self._extract_failures < self._fail_times:
            self._extract_failures += 1
            raise RuntimeError("transient failure")
        return ArgumentExtraction(
            dict(self._extraction), prompt_tokens=7, completion_tokens=3
        )


def _context(**overrides) -> ArmRunContext:
    base = dict(
        protocol_version="2.1.0",
        frozen_commit="abc123",
        dataset_hash="ds-hash",
        provider="fake",
        model="fake-model",
        provider_config={"temperature": 0.0},
        code_version_hash="code-hash",
        dependency_lock_hash="lock-hash",
        timeout_seconds=30.0,
        max_call_attempts=3,
    )
    base.update(overrides)
    return ArmRunContext(**base)


def _normal_r1_scenario():
    scenarios = generate_scenarios()
    for ordinal, scenario in enumerate(scenarios):
        if scenario.case_kind != CASE_KIND_NORMAL:
            continue
        if scenario.expected_skill is None:
            continue
        if scenario.risk_class != "R1":
            continue
        return scenario, ordinal
    raise AssertionError("no normal R1 scenario found in the generated corpus")


def _known_fully_accurate_scenario():
    """A scenario whose gold IS currently accurate end to end -- see
    test_KNOWN_GAP_gold_state_delta_omits_handler_derived_fields below
    for the (real, measured, NOT fixed here) reason most create-operation
    scenarios are not yet usable for this. crm.update_expected_revenue
    (R2) works here specifically because, unapproved, it never reaches
    execution at all -- both gold and the real observed delta correctly
    agree on "no_change" without ever exercising the update-field gap.
    Looked up by property (skill/case_kind/risk), not a hardcoded
    scenario_id -- the generator's exact id assignment is an
    implementation detail (erp_agent_os.scenarios_v2_1's own
    round-robin slot allocation), not a fixture contract."""
    scenarios = generate_scenarios()
    for scenario in scenarios:
        if (
            scenario.expected_skill == "crm.update_expected_revenue"
            and scenario.case_kind == CASE_KIND_NORMAL
            and scenario.risk_class == "R2"
        ):
            return scenario
    raise AssertionError(
        "expected a normal R2 crm.update_expected_revenue scenario, found none"
    )


# --------------------------------------------------------- retry telemetry


def test_call_with_retries_records_one_event_per_attempt_including_failures():
    fake = _CountingFakeLLM(extraction={"customer_name": "Acme"}, fail_times=2)
    recorder = RecordingLLMClient(fake, max_attempts=3)

    result = recorder.extract_arguments("texto", ["customer_name"])

    assert result.arguments == {"customer_name": "Acme"}
    assert fake.extract_calls == 3
    assert len(recorder.events) == 3
    assert [e.success for e in recorder.events] == [False, False, True]
    assert [e.attempt for e in recorder.events] == [1, 2, 3]
    assert recorder.events[0].error_class == "RuntimeError"
    assert recorder.events[-1].error_class is None
    assert recorder.events[-1].prompt_tokens == 7


def test_call_with_retries_raises_after_exhausting_the_budget():
    fake = _CountingFakeLLM(fail_times=99)
    recorder = RecordingLLMClient(fake, max_attempts=2)

    with pytest.raises(AllAttemptsFailedError) as exc_info:
        recorder.extract_arguments("texto", ["customer_name"])

    assert len(exc_info.value.events) == 2
    assert all(not e.success for e in exc_info.value.events)


def test_successful_call_records_exactly_one_event():
    fake = _CountingFakeLLM(extraction={"customer_name": "Acme"})
    recorder = RecordingLLMClient(fake, max_attempts=3)

    recorder.extract_arguments("texto", ["customer_name"])

    assert fake.extract_calls == 1
    assert len(recorder.events) == 1
    assert recorder.events[0].success is True


# ------------------------------------------------------------ delta/effects


def test_observe_delta_reports_create_one_from_a_real_snapshot_diff():
    before = {"records": {"crm.lead": []}}
    after = {"records": {"crm.lead": [["1", {"name": "Acme"}]]}}
    delta = _observe_delta(
        before, after, "crm.lead", decision="ALLOW", operation="create", risk_class="R1"
    )
    assert delta == {"operation_kind": "create_one", "new_fields": {"name": "Acme"}}


def test_observe_delta_reports_no_change_for_a_denied_decision_even_if_state_moved():
    before = {"records": {"crm.lead": []}}
    after = {"records": {"crm.lead": [["1", {"name": "Acme"}]]}}
    delta = _observe_delta(
        before, after, "crm.lead", decision="DENY", operation="create", risk_class="R1"
    )
    assert delta == {"operation_kind": "no_change"}


def test_observe_delta_reports_read_only_for_an_allowed_read_with_no_mutation():
    before = after = {"records": {"crm.lead": []}}
    delta = _observe_delta(
        before, after, "crm.lead", decision="ALLOW", operation="read", risk_class="R0"
    )
    assert delta == {"operation_kind": "read_only"}


def test_side_effects_reports_only_other_models_that_actually_changed():
    before = {"records": {"crm.lead": [], "res.partner": [["9", {"x": 1}]]}}
    after = {"records": {"crm.lead": [["1", {}]], "res.partner": [["9", {"x": 2}]]}}
    assert _side_effects(before, after, "crm.lead") == ("res.partner",)
    assert _side_effects(before, before, "crm.lead") == ()


# ----------------------------------------------------------------- run_c/b/a


def test_run_c_produces_a_structurally_and_semantically_valid_main_row():
    scenario = _known_fully_accurate_scenario()
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    llm = _CountingFakeLLM(extraction=dict(scenario.arguments))
    context = _context()

    observation = run_c(scenario, surface, context, llm, arm="main")

    assert isinstance(observation, ObservationV21)
    assert observation.system == "C"
    assert observation.selected_skill_id == scenario.expected_skill
    assert observation.evaluator_components["success"] is True
    assert observation.selection_prompt_hash is None  # C never selects via LLM
    validate_arm_semantics(observation)  # does not raise


def test_gold_state_delta_matches_real_handler_output_whenever_retrieval_succeeds():
    """Regression for a real gap found while wiring this module (fixed in
    scenarios_v2_1.sandbox_execute, not here): `expected_state_delta`
    used to be built as a literal copy of a scenario's own arguments,
    but several of the 12 real, frozen handlers write additional or
    differently-named fields (crm_create_opportunity also writes
    state="open"; sales_add_quote_line writes last_line_product/
    last_line_quantity, not product_name/quantity; sales_confirm_order
    writes state="confirmed", absent from its arguments entirely).
    Measured before the fix: only 23/60 "normal" scenarios reached a
    fully accurate STSR with perfect argument extraction; after it,
    every single scenario the retriever actually identifies correctly
    does (44/44) -- the remaining 16/60 fail on retrieval margin/
    confusability between near-synonymous skill descriptions (TF-IDF's
    own, separately-documented limitation, H5's concern, not gold
    accuracy), never on a state-delta mismatch. This test locks in that
    100% conditional rate so gold accuracy cannot silently regress."""
    scenarios = [
        s
        for s in generate_scenarios()
        if s.case_kind == CASE_KIND_NORMAL and s.expected_skill is not None
    ]
    context = _context(max_call_attempts=1)
    retrieved_correctly = 0
    fully_successful = 0
    for scenario in scenarios:
        surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
        llm = _CountingFakeLLM(extraction=dict(scenario.arguments))
        observation = run_c(scenario, surface, context, llm)
        if observation.evaluator_components["action_correct"]:
            retrieved_correctly += 1
            if observation.evaluator_components["success"]:
                fully_successful += 1

    assert len(scenarios) == 60
    assert retrieved_correctly == 44  # measured 2026-08-15; TF-IDF's own limitation
    assert fully_successful == retrieved_correctly


def test_run_c_records_exactly_one_extraction_call_and_zero_selection_calls():
    scenario, _ = _normal_r1_scenario()
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    llm = _CountingFakeLLM(extraction=dict(scenario.arguments))
    context = _context(max_call_attempts=1)

    observation = run_c(scenario, surface, context, llm)

    assert llm.extract_calls == 1
    assert llm.propose_calls == 0
    assert len(observation.call_events) == 1
    assert observation.call_events[0].purpose == "argument_extraction"


def test_run_b_selects_via_the_llm_and_normalizes_arguments():
    scenario, _ = _normal_r1_scenario()
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    llm = _CountingFakeLLM(
        tool_name=scenario.expected_skill, extraction=dict(scenario.arguments)
    )
    context = _context()

    observation = run_b(scenario, surface, context, llm)

    assert observation.system == "B"
    assert observation.selected_skill_id == scenario.expected_skill
    assert llm.propose_calls == 1
    assert observation.selection_prompt_hash == context.selection_prompt_hash


def test_run_b_pays_its_own_real_extraction_call_same_as_a_and_c():
    """Regression: run_b used to call system.handle(text, {}) -- an
    always-empty argument dict that made every System B scenario fail
    on "missing required fields" regardless of tool selection, and
    silently gave B zero extraction token cost. D-03/section 7 require
    the SAME real extraction cost across A/B/C."""
    scenario, _ = _normal_r1_scenario()
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    llm = _CountingFakeLLM(
        tool_name=scenario.expected_skill, extraction=dict(scenario.arguments)
    )
    context = _context(max_call_attempts=1)

    observation = run_b(scenario, surface, context, llm)

    assert llm.extract_calls == 1
    assert observation.extracted_arguments == dict(scenario.arguments)
    assert observation.evaluator_components["success"] is True


def test_run_a_maps_its_generic_tool_call_back_onto_the_catalog_skill():
    scenario, _ = _normal_r1_scenario()
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    llm = _CountingFakeLLM(
        tool_name="create_record", extraction=dict(scenario.arguments)
    )
    context = _context()

    observation = run_a(scenario, surface, context, llm)

    assert observation.system == "A"
    assert observation.selected_skill_id == scenario.expected_skill
    assert observation.evaluator_components["action_correct"] is True


def test_run_a_pays_its_own_real_extraction_call_same_as_b_and_c():
    """Regression: run_a used to read scenario.arguments directly --
    a perfect parse nobody paid for, giving A zero extraction token cost
    while B and C paid theirs."""
    scenario, _ = _normal_r1_scenario()
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    llm = _CountingFakeLLM(
        tool_name="create_record", extraction=dict(scenario.arguments)
    )
    context = _context(max_call_attempts=1)

    observation = run_a(scenario, surface, context, llm)

    assert llm.extract_calls == 1
    assert observation.extracted_arguments == dict(scenario.arguments)


def test_run_a_final_state_diverges_from_a_governed_handlers_real_output():
    """System A writes raw arguments straight to FakeERPAdapter, bypassing
    the real handler entirely (CLAUDE.md section 18: no skill registry,
    no governance at all) -- so for a skill whose real handler derives an
    extra field (crm.create_opportunity also writes state="open"), A's
    record is legitimately INCOMPLETE relative to what a governed
    execution actually produces. Gold now reflects the real handler's
    output (scenarios_v2_1.sandbox_execute); this is what exposes the
    gap, not a bug in this test or in System A's own wiring."""
    scenario, _ = _normal_r1_scenario()
    assert scenario.expected_skill == "crm.create_opportunity"
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    llm = _CountingFakeLLM(
        tool_name="create_record", extraction=dict(scenario.arguments)
    )
    context = _context()

    observation = run_a(scenario, surface, context, llm)

    written_record = next(
        iter(observation.final_state["records"]["crm.opportunity"].values())
    )
    assert observation.evaluator_components["final_state_correct"] is False
    assert "state" not in written_record


# --------------------------------------------- comparable inputs (step 2)


def test_provider_config_and_extraction_prompt_hashes_match_across_a_b_c():
    """docs/tfm-closure-no-human-v2.1.md section 7: A/B/C must share
    provider config, extraction prompt, state and timeout/retry budget
    for the same unit. Selection prompt is shared by A/B only -- C
    structurally never calls a selection prompt, which is a declared
    architecture difference (section 7), not an accidental omission."""
    scenario, _ = _normal_r1_scenario()
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    context = _context()

    obs_a = run_a(
        scenario, surface, context, _CountingFakeLLM(tool_name="create_record")
    )
    obs_b = run_b(
        scenario, surface, context, _CountingFakeLLM(tool_name=scenario.expected_skill)
    )
    obs_c = run_c(
        scenario,
        surface,
        context,
        _CountingFakeLLM(extraction=dict(scenario.arguments)),
    )

    assert obs_a.provider_config_hash == obs_b.provider_config_hash
    assert obs_b.provider_config_hash == obs_c.provider_config_hash
    assert (
        obs_a.extraction_prompt_hash
        == obs_b.extraction_prompt_hash
        == obs_c.extraction_prompt_hash
    )
    assert obs_a.selection_prompt_hash == obs_b.selection_prompt_hash
    assert obs_a.selection_prompt_hash is not None
    assert obs_c.selection_prompt_hash is None
    assert obs_a.initial_state == obs_b.initial_state == obs_c.initial_state


def test_a_different_timeout_or_retry_budget_changes_the_provider_config_hash():
    """The hash must actually be sensitive to what section 7 requires
    identical -- otherwise a silent per-system config drift would go
    undetected by the very check meant to catch it."""
    context = _context(timeout_seconds=30.0)
    other = _context(timeout_seconds=99.0)
    assert context.provider_config_hash != other.provider_config_hash

    context2 = _context(max_call_attempts=3)
    other2 = _context(max_call_attempts=7)
    assert context2.provider_config_hash != other2.provider_config_hash


# ================================================== arm orchestration (3-9)


def _llm_by_system() -> dict:
    """One shared, structurally-permissive fake per system -- these arm
    tests exercise ORCHESTRATION (unit counts, systems, arms, surface
    rotation, checkpoint resume), not per-row STSR correctness, which
    the run_a/run_b/run_c tests above already cover directly."""
    return {
        "A": _CountingFakeLLM(tool_name="create_record", extraction={}),
        "B": _CountingFakeLLM(tool_name="crm.create_opportunity", extraction={}),
        "C": _CountingFakeLLM(extraction={}),
    }


def _small_scenario_slice(n: int = 4):
    return list(generate_scenarios())[:n]


def test_run_main_arm_produces_one_row_per_scenario_and_system():
    scenarios = _small_scenario_slice(3)
    observations = run_main_arm(scenarios, _llm_by_system(), _context())

    assert len(observations) == 3 * 3
    assert {o.system for o in observations} == {"A", "B", "C"}
    assert all(o.arm == "main" for o in observations)
    assert {o.scenario_id for o in observations} == {s.scenario_id for s in scenarios}


def test_run_h2_arm_only_includes_scenarios_with_an_expected_skill():
    scenarios = list(generate_scenarios())
    no_skill = [s for s in scenarios if s.expected_skill is None]
    assert no_skill  # sanity: the corpus does contain no-skill scenarios
    sample = _small_scenario_slice(3) + no_skill[:1]

    observations = run_h2_arm(sample, _llm_by_system(), _context())

    assert len(observations) == 3 * 3  # the no_skill one excluded, x3 systems
    assert all(o.arm == "h2_tokens" for o in observations)
    assert all(o.scenario_id != no_skill[0].scenario_id for o in observations)


def test_run_h3a_arm_produces_all_three_surfaces_per_scenario_and_system():
    scenarios = _small_scenario_slice(2)
    observations = run_h3a_arm(scenarios, _llm_by_system(), _context())

    assert len(observations) == 2 * 3 * 3  # scenarios x surfaces x systems
    for scenario in scenarios:
        kinds = {
            o.surface_kind
            for o in observations
            if o.scenario_id == scenario.scenario_id
        }
        assert kinds == {"S1", "S2", "S3"}


def test_run_h3b_arm_produces_repeated_calls_on_the_same_surface():
    scenarios = _small_scenario_slice(2)
    observations = run_h3b_arm(scenarios, _llm_by_system(), _context(), repetitions=3)

    assert len(observations) == 2 * 3 * 3  # scenarios x systems x repetitions
    assert {o.repetition_index for o in observations} == {0, 1, 2}
    for scenario in scenarios:
        surface_ids = {
            o.surface_id for o in observations if o.scenario_id == scenario.scenario_id
        }
        assert len(surface_ids) == 1  # same surface reused across repetitions


def test_run_h4_arm_pairs_dangerous_and_safe_rows_and_shares_their_renderer():
    dangerous, safe = generate_security_population()
    observations = run_h4_arm(dangerous[:2], safe[:2], _llm_by_system(), _context())

    assert len(observations) == 2 * 2 * 3  # pairs x populations x systems
    assert {o.population for o in observations} == {"dangerous", "safe_control"}
    for i in range(2):
        pair_rows = [
            o
            for o in observations
            if o.scenario_id in (dangerous[i].scenario_id, safe[i].scenario_id)
        ]
        assert len({o.security_pair_id for o in pair_rows}) == 1
        assert len({o.control_stratum for o in pair_rows}) == 1
        assert len({o.surface_kind for o in pair_rows}) == 1  # shared renderer
        assert all(o.control_stratum == dangerous[i].attack_category for o in pair_rows)


def test_real_arm_output_satisfies_task_7b_semantic_completeness():
    """Task 7B's validate_arm_semantics was built and unit-tested on
    hand-built ObservationV21 fixtures (test_evidence_v2_1.py) but never
    actually run against Task 8's own runner output until now -- this
    closes that loop for every arm that has one."""
    context = _context()
    llm_by_system = _llm_by_system()
    scenarios = _small_scenario_slice(2)

    for observation in run_main_arm(scenarios, llm_by_system, context):
        validate_arm_semantics(observation)
    for observation in run_h2_arm(scenarios, llm_by_system, context):
        validate_arm_semantics(observation)

    dangerous, safe = generate_security_population()
    for observation in run_h4_arm(dangerous[:1], safe[:1], llm_by_system, context):
        validate_arm_semantics(observation)


def test_run_h6_ablation_relabels_system_and_shares_everything_else():
    scenarios = _small_scenario_slice(2)
    context = _context()
    llm = _CountingFakeLLM(extraction={})

    main_observations = run_main_arm(scenarios, {**_llm_by_system(), "C": llm}, context)
    main_c = [o for o in main_observations if o.system == "C"]
    ablation = run_h6_ablation(scenarios, llm, context)

    assert len(ablation) == len(main_c)
    assert all(o.system == "C_NO_ABSTENTION" for o in ablation)
    assert all(o.arm == "main" for o in ablation)
    for main_row, ablation_row in zip(main_c, ablation, strict=True):
        assert main_row.scenario_id == ablation_row.scenario_id
        assert main_row.request_text == ablation_row.request_text
        assert main_row.provider_config_hash == ablation_row.provider_config_hash


def test_checkpoint_resume_preserves_already_written_rows_and_skips_them(tmp_path):
    scenarios = _small_scenario_slice(2)
    checkpoint_path = tmp_path / "main.jsonl"
    llm_by_system = _llm_by_system()
    context = _context()

    first = run_main_arm(
        scenarios, llm_by_system, context, checkpoint_path=checkpoint_path
    )
    calls_after_first = llm_by_system["C"].extract_calls

    second = run_main_arm(
        scenarios, llm_by_system, context, checkpoint_path=checkpoint_path
    )
    calls_after_second = llm_by_system["C"].extract_calls

    assert len(first) == len(second) == 6
    assert calls_after_second == calls_after_first  # nothing re-called on resume
    assert [o.model_dump(mode="json") for o in first] == [
        o.model_dump(mode="json") for o in second
    ]


def test_h6_ablation_checkpoint_never_collides_with_main_arms(tmp_path):
    """The key_prefix guard on _run_plan: run_h6_ablation's plan entries
    carry system="C"/arm="main" internally (run_c hardcodes both; only
    relabeled to C_NO_ABSTENTION after _run_plan returns) -- pointed at
    the SAME checkpoint file as run_main_arm, they must not merge."""
    scenarios = _small_scenario_slice(1)
    checkpoint_path = tmp_path / "shared.jsonl"
    context = _context()
    llm = _CountingFakeLLM(extraction={})

    run_main_arm(
        scenarios,
        {**_llm_by_system(), "C": llm},
        context,
        checkpoint_path=checkpoint_path,
    )
    ablation = run_h6_ablation(scenarios, llm, context, checkpoint_path=checkpoint_path)

    assert len(ablation) == 1
    assert ablation[0].system == "C_NO_ABSTENTION"


# ============================================ plan-size-without-executing


def test_build_main_arm_plan_size_matches_what_run_main_arm_actually_executes():
    scenarios = _small_scenario_slice(3)
    plan = build_main_arm_plan(scenarios)
    observations = run_main_arm(scenarios, _llm_by_system(), _context())
    assert len(plan) == len(observations) == len(scenarios) * 3


def test_build_h2_arm_plan_size_matches_what_run_h2_arm_actually_executes():
    scenarios = list(generate_scenarios())
    no_skill = [s for s in scenarios if s.expected_skill is None]
    sample = _small_scenario_slice(3) + no_skill[:1]
    plan = build_h2_arm_plan(sample)
    observations = run_h2_arm(sample, _llm_by_system(), _context())
    assert len(plan) == len(observations) == 3 * 3  # the no_skill one excluded


def test_build_h3a_arm_plan_size_matches_what_run_h3a_arm_actually_executes():
    scenarios = _small_scenario_slice(2)
    plan = build_h3a_arm_plan(scenarios)
    observations = run_h3a_arm(scenarios, _llm_by_system(), _context())
    assert (
        len(plan) == len(observations) == len(scenarios) * 3 * 3
    )  # surfaces x systems


def test_build_h3b_arm_plan_size_matches_what_run_h3b_arm_actually_executes():
    scenarios = _small_scenario_slice(2)
    plan = build_h3b_arm_plan(scenarios, repetitions=3)
    observations = run_h3b_arm(scenarios, _llm_by_system(), _context(), repetitions=3)
    assert (
        len(plan) == len(observations) == len(scenarios) * 3 * 3
    )  # systems x repetitions


def test_build_h4_arm_plan_size_matches_what_run_h4_arm_actually_executes():
    dangerous, safe = generate_security_population()
    plan = build_h4_arm_plan(dangerous[:2], safe[:2])
    observations = run_h4_arm(dangerous[:2], safe[:2], _llm_by_system(), _context())
    assert len(plan) == len(observations) == 2 * 2 * 3  # pairs x populations x systems


def test_build_h6_ablation_plan_size_matches_what_run_h6_ablation_actually_executes():
    scenarios = _small_scenario_slice(2)
    plan = build_h6_ablation_plan(scenarios)
    llm = _CountingFakeLLM(extraction={})
    observations = run_h6_ablation(scenarios, llm, _context())
    assert len(plan) == len(observations) == len(scenarios)
