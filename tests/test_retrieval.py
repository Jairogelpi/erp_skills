from erp_agent_os.dataset import RiskClass
from erp_agent_os.retrieval import (
    HybridRetriever,
    HybridWeights,
    TfidfRetriever,
    should_abstain,
)
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState


def make_skill(skill_id, description, roles, **changes):
    data = {
        "skill_id": skill_id,
        "version": "1.0.0",
        "module": "crm",
        "operation": "create",
        "description": description,
        "risk_class": RiskClass.R1,
        "input_schema": {"type": "object"},
        "permissions": Permissions(allowed_roles=roles),
        "preconditions": [],
        "execution": Execution(
            handler="a.b", timeout_seconds=10, max_retries=1, idempotent=True
        ),
        "postconditions": ["p"],
        "state": SkillState.ACTIVE,
    }
    data.update(changes)
    return SkillDefinition(**data)


CREATE_OPPORTUNITY = make_skill(
    "crm.create_opportunity",
    "Crea una oportunidad comercial en estado inicial.",
    ["sales_user"],
)
CREATE_TASK = make_skill(
    "task.create_task",
    "Crea una tarea interna de seguimiento.",
    ["sales_user", "ops_user"],
    module="task",
)


def test_query_ranks_closer_description_first():
    retriever = TfidfRetriever([CREATE_OPPORTUNITY, CREATE_TASK])
    ranked = retriever.rank("crear una oportunidad comercial para un cliente")
    assert ranked[0].skill.skill_id == "crm.create_opportunity"


def test_role_filter_excludes_unpermitted_skill():
    retriever = TfidfRetriever([CREATE_OPPORTUNITY, CREATE_TASK])
    ranked = retriever.rank("crear una tarea", role="ops_user")
    assert all(c.skill.skill_id != "crm.create_opportunity" for c in ranked)


def test_abstain_when_missing_fields_present():
    retriever = TfidfRetriever([CREATE_OPPORTUNITY])
    ranked = retriever.rank("crear una oportunidad comercial")
    assert should_abstain(ranked, missing_fields=["customer_name"]) is True


def test_abstain_when_top_score_below_threshold():
    retriever = TfidfRetriever([CREATE_OPPORTUNITY])
    ranked = retriever.rank("algo totalmente no relacionado xyz")
    assert should_abstain(ranked, missing_fields=[], threshold=0.9) is True


def test_no_abstain_when_confident_and_no_missing_fields():
    retriever = TfidfRetriever([CREATE_OPPORTUNITY, CREATE_TASK])
    ranked = retriever.rank("crear una oportunidad comercial")
    assert (
        should_abstain(ranked, missing_fields=[], threshold=0.05, margin=0.01) is False
    )


def test_hybrid_module_match_boosts_correct_skill_above_vector_tie():
    tied_vector = TfidfRetriever([CREATE_OPPORTUNITY, CREATE_TASK])
    hybrid = HybridRetriever(
        [CREATE_OPPORTUNITY, CREATE_TASK],
        tied_vector,
        weights=HybridWeights(
            vector_similarity=0.0, module_match=1.0, operation_match=0.0
        ),
    )
    ranked = hybrid.rank("crear algo", module="task")
    assert ranked[0].skill.skill_id == "task.create_task"


def test_hybrid_without_module_operation_falls_back_to_vector_only():
    vector = TfidfRetriever([CREATE_OPPORTUNITY, CREATE_TASK])
    hybrid = HybridRetriever([CREATE_OPPORTUNITY, CREATE_TASK], vector)
    ranked = hybrid.rank("crear una oportunidad comercial")
    assert ranked[0].skill.skill_id == "crm.create_opportunity"


def test_hybrid_respects_upstream_role_filter():
    vector = TfidfRetriever([CREATE_OPPORTUNITY, CREATE_TASK])
    hybrid = HybridRetriever([CREATE_OPPORTUNITY, CREATE_TASK], vector)
    ranked = hybrid.rank("crear una tarea", role="ops_user")
    assert all(c.skill.skill_id != "crm.create_opportunity" for c in ranked)
