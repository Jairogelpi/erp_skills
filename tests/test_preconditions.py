import pytest

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.catalog import CATALOG_BY_ID
from erp_agent_os.dataset import RiskClass
from erp_agent_os.preconditions import (
    UnknownPreconditionError,
    build_preconditions,
    unmet_preconditions,
)
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState

MODEL = "crm.opportunity"


def _skill(preconditions: list[str]) -> SkillDefinition:
    return SkillDefinition(
        skill_id="crm.create_opportunity",
        version="1.0.0",
        module="crm",
        operation="create",
        description="Crea una oportunidad comercial.",
        risk_class=RiskClass.R1,
        input_schema={
            "type": "object",
            "required": ["customer_name", "expected_revenue"],
            "properties": {},
        },
        permissions=Permissions(allowed_roles=["erp_user"]),
        preconditions=preconditions,
        execution=Execution(
            handler="erp_agent_os.handlers.crm_create_opportunity",
            timeout_seconds=10,
            max_retries=1,
            idempotent=True,
        ),
        postconditions=["exactly_one_new_opportunity"],
        state=SkillState.ACTIVE,
    )


def _erp() -> FakeERPAdapter:
    return FakeERPAdapter(allowed_models={MODEL})


def test_non_empty_precondition_holds_and_fails():
    skill = _skill(["customer_name_not_empty"])
    erp = _erp()
    assert (
        unmet_preconditions(skill, "erp_user", MODEL, erp, {"customer_name": "Acme"})
        == []
    )
    assert unmet_preconditions(
        skill, "erp_user", MODEL, erp, {"customer_name": "  "}
    ) == ["customer_name_not_empty"]


def test_revenue_limit_is_role_scoped():
    skill = _skill(["expected_revenue_within_role_limit"])
    erp = _erp()
    args = {"expected_revenue": "80000"}
    # erp_user's ceiling is 50k, sales_manager's is 100k: same request,
    # different answer, which is the point of a role-scoped rule.
    assert unmet_preconditions(skill, "erp_user", MODEL, erp, args) == [
        "expected_revenue_within_role_limit"
    ]
    assert unmet_preconditions(skill, "sales_manager", MODEL, erp, args) == []


def test_revenue_limit_treats_malformed_input_as_unmet():
    skill = _skill(["expected_revenue_within_role_limit"])
    assert unmet_preconditions(
        skill, "erp_user", MODEL, _erp(), {"expected_revenue": "mucho"}
    ) == ["expected_revenue_within_role_limit"]


def test_no_equivalent_open_record_sees_real_erp_state():
    skill = _skill(["no_equivalent_open_opportunity"])
    erp = _erp()
    args = {"customer_name": "Acme"}

    # Nothing there yet: the precondition holds.
    assert unmet_preconditions(skill, "erp_user", MODEL, erp, args) == []

    # An OPEN opportunity for the same customer: it must not hold.
    erp.create(MODEL, {"customer_name": "Acme", "state": "open"})
    assert unmet_preconditions(skill, "erp_user", MODEL, erp, args) == [
        "no_equivalent_open_opportunity"
    ]


def test_a_closed_equivalent_does_not_block():
    skill = _skill(["no_equivalent_open_opportunity"])
    erp = _erp()
    erp.create(MODEL, {"customer_name": "Acme", "state": "won"})
    assert (
        unmet_preconditions(skill, "erp_user", MODEL, erp, {"customer_name": "Acme"})
        == []
    )


def test_unknown_precondition_raises_instead_of_passing_silently():
    # A precondition nobody implemented must not read as one that held.
    skill = _skill(["some_rule_nobody_wrote"])
    with pytest.raises(UnknownPreconditionError):
        build_preconditions(skill, "erp_user", MODEL)


def test_frozen_catalog_declares_no_preconditions_yet():
    # Documents the deliberate state, so switching them on is a visible
    # change rather than a silent one: turning preconditions on alters
    # System C's decisions and therefore needs its own experiment run
    # (the confirmatory result describes the system without them).
    assert all(not s.preconditions for s in CATALOG_BY_ID.values())
