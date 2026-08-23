import hashlib
import json

import pytest

from erp_agent_os.evidence import (
    OBSERVATION_SCHEMA_VERSION,
    load_observations_jsonl,
    trace_from_execution_record,
    validate_observation_units,
    write_observations_jsonl,
)
from erp_agent_os.metrics import ExecutionRecord


def _record(request_id: str = "r1", system: str = "C", repetition: int = 0):
    return ExecutionRecord(
        request_id=request_id,
        system=system,
        repetition=repetition,
        selected_skill_id="crm.create_opportunity",
        decision="ALLOW",
        postconditions_met=True,
        side_effect_free=True,
        ranked_skill_ids=("crm.create_opportunity",),
        final_state={"crm.opportunity": [["1", {"state": "open"}]]},
        initial_state={"records": {}, "next_id": 1},
        normalized_arguments={"customer_name": "Acme", "expected_revenue": 1000},
        candidate_scores={"crm.create_opportunity": 0.9},
        role="erp_user",
        policy_reasons=("allowed",),
        permission_evidence="allowed_role",
        selected_skill_version="1.0.0",
        handler_name="erp_agent_os.handlers.crm_create_opportunity",
        postcondition_evidence={"opportunity_is_open": True},
        traceability_components={
            "request_identity": 1.0,
            "interpretation": 1.0,
            "candidate_or_abstention": 1.0,
            "policy_decision": 1.0,
            "skill_version_and_key": 1.0,
            "result_and_effects": 1.0,
            "postcondition_or_block_evidence": 1.0,
        },
    )


def test_observation_archive_round_trips_and_is_content_addressed(tmp_path):
    records = [_record()]
    archive = write_observations_jsonl(
        records,
        tmp_path / "run.json",
        provenance={
            "dataset_hash": "abc",
            "epistemic_status": "post_freeze_exploratory",
        },
    )

    assert archive.path.name == f"run_observations_{archive.sha256}.jsonl"
    assert archive.row_count == 1
    assert hashlib.sha256(archive.path.read_bytes()).hexdigest() == archive.sha256
    loaded = load_observations_jsonl(archive.path)
    assert loaded.schema_version == OBSERVATION_SCHEMA_VERSION
    assert loaded.provenance["epistemic_status"] == "post_freeze_exploratory"
    assert loaded.records == records


def test_archive_refuses_conflicting_content_at_existing_address(tmp_path):
    first = write_observations_jsonl(
        [_record()], tmp_path / "run.json", provenance={"dataset_hash": "abc"}
    )
    first.path.write_text("different", encoding="utf-8")

    with pytest.raises(FileExistsError, match="content-addressed"):
        write_observations_jsonl(
            [_record()], tmp_path / "run.json", provenance={"dataset_hash": "abc"}
        )


def test_unit_validation_rejects_duplicates_and_missing_units():
    with pytest.raises(ValueError, match="duplicate"):
        validate_observation_units(
            [_record(), _record()],
            request_ids={"r1"},
            systems={"A", "B", "C"},
            repetitions=1,
        )

    with pytest.raises(ValueError, match="missing"):
        validate_observation_units(
            [_record(system="A"), _record(system="B")],
            request_ids={"r1"},
            systems={"A", "B", "C"},
            repetitions=1,
        )


def test_archive_rows_include_semantically_auditable_evidence(tmp_path):
    archive = write_observations_jsonl(
        [_record()], tmp_path / "run.json", provenance={"dataset_hash": "abc"}
    )
    observation = json.loads(archive.path.read_text(encoding="utf-8").splitlines()[1])[
        "record"
    ]

    assert observation["normalized_arguments"]["customer_name"] == "Acme"
    assert observation["candidate_scores"]["crm.create_opportunity"] == 0.9
    assert observation["initial_state"]["records"] == {}
    assert observation["postcondition_evidence"]["opportunity_is_open"] is True
    assert len(observation["traceability_components"]) == 7


def test_trace_from_execution_record_feeds_a_recoverable_reconstruction():
    from erp_agent_os.audit_reconstruction import reconstruct

    trace = trace_from_execution_record(_record())
    result = reconstruct(trace)

    # request_text/intent are not carried by v1's ExecutionRecord, so
    # those two facts genuinely cannot be fully recovered from it -- the
    # adapter must not fabricate them to force a passing result.
    assert result.facts["intent_and_arguments"].present is False
    assert result.facts["policy_permission_decision"].recovered is True
    assert result.facts["exact_tool_skill_handler_version"].recovered is True
    assert result.facts["selected_action_or_skill"].recovered is True


def test_trace_from_execution_record_marks_placeholder_role_as_missing():
    record = ExecutionRecord(
        request_id="r2",
        system="A",
        repetition=0,
        selected_skill_id=None,
        decision="DENY",
        postconditions_met=None,
        side_effect_free=True,
        role="not_available",
        handler_name="not_available",
    )
    trace = trace_from_execution_record(record)
    assert trace["role"] is None
    assert trace["handler"] is None
