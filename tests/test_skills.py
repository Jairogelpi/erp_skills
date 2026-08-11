import pytest
from pydantic import ValidationError

from erp_agent_os.dataset import RiskClass
from erp_agent_os.skills import (
    Execution,
    InvalidTransitionError,
    Permissions,
    SkillDefinition,
    SkillState,
    transition,
)


def skill(**changes):
    data = {
        "skill_id": "crm.create_opportunity",
        "version": "1.2.0",
        "module": "crm",
        "operation": "create",
        "description": "Crea una oportunidad comercial en estado inicial.",
        "risk_class": RiskClass.R1,
        "input_schema": {"type": "object"},
        "permissions": Permissions(allowed_roles=["sales_user"]),
        "preconditions": ["customer_name_not_empty"],
        "execution": Execution(
            handler="erp_agent_os.skills.crm.create_opportunity",
            timeout_seconds=10,
            max_retries=1,
            idempotent=True,
        ),
        "postconditions": ["exactly_one_new_opportunity"],
    }
    data.update(changes)
    return data


def test_valid_skill_defaults_to_draft():
    assert SkillDefinition(**skill()).state == SkillState.DRAFT


def test_draft_to_active_direct_jump_rejected():
    with pytest.raises(InvalidTransitionError):
        transition(SkillState.DRAFT, SkillState.ACTIVE)


def test_any_state_can_quarantine():
    for state in SkillState:
        if state is SkillState.QUARANTINED:
            continue
        assert transition(state, SkillState.QUARANTINED) == SkillState.QUARANTINED


def test_full_lifecycle_path_accepted():
    path = [
        SkillState.DRAFT,
        SkillState.VALIDATED,
        SkillState.TESTED,
        SkillState.APPROVED,
        SkillState.ACTIVE,
        SkillState.DEPRECATED,
    ]
    for current, target in zip(path, path[1:]):
        assert transition(current, target) == target


@pytest.mark.parametrize(
    "changes",
    [
        {"risk_class": RiskClass.R4},
        {"postconditions": []},
        {"version": "1.2"},
    ],
)
def test_rejects_prohibited_risk_missing_postconditions_and_bad_version(changes):
    with pytest.raises(ValidationError):
        SkillDefinition(**skill(**changes))
