"""Direct tests for the verification engine.

`postconditions.py` decides whether an execution actually reached the
expected state, so it drives STSR's fourth conjunct. It was previously
exercised only indirectly through the experiment runner; a defect here
would silently move every reported result.
"""

import pytest

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.handlers import HANDLERS, SKILL_MODELS
from erp_agent_os.postconditions import (
    UnknownPostconditionError,
    build_checks,
    read_only_checks,
)
from erp_agent_os.skills import SkillDefinition


def erp() -> FakeERPAdapter:
    return FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))


def run(skill_id: str, args: dict) -> tuple[FakeERPAdapter, dict, object]:
    store = erp()
    before = store.snapshot()
    output = HANDLERS[skill_id](store, args)
    return store, before, output


def test_every_catalog_skill_resolves_to_executable_checks():
    for skill in CATALOG:
        checks = build_checks(
            skill, {"expected_revenue": "1", "field": "precio"}, {"records": {}}
        )
        assert checks, f"{skill.skill_id} produced no checks"
        assert tuple(check.check_id for check in checks) == tuple(skill.postconditions)


def test_unknown_postcondition_is_rejected_not_silently_passed():
    base = CATALOG_BY_ID["tasks.create_task"]
    tampered = SkillDefinition(
        **{
            **base.model_dump(),
            "postconditions": ["a_postcondition_nobody_implemented"],
        }
    )
    with pytest.raises(UnknownPostconditionError):
        build_checks(tampered, {}, {"records": {}})


def test_unknown_exactly_one_new_prefix_is_also_rejected():
    base = CATALOG_BY_ID["tasks.create_task"]
    tampered = SkillDefinition(
        **{
            **base.model_dump(),
            "postconditions": ["exactly_one_new_unregistered_record"],
        }
    )

    with pytest.raises(UnknownPostconditionError):
        build_checks(tampered, {}, {"records": {}})


def test_checks_pass_on_a_correct_execution():
    skill = CATALOG_BY_ID["crm.create_opportunity"]
    args = {"customer_name": "Acme", "expected_revenue": "1000"}
    store, before, output = run(skill.skill_id, args)

    assert all(check(store, output) for check in build_checks(skill, args, before))


def test_named_catalog_checks_remain_directly_callable():
    skill = CATALOG_BY_ID["crm.create_opportunity"]
    args = {"customer_name": "Acme", "expected_revenue": "1000"}
    store, before, output = run(skill.skill_id, args)

    check = build_checks(skill, args, before)[0]

    assert check.check_id == skill.postconditions[0]
    assert check(store, output) is True


def test_exactly_one_new_fails_when_a_second_record_appears():
    skill = CATALOG_BY_ID["crm.create_opportunity"]
    args = {"customer_name": "Acme", "expected_revenue": "1000"}
    store, before, output = run(skill.skill_id, args)

    # Simulate a duplicate mutation after the fact.
    store.create("crm.opportunity", {"customer_name": "Acme"})

    assert not all(check(store, output) for check in build_checks(skill, args, before))


def test_state_check_fails_when_business_state_is_missing():
    # This is exactly how System A fails: it writes the fields but not the
    # business state the skill contract requires.
    skill = CATALOG_BY_ID["crm.create_opportunity"]
    args = {"customer_name": "Acme", "expected_revenue": "1000"}
    store = erp()
    before = store.snapshot()
    record_id = store.create("crm.opportunity", dict(args))  # no "state"

    assert not all(
        check(store, record_id) for check in build_checks(skill, args, before)
    )


def test_field_match_fails_when_the_value_differs():
    skill = CATALOG_BY_ID["crm.update_expected_revenue"]
    store = erp()
    store.create("crm.opportunity", {"expected_revenue": "1"}, record_id="OPP-1")
    before = store.snapshot()
    args = {"opportunity_id": "OPP-1", "expected_revenue": "9999"}
    HANDLERS[skill.skill_id](store, args)

    passing = build_checks(skill, args, before)
    assert all(check(store, "OPP-1") for check in passing)

    wrong = build_checks(skill, {**args, "expected_revenue": "1"}, before)
    assert not all(check(store, "OPP-1") for check in wrong)


def test_no_other_fields_changed_detects_collateral_edits():
    skill = CATALOG_BY_ID["crm.update_expected_revenue"]
    store = erp()
    store.create(
        "crm.opportunity", {"expected_revenue": "1", "owner": "ana"}, record_id="OPP-1"
    )
    before = store.snapshot()
    args = {"opportunity_id": "OPP-1", "expected_revenue": "500"}
    HANDLERS[skill.skill_id](store, args)
    store.update("crm.opportunity", "OPP-1", {"owner": "someone_else"})

    assert not all(check(store, "OPP-1") for check in build_checks(skill, args, before))


def test_output_shape_checks_reject_a_wrong_return_type():
    skill = CATALOG_BY_ID["inventory.check_availability"]
    store = erp()
    before = store.snapshot()
    checks = build_checks(skill, {"product_name": "X"}, before)

    assert not all(check(store, "not a dict") for check in checks)
    assert all(check(store, {"available_units": 5}) for check in checks)


def test_read_only_checks_detect_a_mutation():
    skill = CATALOG_BY_ID["contacts.search_contact"]
    store = erp()
    before = store.snapshot()
    checks = read_only_checks(skill, before)

    assert tuple(check.check_id for check in checks) == ("state_unchanged",)
    assert all(check(store, {"results": []}) for check in checks)

    store.create("contacts.contact", {"customer_name": "Acme"})
    assert not all(check(store, {"results": []}) for check in checks)


def test_read_only_state_invariant_detects_same_count_and_cross_model_edits():
    skill = CATALOG_BY_ID["contacts.search_contact"]
    store = erp()
    contact_id = store.create("contacts.contact", {"customer_name": "Acme"})
    before = store.snapshot()
    checks = read_only_checks(skill, before)

    store.update("contacts.contact", contact_id, {"customer_name": "Changed"})
    assert not all(check(store, {"results": []}) for check in checks)

    store.restore(before)
    store.create("tasks.task", {"title": "Collateral mutation"})
    assert not all(check(store, {"results": []}) for check in checks)
