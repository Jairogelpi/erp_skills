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
    run_a,
    run_b,
    run_c,
)
from erp_agent_os.llm_client import ArgumentExtraction, ToolCall
from erp_agent_os.scenarios_v2_1 import CASE_KIND_NORMAL, generate_scenarios
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
    agree on "no_change" without ever exercising the update-field gap."""
    scenarios = generate_scenarios()
    for scenario in scenarios:
        if scenario.scenario_id == "scn-0002-0":
            return scenario
    raise AssertionError("expected fixture scenario scn-0002-0 not found")


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
    llm = _CountingFakeLLM(tool_name=scenario.expected_skill)
    context = _context()

    observation = run_b(scenario, surface, context, llm)

    assert observation.system == "B"
    assert observation.selected_skill_id == scenario.expected_skill
    assert llm.propose_calls == 1
    assert observation.selection_prompt_hash == context.selection_prompt_hash


def test_run_a_maps_its_generic_tool_call_back_onto_the_catalog_skill():
    scenario, _ = _normal_r1_scenario()
    surface = render_surface(scenario, SurfaceKind.S1_TEMPLATE)
    llm = _CountingFakeLLM(tool_name="create_record")
    context = _context()

    observation = run_a(scenario, surface, context, llm)

    assert observation.system == "A"
    assert observation.selected_skill_id == scenario.expected_skill
    assert observation.evaluator_components["action_correct"] is True


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
    llm = _CountingFakeLLM(tool_name="create_record")
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
