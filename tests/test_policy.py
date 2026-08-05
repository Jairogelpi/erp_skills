from erp_agent_os.dataset import RiskClass
from erp_agent_os.policy import PolicyDecision, decide
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState


def skill(**changes):
    data = {
        "skill_id": "crm.create_opportunity",
        "version": "1.0.0",
        "module": "crm",
        "operation": "create",
        "description": "Crea una oportunidad.",
        "risk_class": RiskClass.R1,
        "input_schema": {"type": "object"},
        "permissions": Permissions(allowed_roles=["sales_user"]),
        "preconditions": [],
        "execution": Execution(
            handler="erp_agent_os.skills.crm.create_opportunity",
            timeout_seconds=10,
            max_retries=1,
            idempotent=True,
        ),
        "postconditions": ["exactly_one_new_opportunity"],
        "state": SkillState.ACTIVE,
    }
    data.update(changes)
    return SkillDefinition(**data)


def test_allowed_role_low_risk_active_skill_allows():
    assert decide(skill(), "sales_user").decision == PolicyDecision.ALLOW


def test_disallowed_role_denies():
    assert decide(skill(), "warehouse_user").decision == PolicyDecision.DENY


def test_inactive_skill_denies_even_for_allowed_role():
    assert (
        decide(skill(state=SkillState.APPROVED), "sales_user").decision
        == PolicyDecision.DENY
    )


def test_r2_requires_approval_then_allows():
    r2 = skill(risk_class=RiskClass.R2)
    assert decide(r2, "sales_user").decision == PolicyDecision.REQUIRE_APPROVAL
    assert (
        decide(r2, "sales_user", approval_granted=True).decision == PolicyDecision.ALLOW
    )


def test_r3_requires_approval_then_simulates_not_allows():
    r3 = skill(risk_class=RiskClass.R3)
    assert decide(r3, "sales_user").decision == PolicyDecision.REQUIRE_APPROVAL
    assert (
        decide(r3, "sales_user", approval_granted=True).decision
        == PolicyDecision.SIMULATE
    )
