import pytest
from sqlalchemy import create_engine

from erp_agent_os.registry import SqlSkillRegistry, create_registry_schema
from erp_agent_os.skill_proposal import (
    ProposalRejected,
    approve_and_activate,
    propose_skill,
    run_in_sandbox,
    validate_proposal,
)
from erp_agent_os.skills import SkillState

MODEL = "crm.opportunity"


@pytest.fixture
def registry():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_registry_schema(engine)
    return SqlSkillRegistry(engine)


def _payload(**overrides):
    payload = {
        "skill_id": "crm.follow_up_opportunity",
        "version": "1.0.0",
        "module": "crm",
        "operation": "create",
        "description": "Crea una oportunidad de seguimiento para un cliente.",
        "risk_class": "R1",
        "input_schema": {
            "type": "object",
            "required": ["customer_name"],
            "properties": {},
        },
        "permissions": {"allowed_roles": ["erp_user"]},
        "preconditions": [],
        "execution": {
            "handler": "erp_agent_os.handlers.crm_create_opportunity",
            "timeout_seconds": 10,
            "max_retries": 1,
            "idempotent": True,
        },
        "postconditions": ["exactly_one_new_opportunity"],
        "state": "DRAFT",
    }
    payload.update(overrides)
    return payload


def _handler(erp, args):
    return erp.create(MODEL, {"customer_name": args["customer_name"], "state": "open"})


def _broken_handler(erp, args):
    raise ValueError("this handler is wrong")


# --- validation --------------------------------------------------------


def test_a_valid_proposal_validates_as_draft():
    skill = validate_proposal(_payload())
    assert skill.state is SkillState.DRAFT


def test_a_proposal_claiming_to_be_active_is_rejected():
    # Otherwise a generated skill could declare itself production-ready.
    with pytest.raises(ProposalRejected, match="must enter as DRAFT"):
        validate_proposal(_payload(state="ACTIVE"))


def test_an_r4_proposal_is_rejected_by_the_schema():
    # §16: R4 is prohibited outright, so it cannot even be proposed.
    with pytest.raises(ProposalRejected):
        validate_proposal(_payload(risk_class="R4"))


def test_a_proposal_with_no_allowed_roles_is_rejected():
    with pytest.raises(ProposalRejected):
        validate_proposal(_payload(permissions={"allowed_roles": []}))


# --- sandbox -----------------------------------------------------------


def test_sandbox_passes_for_a_working_handler():
    skill = validate_proposal(_payload())
    result = run_in_sandbox(skill, _handler, {"customer_name": "Acme"}, MODEL)
    assert result.passed is True


def test_sandbox_fails_for_a_broken_handler_without_raising():
    skill = validate_proposal(_payload())
    result = run_in_sandbox(skill, _broken_handler, {"customer_name": "Acme"}, MODEL)
    assert result.passed is False
    assert "ValueError" in result.detail or "handler error" in result.detail


# --- the CU-02 flow ----------------------------------------------------


def test_a_proposal_stops_at_tested_and_never_self_activates(registry):
    # §15's central safety rule for generated skills: "Una skill nunca se
    # activará automáticamente tras su primera generación."
    skill = propose_skill(
        registry, _payload(), _handler, {"customer_name": "Acme"}, MODEL
    )
    assert registry.state_of(skill.skill_id, skill.version) is SkillState.TESTED
    assert skill.skill_id not in {s.skill_id for s in registry.active()}


def test_a_failed_sandbox_never_reaches_the_registry(registry):
    with pytest.raises(ProposalRejected, match="sandbox tests failed"):
        propose_skill(
            registry, _payload(), _broken_handler, {"customer_name": "Acme"}, MODEL
        )
    assert registry.versions("crm.follow_up_opportunity") == []


def test_human_approval_activates_and_is_attributable(registry):
    skill = propose_skill(
        registry, _payload(), _handler, {"customer_name": "Acme"}, MODEL
    )
    state = approve_and_activate(
        registry, skill.skill_id, skill.version, approver="jefa.de.ventas"
    )

    assert state is SkillState.ACTIVE
    history = registry.history(skill.skill_id, skill.version)
    assert [h["to_state"] for h in history] == [
        "DRAFT",
        "VALIDATED",
        "TESTED",
        "APPROVED",
        "ACTIVE",
    ]
    # "Who let this into production" must be answerable from history.
    assert history[-1]["actor"] == "jefa.de.ventas"


def test_activation_requires_a_named_approver(registry):
    skill = propose_skill(
        registry, _payload(), _handler, {"customer_name": "Acme"}, MODEL
    )
    with pytest.raises(ProposalRejected, match="named human approver"):
        approve_and_activate(registry, skill.skill_id, skill.version, approver="  ")
    assert registry.state_of(skill.skill_id, skill.version) is SkillState.TESTED
