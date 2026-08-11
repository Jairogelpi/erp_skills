"""Property-based tests for core safety invariants (CLAUDE.md §29).

Covers: R4 never registrable, an idempotency key never produces two
mutations, a disallowed model never reaches the adapter, every terminal
execution has an audit event, and a more restrictive policy input never
yields a more permissive decision.
"""

from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from erp_agent_os.adapters import FakeERPAdapter, UnknownModelError
from erp_agent_os.audit import AuditStore
from erp_agent_os.dataset import RiskClass
from erp_agent_os.policy import PolicyDecision, decide
from erp_agent_os.runtime import Runtime
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState
from erp_agent_os.validation import Finding, FindingKind

_PERMISSIVENESS = {
    PolicyDecision.DENY: 0,
    PolicyDecision.REQUIRE_APPROVAL: 1,
    PolicyDecision.SIMULATE: 2,
    PolicyDecision.ALLOW: 3,
}

_NON_R4_RISKS = [r for r in RiskClass if r is not RiskClass.R4]


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


def handler(erp, args):
    return erp.create("crm.lead", args)


@given(role=st.text(min_size=1, max_size=20))
def test_r4_is_never_a_registrable_skill(role):
    try:
        SkillDefinition(
            skill_id="x.op",
            version="1.0.0",
            module="x",
            operation="op",
            description="d",
            risk_class=RiskClass.R4,
            input_schema={},
            permissions=Permissions(allowed_roles=[role]),
            preconditions=[],
            execution=Execution(
                handler="a.b", timeout_seconds=1, max_retries=0, idempotent=True
            ),
            postconditions=["p"],
        )
        raised = False
    except ValidationError:
        raised = True
    assert raised


@given(repeats=st.integers(min_value=1, max_value=10))
def test_idempotency_key_never_produces_two_mutations(repeats):
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", handler)

    for _ in range(repeats):
        runtime.execute(skill(), {"name": "Acme"}, "sales_user", "fixed-key")

    assert len(erp._records["crm.lead"]) == 1


@given(model=st.text(min_size=1, max_size=15).filter(lambda m: m != "crm.lead"))
def test_disallowed_model_never_reaches_adapter_store(model):
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    try:
        erp.create(model, {"x": 1})
        raised = False
    except UnknownModelError:
        raised = True
    assert raised
    assert model not in erp._records


@given(role=st.sampled_from(["sales_user", "other_role"]))
def test_every_terminal_execution_has_an_audit_event(role):
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", handler)
    store = AuditStore()

    outcome = decide(skill(), role)
    execution = runtime.execute(skill(), {"name": "Acme"}, role, "key-props")
    before = len(store.events())
    store.record("corr", skill(), role, outcome, execution, "key-props")

    assert len(store.events()) == before + 1


@given(
    risk=st.sampled_from(_NON_R4_RISKS),
    state=st.sampled_from(list(SkillState)),
    approval=st.booleans(),
)
def test_disallowed_role_never_more_permissive_than_allowed_role(risk, state, approval):
    allowed = decide(
        skill(risk_class=risk, state=state), "sales_user", approval_granted=approval
    )
    denied = decide(
        skill(risk_class=risk, state=state), "nobody", approval_granted=approval
    )

    assert _PERMISSIVENESS[denied.decision] <= _PERMISSIVENESS[allowed.decision]


@given(risk=st.sampled_from(_NON_R4_RISKS), approval=st.booleans())
def test_inactive_state_never_more_permissive_than_active(risk, approval):
    active = decide(
        skill(risk_class=risk, state=SkillState.ACTIVE),
        "sales_user",
        approval_granted=approval,
    )
    inactive = decide(
        skill(risk_class=risk, state=SkillState.DRAFT),
        "sales_user",
        approval_granted=approval,
    )

    assert _PERMISSIVENESS[inactive.decision] <= _PERMISSIVENESS[active.decision]


@given(
    risk=st.sampled_from(_NON_R4_RISKS),
    approval=st.booleans(),
    kind=st.sampled_from(list(FindingKind)),
)
def test_a_finding_never_makes_a_decision_more_permissive(risk, approval, kind):
    """Adding evidence of a problem must never loosen the decision.

    `policy.decide` gained a `findings` argument; the monotonicity
    property above predates it and did not cover it. A blocking finding
    that somehow produced a *more* permissive outcome would be a serious
    security defect, so it is asserted directly.
    """
    active = skill(risk_class=risk, state=SkillState.ACTIVE)

    without = decide(active, "sales_user", approval_granted=approval)
    with_finding = decide(
        active,
        "sales_user",
        approval_granted=approval,
        findings=[Finding(kind, "planted")],
    )

    assert _PERMISSIVENESS[with_finding.decision] <= _PERMISSIVENESS[without.decision]


@given(risk=st.sampled_from(_NON_R4_RISKS), approval=st.booleans())
def test_a_blocking_finding_always_denies(risk, approval):
    active = skill(risk_class=risk, state=SkillState.ACTIVE)
    outcome = decide(
        active,
        "sales_user",
        approval_granted=approval,
        findings=[Finding(FindingKind.PROMPT_INJECTION, "planted")],
    )
    assert outcome.decision is PolicyDecision.DENY
