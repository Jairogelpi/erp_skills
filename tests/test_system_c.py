from datetime import UTC, datetime

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditStore
from erp_agent_os.dataset import RiskClass
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState
from erp_agent_os.system_c import SystemC


def make_skill(**changes):
    data = {
        "skill_id": "crm.create_opportunity",
        "version": "1.0.0",
        "module": "crm",
        "operation": "create",
        "description": "Crea una oportunidad comercial en estado inicial.",
        "risk_class": RiskClass.R1,
        "input_schema": {"type": "object"},
        "permissions": Permissions(allowed_roles=["sales_user"]),
        "preconditions": [],
        "execution": Execution(
            handler="a.b", timeout_seconds=10, max_retries=1, idempotent=True
        ),
        "postconditions": ["exactly_one_new_opportunity"],
        "state": SkillState.ACTIVE,
    }
    data.update(changes)
    return SkillDefinition(**data)


def handler(erp, args):
    return erp.create("crm.lead", args)


def build_system(skill):
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register(skill.skill_id, skill.version, handler)
    retriever = TfidfRetriever([skill])
    audit = AuditStore()
    return erp, SystemC(erp, runtime, retriever, audit), audit


def test_full_allow_path_mutates_erp_and_audits():
    skill = make_skill()
    erp, system, audit = build_system(skill)
    proposal = structure_proposal(
        skill.skill_id, {"name": "Acme"}, ["name"], confidence=0.9
    )

    result = system.handle(
        "corr-1", "crear una oportunidad comercial", proposal, "sales_user", "key-1"
    )

    assert result.decision == "ALLOW"
    assert erp.get("crm.lead", result.execution.output) == {"name": "Acme"}
    assert len(audit.events("corr-1")) == 1


def test_missing_field_clarifies_without_touching_erp():
    skill = make_skill()
    erp, system, audit = build_system(skill)
    proposal = structure_proposal(skill.skill_id, {}, ["name"], confidence=0.9)

    result = system.handle(
        "corr-2", "crear una oportunidad comercial", proposal, "sales_user", "key-1"
    )

    # Missing required data asks for clarification; abstention is reserved
    # for "no candidate is trustworthy enough".
    assert result.decision == "CLARIFY"
    assert erp._records["crm.lead"] == {}
    assert len(audit.abstentions("corr-2")) == 1
    assert len(audit.events("corr-2")) == 0


def test_no_confident_candidate_abstains():
    skill = make_skill()
    erp, system, audit = build_system(skill)
    proposal = structure_proposal(
        skill.skill_id, {"name": "Acme"}, ["name"], confidence=0.9
    )

    result = system.handle(
        "corr-3", "algo totalmente no relacionado xyz", proposal, "sales_user", "key-1"
    )

    assert result.decision == "ABSTAIN"
    assert len(audit.abstentions("corr-3")) == 1


def test_abstain_gate_is_injectable_for_the_v21_no_abstention_ablation():
    """docs/tfm-closure-no-human-v2.1.md section 6.1/8: C_NO_ABSTENTION
    must differ from C in exactly one way. Injecting a permissive
    `abstain` callable is that one difference -- everything else
    (parser, retriever, candidates, policy, runtime, state) is the same
    constructor call with the same skill/erp/runtime/retriever/audit."""
    skill = make_skill()
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register(skill.skill_id, skill.version, handler)
    retriever = TfidfRetriever([skill])
    audit = AuditStore()
    proposal = structure_proposal(
        skill.skill_id, {"name": "Acme"}, ["name"], confidence=0.9
    )
    query = "algo totalmente no relacionado xyz"

    governed = SystemC(erp, runtime, retriever, audit)
    governed_result = governed.handle("corr-4", query, proposal, "sales_user", "key-1")
    assert governed_result.decision == "ABSTAIN"

    ungated = SystemC(
        erp,
        runtime,
        retriever,
        audit,
        abstain=lambda ranked, missing: bool(missing) or not ranked,
    )
    ungated_result = ungated.handle("corr-5", query, proposal, "sales_user", "key-2")
    assert ungated_result.decision == "ALLOW"


def test_inactive_skill_denies_but_still_audits():
    skill = make_skill(state=SkillState.DRAFT)
    erp, system, audit = build_system(skill)
    proposal = structure_proposal(
        skill.skill_id, {"name": "Acme"}, ["name"], confidence=0.9
    )

    result = system.handle(
        "corr-4", "crear una oportunidad comercial", proposal, "sales_user", "key-1"
    )

    assert result.decision == "DENY"
    assert erp._records["crm.lead"] == {}
    assert len(audit.events("corr-4")) == 1


def test_repeated_idempotency_key_single_mutation():
    skill = make_skill()
    erp, system, _audit = build_system(skill)
    proposal = structure_proposal(
        skill.skill_id, {"name": "Acme"}, ["name"], confidence=0.9
    )

    system.handle(
        "corr-5", "crear una oportunidad comercial", proposal, "sales_user", "same-key"
    )
    system.handle(
        "corr-6", "crear una oportunidad comercial", proposal, "sales_user", "same-key"
    )

    assert len(erp._records["crm.lead"]) == 1


def test_approval_grants_allow_for_r2_skill():
    skill = make_skill(risk_class=RiskClass.R2)
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register(skill.skill_id, skill.version, handler)
    retriever = TfidfRetriever([skill])
    audit = AuditStore()
    approval = ApprovalService(clock=lambda: datetime(2026, 8, 5, tzinfo=UTC))
    approval.grant("manager1", skill.skill_id, ttl_seconds=60)
    system = SystemC(erp, runtime, retriever, audit, approval)
    proposal = structure_proposal(
        skill.skill_id, {"name": "Acme"}, ["name"], confidence=0.9
    )

    result = system.handle(
        "corr-7", "crear una oportunidad comercial", proposal, "sales_user", "key-1"
    )

    assert result.decision == "ALLOW"
