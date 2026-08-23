"""TDD for erp_agent_os.evidence_v2_1 (v2.1 plan, Task 7B)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from erp_agent_os.evidence_v2_1 import (
    EvidenceV21Error,
    ModelCallEvent,
    ObservationV21,
    load_observations_v21_jsonl,
    surface_id_for,
    validate_arm_semantics,
    validate_observation_units_v21,
    write_observations_v21_jsonl,
)


def _call_event(**overrides) -> ModelCallEvent:
    base = dict(
        purpose="argument_extraction",
        attempt=1,
        success=True,
        error_class=None,
        prompt_tokens=120,
        completion_tokens=40,
        latency_seconds=0.42,
        cache_hit=False,
    )
    base.update(overrides)
    return ModelCallEvent(**base)


def _observation(**overrides) -> dict:
    scenario_id = overrides.pop("scenario_id", "scn-0001-0")
    surface_kind = overrides.pop("surface_kind", "S1")
    base: dict = dict(
        protocol_version="2.1.0",
        frozen_commit="abc123",
        dataset_hash="ds-hash",
        scenario_id=scenario_id,
        surface_id=surface_id_for(scenario_id, surface_kind),
        surface_kind=surface_kind,
        security_pair_id=None,
        population="main",
        control_stratum=None,
        system="C",
        arm="main",
        repetition_index=0,
        provider="groq",
        model="llama-3.1-8b-instant",
        provider_config_hash="cfg-hash",
        selection_prompt_hash=None,
        extraction_prompt_hash="extract-hash",
        started_at="2026-08-14T00:00:00Z",
        completed_at="2026-08-14T00:00:01Z",
        correlation_id="corr-1",
        request_text="Crea una oportunidad para Acme por 15000 euros.",
        extracted_arguments={"customer_name": "Acme", "expected_revenue": 15000.0},
        selected_skill_id="crm.create_opportunity",
        ranked_skill_ids=("crm.create_opportunity",),
        candidate_scores={"crm.create_opportunity": 0.9},
        policy_decision="ALLOW",
        policy_reasons=("allowed_role",),
        call_events=(_call_event(),),
        latency_seconds=0.5,
        initial_state={"crm.opportunity": []},
        final_state={"crm.opportunity": [["1", {"state": "open"}]]},
        observed_state_delta={"operation_kind": "create_one", "new_fields": {}},
        postcondition_evidence={"opportunity_is_open": True},
        side_effects=(),
        raw_trace={"raw": "trace"},
        normalized_trace={"normalized": "trace"},
        evaluator_components={"action_correct": True},
        code_version_hash="code-hash",
        dependency_lock_hash="lock-hash",
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------- ModelCallEvent


def test_model_call_event_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ModelCallEvent(**{**_call_event().model_dump(), "unexpected": True})


def test_model_call_event_requires_error_class_on_failure():
    with pytest.raises(ValidationError, match="error_class"):
        _call_event(success=False, error_class=None)


def test_model_call_event_forbids_error_class_on_success():
    with pytest.raises(ValidationError, match="error_class"):
        _call_event(success=True, error_class="RateLimitError")


def test_model_call_event_rejects_zero_or_negative_attempt():
    with pytest.raises(ValidationError, match="attempt"):
        _call_event(attempt=0)


def test_model_call_event_rejects_negative_tokens():
    with pytest.raises(ValidationError):
        _call_event(prompt_tokens=-1)


def test_model_call_event_accepts_a_genuine_failed_retry():
    event = _call_event(attempt=2, success=False, error_class="RateLimitError")
    assert event.success is False
    assert event.error_class == "RateLimitError"


# ------------------------------------------------------------ ObservationV21


def test_observation_rejects_missing_required_field():
    payload = _observation()
    del payload["scenario_id"]
    with pytest.raises(ValidationError):
        ObservationV21(**payload)


def test_observation_rejects_extra_field():
    payload = _observation()
    payload["totally_unexpected_field"] = True
    with pytest.raises(ValidationError):
        ObservationV21(**payload)


def test_observation_round_trips_a_valid_row():
    observation = ObservationV21(**_observation())
    assert observation.scenario_id == "scn-0001-0"
    assert observation.call_events[0].purpose == "argument_extraction"


def test_observation_rejects_negative_repetition_index():
    with pytest.raises(ValidationError, match="repetition_index"):
        ObservationV21(**_observation(repetition_index=-1))


def test_observation_rejects_negative_latency():
    with pytest.raises(ValidationError, match="latency_seconds"):
        ObservationV21(**_observation(latency_seconds=-0.1))


def test_main_population_rejects_a_security_pair_id():
    with pytest.raises(ValidationError, match="security_pair_id"):
        ObservationV21(**_observation(population="main", security_pair_id="sec-x-000"))


def test_dangerous_population_requires_a_security_pair_id():
    with pytest.raises(ValidationError, match="security_pair_id"):
        ObservationV21(
            **_observation(
                population="dangerous",
                arm="h4_security",
                control_stratum="r4_operation",
                policy_decision="DENY",
            )
        )


# -------------------------------------------------------------- archive I/O


def test_archive_round_trips_and_is_content_addressed(tmp_path):
    observations = [ObservationV21(**_observation())]
    archive = write_observations_v21_jsonl(
        observations,
        tmp_path / "run.json",
        provenance={
            "dataset_hash": "ds-hash",
            "epistemic_status": "post_freeze_exploratory",
        },
    )
    assert archive.path.name == f"run_observations_v21_{archive.sha256}.jsonl"
    assert archive.row_count == 1

    loaded = load_observations_v21_jsonl(archive.path)
    assert loaded.schema_version == "2.1"
    assert loaded.observations == observations


def test_archive_refuses_conflicting_content_at_existing_address(tmp_path):
    first = write_observations_v21_jsonl(
        [ObservationV21(**_observation())],
        tmp_path / "run.json",
        provenance={"dataset_hash": "ds-hash"},
    )
    first.path.write_text("different bytes entirely", encoding="utf-8")

    with pytest.raises(FileExistsError, match="content-addressed"):
        write_observations_v21_jsonl(
            [ObservationV21(**_observation())],
            tmp_path / "run.json",
            provenance={"dataset_hash": "ds-hash"},
        )


def test_load_rejects_a_renamed_archive_whose_filename_hash_no_longer_matches(tmp_path):
    archive = write_observations_v21_jsonl(
        [ObservationV21(**_observation())],
        tmp_path / "run.json",
        provenance={"dataset_hash": "ds-hash"},
    )
    renamed = archive.path.with_name("run_observations_v21_deadbeef.jsonl")
    archive.path.rename(renamed)

    with pytest.raises(EvidenceV21Error, match="filename hash"):
        load_observations_v21_jsonl(renamed)


def test_unit_validation_rejects_duplicates_missing_and_extra():
    obs = ObservationV21(**_observation())
    with pytest.raises(EvidenceV21Error, match="duplicate"):
        validate_observation_units_v21(
            [obs, obs],
            scenario_ids={"scn-0001-0"},
            systems={"A", "B", "C"},
            arm="main",
            repetitions=1,
        )

    only_a = ObservationV21(**_observation(system="A"))
    with pytest.raises(EvidenceV21Error, match="missing"):
        validate_observation_units_v21(
            [only_a],
            scenario_ids={"scn-0001-0"},
            systems={"A", "B", "C"},
            arm="main",
            repetitions=1,
        )

    covering = ObservationV21(**_observation())
    extra = ObservationV21(**_observation(scenario_id="scn-9999-0"))
    with pytest.raises(EvidenceV21Error, match="unexpected"):
        validate_observation_units_v21(
            [covering, extra],
            scenario_ids={"scn-0001-0"},
            systems={"C"},
            arm="main",
            repetitions=1,
        )


# ------------------------------------------------- arm-specific completeness


def test_h2_row_requires_nonempty_uncached_call_events():
    incomplete = ObservationV21(**_observation(arm="h2_tokens", call_events=()))
    with pytest.raises(EvidenceV21Error, match="call_events"):
        validate_arm_semantics(incomplete)

    cached = ObservationV21(
        **_observation(arm="h2_tokens", call_events=(_call_event(cache_hit=True),))
    )
    with pytest.raises(EvidenceV21Error, match="cached"):
        validate_arm_semantics(cached)

    complete = ObservationV21(**_observation(arm="h2_tokens"))
    validate_arm_semantics(complete)  # does not raise


def test_h3a_row_requires_a_surface_id_matching_its_own_scenario_and_kind():
    mismatched = ObservationV21(
        **_observation(arm="h3a_stability", surface_id="scn-wrong:S1")
    )
    with pytest.raises(EvidenceV21Error, match="surface_id"):
        validate_arm_semantics(mismatched)

    matching = ObservationV21(**_observation(arm="h3a_stability"))
    validate_arm_semantics(matching)  # does not raise


def test_h4_dangerous_row_requires_category_and_forbidden_delta_evidence():
    no_stratum = ObservationV21(
        **_observation(
            arm="h4_security",
            population="dangerous",
            security_pair_id="sec-r4_operation-000",
            control_stratum=None,
            policy_decision="DENY",
            observed_state_delta={"operation_kind": "no_change"},
        )
    )
    with pytest.raises(EvidenceV21Error, match="control_stratum"):
        validate_arm_semantics(no_stratum)

    no_delta_evidence = ObservationV21(
        **_observation(
            arm="h4_security",
            population="dangerous",
            security_pair_id="sec-r4_operation-000",
            control_stratum="r4_operation",
            policy_decision="DENY",
            observed_state_delta={},
        )
    )
    with pytest.raises(EvidenceV21Error, match="forbidden-delta"):
        validate_arm_semantics(no_delta_evidence)

    complete = ObservationV21(
        **_observation(
            arm="h4_security",
            population="dangerous",
            security_pair_id="sec-r4_operation-000",
            control_stratum="r4_operation",
            policy_decision="DENY",
            observed_state_delta={"operation_kind": "no_change"},
        )
    )
    validate_arm_semantics(complete)  # does not raise


def test_h4_safe_control_row_requires_its_declared_safe_gold_check():
    incomplete = ObservationV21(
        **_observation(
            arm="h4_security",
            population="safe_control",
            security_pair_id="sec-r4_operation-000",
            control_stratum="r4_operation",
            evaluator_components={},
        )
    )
    with pytest.raises(EvidenceV21Error, match="evaluator_components"):
        validate_arm_semantics(incomplete)

    complete = ObservationV21(
        **_observation(
            arm="h4_security",
            population="safe_control",
            security_pair_id="sec-r4_operation-000",
            control_stratum="r4_operation",
        )
    )
    validate_arm_semantics(complete)  # does not raise


def test_main_row_requires_raw_and_normalized_trace():
    no_raw = ObservationV21(**_observation(arm="main", raw_trace={}))
    with pytest.raises(EvidenceV21Error, match="raw_trace"):
        validate_arm_semantics(no_raw)

    no_normalized = ObservationV21(**_observation(arm="main", normalized_trace={}))
    with pytest.raises(EvidenceV21Error, match="normalized_trace"):
        validate_arm_semantics(no_normalized)


def test_a_structurally_valid_but_semantically_incomplete_row_fails():
    """The whole point of Task 7B step 4: passing Pydantic validation is
    not sufficient. An h2_tokens row with zero call events is a
    perfectly well-typed ObservationV21 and still must be rejected."""
    row = ObservationV21(**_observation(arm="h2_tokens", call_events=()))
    assert isinstance(row, ObservationV21)  # structurally valid
    with pytest.raises(EvidenceV21Error):
        validate_arm_semantics(row)  # semantically incomplete
