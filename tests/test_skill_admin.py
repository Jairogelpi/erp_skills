"""CU-02 backing logic for the product demo: draft, modify, diff, sandbox."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from erp_agent_os.skill_admin import (
    SkillAdmin,
    SkillAdminError,
    _repair_mojibake,
    bump_minor_version,
    diff_contract,
    draft_skill_contract,
    draft_skill_modification,
    evaluate_approval_conditions,
    parse_threshold,
    synthesize_sample_arguments,
)

_VALID_CONTRACT = {
    "skill_id": "demo.create_thing",
    "version": "1.0.0",
    "module": "demo",
    "operation": "create",
    "description": "Create a thing",
    "risk_class": "R1",
    "input_schema": {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
    },
    "permissions": {"allowed_roles": ["erp_user"]},
    "preconditions": [],
    "execution": {
        "handler": "demo_proposals.generic_create",
        "timeout_seconds": 10,
        "max_retries": 1,
        "idempotent": True,
    },
    "postconditions": ["exactly_one_new_record"],
    "approval_required_when": [],
    "state": "DRAFT",
}


def _mock_completion(monkeypatch, content: str) -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"choices": [{"message": {"content": content}}]}
    monkeypatch.setattr(
        "erp_agent_os.skill_admin.httpx.post", MagicMock(return_value=response)
    )


# --- pure helpers ---------------------------------------------------------


def test_bump_minor_version_increments_minor_and_resets_patch():
    assert bump_minor_version("1.0.0") == "1.1.0"
    assert bump_minor_version("2.4.9") == "2.5.0"


def test_bump_minor_version_falls_back_on_malformed_input():
    # A downstream SkillDefinition validator, not this helper, is the
    # place a genuinely bad version becomes a rejection.
    assert bump_minor_version("not-a-version") == "1.1.0"


def test_repair_mojibake_fixes_double_encoded_utf8():
    assert _repair_mojibake("lÃ­mite") == "límite"


def test_repair_mojibake_leaves_correct_text_untouched():
    assert _repair_mojibake("límite") == "límite"
    assert _repair_mojibake("plain ascii") == "plain ascii"


def test_synthesize_sample_arguments_covers_declared_types():
    schema = {
        "required": ["description", "amount", "urgent"],
        "properties": {
            "description": {"type": "string"},
            "amount": {"type": "number"},
            "urgent": {"type": "boolean"},
        },
    }
    sample = synthesize_sample_arguments(schema)
    assert sample["description"] == "valor de prueba"
    assert sample["amount"] == 1
    assert sample["urgent"] is True


def test_synthesize_sample_arguments_uses_readable_values_for_name_and_id_fields():
    # Cosmetic only (see the function's own docstring): a business-sounding
    # value instead of the literal words "valor de prueba", so a sandbox
    # result reads as a real record on camera.
    schema = {
        "required": ["client_id", "customer_name", "order_id", "notes"],
        "properties": {
            f: {"type": "string"}
            for f in ["client_id", "customer_name", "order_id", "notes"]
        },
    }
    sample = synthesize_sample_arguments(schema)
    assert sample["client_id"] == "Hotel Miramar"  # name-like wins over id-like
    assert sample["customer_name"] == "Hotel Miramar"
    assert sample["order_id"] == "1042"
    assert sample["notes"] == "valor de prueba"  # no match, unchanged fallback


def test_diff_contract_reports_only_changed_fields():
    old = dict(_VALID_CONTRACT)
    new = dict(_VALID_CONTRACT, description="Create a thing, faster", risk_class="R2")
    diff = diff_contract(old, new)
    fields = {entry["field"] for entry in diff}
    assert fields == {"description", "risk_class"}


def test_diff_contract_ignores_identity_and_lifecycle_fields():
    old = dict(_VALID_CONTRACT)
    new = dict(_VALID_CONTRACT, version="1.1.0", state="VALIDATED")
    # version is a real, intentional diff; skill_id/state are not shown.
    diff = diff_contract(old, new)
    fields = {entry["field"] for entry in diff}
    assert "skill_id" not in fields
    assert "state" not in fields
    assert "version" in fields


def test_diff_contract_empty_when_nothing_changed():
    assert diff_contract(_VALID_CONTRACT, dict(_VALID_CONTRACT)) == []


# --- LLM-backed drafting, network mocked -----------------------------------


def test_draft_skill_contract_forces_the_generic_handler(monkeypatch):
    payload = dict(_VALID_CONTRACT)
    payload["execution"] = {**payload["execution"], "handler": "something.else"}
    _mock_completion(monkeypatch, json.dumps(payload))

    contract = draft_skill_contract("crea una tarea", api_key="k")

    assert contract["execution"]["handler"] == "demo_proposals.generic_create"


def test_draft_skill_contract_raises_on_non_json_response(monkeypatch):
    _mock_completion(monkeypatch, "not json at all")
    with pytest.raises(SkillAdminError):
        draft_skill_contract("crea una tarea", api_key="k")


def test_draft_skill_modification_keeps_identity_and_bumps_version(monkeypatch):
    # The model tries to drift skill_id and pick its own version --
    # both must be overridden by the caller, not trusted from the LLM.
    modified = dict(
        _VALID_CONTRACT,
        skill_id="something.else.entirely",
        version="9.9.9",
        description="Create a thing, faster",
    )
    _mock_completion(monkeypatch, json.dumps(modified))

    contract = draft_skill_modification(
        _VALID_CONTRACT, "hazlo mas rapido", api_key="k"
    )

    assert contract["skill_id"] == _VALID_CONTRACT["skill_id"]
    assert contract["version"] == "1.1.0"
    assert contract["state"] == "DRAFT"
    assert contract["description"] == "Create a thing, faster"


# --- sandbox / registry lifecycle ------------------------------------------


def test_skill_admin_propose_then_approve_reaches_active():
    admin = SkillAdmin()
    sample = synthesize_sample_arguments(_VALID_CONTRACT["input_schema"])

    described = admin.propose(_VALID_CONTRACT, sample)
    assert described["state"] == "TESTED"

    # A real sandbox execution, independently re-read -- not a
    # simulation and not fabricated: the created record's own field
    # value matches what was actually passed in.
    preview = described["sandbox_preview"]
    assert preview["passed"] is True
    assert preview["created_record"]["name"] == sample["name"]

    approved = admin.approve(
        _VALID_CONTRACT["skill_id"], _VALID_CONTRACT["version"], approver="tutor"
    )
    assert approved["state"] == "ACTIVE"
    assert [h["to"] for h in approved["history"]] == [
        "DRAFT",
        "VALIDATED",
        "TESTED",
        "APPROVED",
        "ACTIVE",
    ]


def test_skill_admin_approve_requires_a_named_approver():
    admin = SkillAdmin()
    sample = synthesize_sample_arguments(_VALID_CONTRACT["input_schema"])
    admin.propose(_VALID_CONTRACT, sample)

    with pytest.raises(SkillAdminError):
        admin.approve(
            _VALID_CONTRACT["skill_id"], _VALID_CONTRACT["version"], approver=""
        )


def test_skill_admin_testing_the_same_contract_twice_is_idempotent():
    # Real bug, found live: clicking "Validate + sandbox test" twice for
    # the same skill_id@version (no edits in between) raised a raw
    # DuplicateSkillError -- an unhandled 500 through the API, not a
    # SkillAdminError the frontend could show.
    admin = SkillAdmin()
    sample = synthesize_sample_arguments(_VALID_CONTRACT["input_schema"])
    first = admin.propose(_VALID_CONTRACT, sample)
    second = admin.propose(_VALID_CONTRACT, sample)
    assert second == first


def test_skill_admin_testing_an_edited_contract_under_the_same_version_errors():
    admin = SkillAdmin()
    sample = synthesize_sample_arguments(_VALID_CONTRACT["input_schema"])
    admin.propose(_VALID_CONTRACT, sample)

    edited = dict(_VALID_CONTRACT, description="a different description")
    with pytest.raises(SkillAdminError):
        admin.propose(edited, sample)


def test_skill_admin_rejects_r4_at_the_schema():
    bad = dict(_VALID_CONTRACT, risk_class="R4")
    with pytest.raises(SkillAdminError):
        SkillAdmin().propose(bad, {"name": "x"})


def test_skill_admin_list_proposals_and_registry_are_exposed():
    admin = SkillAdmin()
    sample = synthesize_sample_arguments(_VALID_CONTRACT["input_schema"])
    admin.propose(_VALID_CONTRACT, sample)

    assert admin.proposal_ids == [
        (_VALID_CONTRACT["skill_id"], _VALID_CONTRACT["version"])
    ]
    assert len(admin.list_proposals()) == 1
    history = admin.registry.history(
        _VALID_CONTRACT["skill_id"], _VALID_CONTRACT["version"]
    )
    assert history  # append-only trail exists from registration onward


# --- approval-condition evaluator: Skill Studio demo only, isolated -------


def test_parse_threshold_recognises_the_recognised_shapes():
    assert parse_threshold("si afecta a mas de 10 oportunidades") == 10
    assert parse_threshold("mayor a 5 registros") == 5
    assert parse_threshold("supera 20 clientes") == 20
    assert parse_threshold("excede 3 lineas") == 3
    assert parse_threshold("> 7") == 7


def test_parse_threshold_returns_none_for_unrecognised_text():
    assert parse_threshold("cuando le apetezca al jefe") is None
    assert parse_threshold("") is None


def test_evaluate_approval_conditions_matches_when_count_exceeds_threshold():
    result = evaluate_approval_conditions(["mas de 10 oportunidades"], 15)
    assert result["requires_approval"] is True
    assert result["matched_conditions"] == ["mas de 10 oportunidades"]
    assert result["unparsed_conditions"] == []


def test_evaluate_approval_conditions_does_not_match_at_or_below_threshold():
    for count in (10, 5, 0):
        result = evaluate_approval_conditions(["mas de 10 oportunidades"], count)
        assert result["requires_approval"] is False


def test_evaluate_approval_conditions_reports_unparsed_text_honestly():
    result = evaluate_approval_conditions(["cuando le apetezca al jefe"], 999)
    # A count this large must not silently satisfy a condition the
    # parser never understood -- "requires_approval" stays False and the
    # text is surfaced as unparsed, not swallowed as "no approval needed".
    assert result["requires_approval"] is False
    assert result["unparsed_conditions"] == ["cuando le apetezca al jefe"]


def test_evaluate_approval_conditions_any_matching_condition_is_enough():
    result = evaluate_approval_conditions(
        ["mas de 100 registros", "mas de 5 clientes"], 8
    )
    assert result["requires_approval"] is True
    assert result["matched_conditions"] == ["mas de 5 clientes"]
