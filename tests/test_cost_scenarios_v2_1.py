"""TDD for erp_agent_os.cost_scenarios_v2_1 (v2.1 plan, Task 9B)."""

from __future__ import annotations

import dataclasses

import pytest

from erp_agent_os.cost_scenarios_v2_1 import (
    HYPOTHETICAL_FIELD_NAMES,
    MEASURED_FIELD_NAMES,
    CostBreakdown,
    CostGridPoint,
    CostScenarioError,
    MeasuredComponents,
    build_cost_grid,
    compute_cost_breakdown,
    compute_cost_sensitivity,
    measure_components,
    validate_cost_grid_coverage,
)
from erp_agent_os.evidence_v2_1 import ModelCallEvent, ObservationV21
from erp_agent_os.protocol_v2_1 import H8CostGrid

_CONFIG = H8CostGrid(
    inference_price_eur_per_million_tokens=[0.10, 1.0, 10.0],
    review_cost_eur_per_hour=[20.0, 40.0, 80.0],
    review_minutes=[1.0, 3.0, 10.0],
    error_cost_eur=[10.0, 100.0, 1000.0],
)


def _call_event(**overrides) -> ModelCallEvent:
    base = {
        "purpose": "argument_extraction",
        "attempt": 1,
        "success": True,
        "error_class": None,
        "prompt_tokens": 50,
        "completion_tokens": 20,
        "latency_seconds": 0.1,
        "cache_hit": False,
    }
    base.update(overrides)
    return ModelCallEvent(**base)


def _observation(**overrides) -> ObservationV21:
    base = {
        "protocol_version": "2.1.0",
        "frozen_commit": "abc",
        "dataset_hash": "d",
        "scenario_id": "scn-0001-0",
        "surface_id": "scn-0001-0:S1",
        "surface_kind": "S1",
        "security_pair_id": None,
        "population": "main",
        "control_stratum": None,
        "system": "C",
        "arm": "main",
        "repetition_index": 0,
        "provider": "fake",
        "model": "fake-model",
        "provider_config_hash": "cfg",
        "selection_prompt_hash": None,
        "extraction_prompt_hash": "ext",
        "started_at": "2026-08-15T00:00:00Z",
        "completed_at": "2026-08-15T00:00:01Z",
        "correlation_id": "scn-0001-0",
        "request_text": "texto",
        "extracted_arguments": {},
        "selected_skill_id": "crm.create_opportunity",
        "ranked_skill_ids": (),
        "candidate_scores": {},
        "policy_decision": "ALLOW",
        "policy_reasons": (),
        "call_events": (_call_event(),),
        "latency_seconds": 0.1,
        "initial_state": {},
        "final_state": {},
        "observed_state_delta": {"operation_kind": "no_change"},
        "postcondition_evidence": {},
        "side_effects": (),
        "raw_trace": {"x": 1},
        "normalized_trace": {"x": 1},
        "evaluator_components": {"success": True},
        "code_version_hash": "code",
        "dependency_lock_hash": "lock",
    }
    base.update(overrides)
    return ObservationV21(**base)


# ------------------------------------------------------------- grid coverage


def test_build_cost_grid_has_exactly_81_points():
    grid = build_cost_grid(_CONFIG)
    assert len(grid) == 81
    assert len(set(grid)) == 81  # no duplicates


def test_build_cost_grid_covers_the_full_cartesian_product():
    grid = build_cost_grid(_CONFIG)
    expected = {
        (price, hourly, minutes, error)
        for price in _CONFIG.inference_price_eur_per_million_tokens
        for hourly in _CONFIG.review_cost_eur_per_hour
        for minutes in _CONFIG.review_minutes
        for error in _CONFIG.error_cost_eur
    }
    actual = {
        (
            p.inference_price_eur_per_million_tokens,
            p.review_cost_eur_per_hour,
            p.review_minutes,
            p.error_cost_eur,
        )
        for p in grid
    }
    assert actual == expected


def test_validate_cost_grid_coverage_accepts_a_complete_report():
    observations = [_observation(system=s) for s in ("A", "B", "C")]
    results = compute_cost_sensitivity(observations, _CONFIG)
    validate_cost_grid_coverage(results, _CONFIG, systems=("A", "B", "C"))  # no raise


def test_validate_cost_grid_coverage_rejects_a_missing_scenario():
    observations = [_observation(system=s) for s in ("A", "B", "C")]
    results = list(compute_cost_sensitivity(observations, _CONFIG))
    filtered = [
        r
        for r in results
        if not (r.system == "C" and r.grid_point == results[0].grid_point)
    ]
    with pytest.raises(CostScenarioError):
        validate_cost_grid_coverage(filtered, _CONFIG, systems=("A", "B", "C"))


def test_validate_cost_grid_coverage_rejects_a_selectively_filtered_report():
    """ "Selectively filtered" -- e.g. keeping only grid points favorable
    to C -- must be rejected exactly like an outright missing point."""
    observations = [_observation(system=s) for s in ("A", "B", "C")]
    results = list(compute_cost_sensitivity(observations, _CONFIG))
    favorable_only = [
        r
        for r in results
        if r.grid_point.inference_price_eur_per_million_tokens == 0.10
    ]
    with pytest.raises(CostScenarioError):
        validate_cost_grid_coverage(favorable_only, _CONFIG, systems=("A", "B", "C"))


def test_validate_cost_grid_coverage_rejects_duplicate_grid_points():
    observations = [_observation(system="C")]
    results = list(compute_cost_sensitivity(observations, _CONFIG, systems=("C",)))
    duplicated = [*results, results[0]]
    with pytest.raises(CostScenarioError):
        validate_cost_grid_coverage(duplicated, _CONFIG, systems=("C",))


# --------------------------------------------------------- measured vs hypothetical


def test_no_field_anywhere_is_named_observed_savings():
    for cls in (CostGridPoint, MeasuredComponents, CostBreakdown):
        field_names = {f.name for f in dataclasses.fields(cls)}
        assert "observed_savings" not in field_names


def test_measured_and_hypothetical_field_sets_do_not_overlap():
    assert MEASURED_FIELD_NAMES.isdisjoint(HYPOTHETICAL_FIELD_NAMES)


def test_cost_breakdown_fields_partition_into_measured_and_hypothetical_plus_derived():
    breakdown_fields = {f.name for f in dataclasses.fields(CostBreakdown)}
    derived = {
        "system",
        "grid_point",
        "inference_cost_eur",
        "review_cost_eur",
        "error_cost_eur",
        "total_cost_eur",
    }
    assert breakdown_fields == MEASURED_FIELD_NAMES | derived


def test_measured_components_only_contains_measured_fields():
    measured_fields = {f.name for f in dataclasses.fields(MeasuredComponents)}
    assert measured_fields == MEASURED_FIELD_NAMES | {"system"}


def test_grid_point_only_contains_hypothetical_fields():
    grid_fields = {f.name for f in dataclasses.fields(CostGridPoint)}
    assert grid_fields == HYPOTHETICAL_FIELD_NAMES


def test_measure_components_reads_tokens_directly_from_call_events():
    observations = [
        _observation(
            system="C",
            call_events=(
                _call_event(prompt_tokens=100, completion_tokens=40),
                _call_event(
                    purpose="tool_selection", prompt_tokens=30, completion_tokens=10
                ),
            ),
        )
    ]
    measured = measure_components(observations, system="C")
    assert measured.total_tokens == 100 + 40 + 30 + 10


def test_measure_components_counts_retries_beyond_the_first_attempt_per_row():
    observations = [
        _observation(
            system="C",
            call_events=(
                _call_event(attempt=1, success=False, error_class="RateLimitError"),
                _call_event(attempt=2, success=True),
            ),
        ),
        _observation(
            system="C", scenario_id="scn-0002-0", call_events=(_call_event(),)
        ),
    ]
    measured = measure_components(observations, system="C")
    assert measured.n_retries == 1  # only the first row retried once


def test_measure_components_counts_real_require_approval_decisions():
    observations = [
        _observation(system="C", policy_decision="REQUIRE_APPROVAL"),
        _observation(system="C", scenario_id="scn-0002-0", policy_decision="ALLOW"),
    ]
    measured = measure_components(observations, system="C")
    assert measured.n_review_required == 1


def test_measure_components_counts_real_evaluator_failures():
    observations = [
        _observation(system="C", evaluator_components={"success": False}),
        _observation(
            system="C", scenario_id="scn-0002-0", evaluator_components={"success": True}
        ),
    ]
    measured = measure_components(observations, system="C")
    assert measured.n_observed_errors == 1


def test_measure_components_rejects_a_system_with_no_rows():
    with pytest.raises(CostScenarioError):
        measure_components([_observation(system="A")], system="C")


# ---------------------------------------------------------- cost computation


def test_compute_cost_breakdown_is_a_deterministic_pure_function():
    measured = MeasuredComponents(
        system="C",
        n_scenarios=10,
        total_tokens=1_000_000,
        n_retries=2,
        n_review_required=5,
        n_observed_errors=1,
    )
    point = CostGridPoint(
        inference_price_eur_per_million_tokens=1.0,
        review_cost_eur_per_hour=60.0,
        review_minutes=3.0,
        error_cost_eur=100.0,
    )
    result = compute_cost_breakdown(measured, point)

    assert result.inference_cost_eur == pytest.approx(1.0)  # 1M tokens * 1 EUR/M
    assert result.review_cost_eur == pytest.approx(5 * (3.0 / 60.0) * 60.0)  # = 15.0
    assert result.error_cost_eur == pytest.approx(1 * 100.0)
    assert result.total_cost_eur == pytest.approx(
        result.inference_cost_eur + result.review_cost_eur + result.error_cost_eur
    )


def test_compute_cost_breakdown_never_carries_a_verdict_field():
    measured = MeasuredComponents("C", 1, 0, 0, 0, 0)
    point = CostGridPoint(1.0, 20.0, 1.0, 10.0)
    result = compute_cost_breakdown(measured, point)
    field_names = {f.name for f in dataclasses.fields(result)}
    assert not any("verdict" in name for name in field_names)
    assert not any("pass" in name.lower() for name in field_names)


def test_compute_cost_sensitivity_returns_every_system_times_every_grid_point():
    observations = [_observation(system=s) for s in ("A", "B", "C")]
    results = compute_cost_sensitivity(observations, _CONFIG)
    assert len(results) == 3 * 81
    assert {r.system for r in results} == {"A", "B", "C"}


def test_compute_cost_sensitivity_does_not_single_out_the_most_favorable_point():
    """No aggregation, no "best case" selection -- every combination
    survives untouched in the output, in the exact quantity the grid
    times the system count implies."""
    observations = [_observation(system="C")]
    results = compute_cost_sensitivity(observations, _CONFIG, systems=("C",))
    assert len(results) == 81
    totals = {r.total_cost_eur for r in results}
    assert len(totals) > 1  # genuinely varies across the grid, not collapsed
