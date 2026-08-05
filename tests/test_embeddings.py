"""Embeddings retriever tests using a deterministic stub embedder.

No network/model download here — the stub hashes tokens into a small
bag-of-words vector so ranking behavior is testable without
sentence-transformers actually loading a model. A real-model smoke check
is documented separately (README/roadmap), not part of the pytest suite.
"""

from erp_agent_os.dataset import RiskClass
from erp_agent_os.embeddings import EmbeddingRetriever
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState

_VOCAB = ["oportunidad", "comercial", "tarea", "interna", "seguimiento", "cliente"]


def stub_embed(texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        lowered = text.lower()
        vector = [1.0 if term in lowered else 0.0 for term in _VOCAB]
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        vectors.append([v / norm for v in vector])
    return vectors


def make_skill(skill_id, description, roles):
    return SkillDefinition(
        skill_id=skill_id,
        version="1.0.0",
        module="crm",
        operation="create",
        description=description,
        risk_class=RiskClass.R1,
        input_schema={"type": "object"},
        permissions=Permissions(allowed_roles=roles),
        preconditions=[],
        execution=Execution(
            handler="a.b", timeout_seconds=10, max_retries=1, idempotent=True
        ),
        postconditions=["p"],
        state=SkillState.ACTIVE,
    )


CREATE_OPPORTUNITY = make_skill(
    "crm.create_opportunity", "Crea una oportunidad comercial", ["sales_user"]
)
CREATE_TASK = make_skill(
    "task.create_task",
    "Crea una tarea interna de seguimiento",
    ["sales_user", "ops_user"],
)


def test_closer_description_ranks_first():
    retriever = EmbeddingRetriever([CREATE_OPPORTUNITY, CREATE_TASK], embed=stub_embed)
    ranked = retriever.rank("quiero registrar una oportunidad comercial")
    assert ranked[0].skill.skill_id == "crm.create_opportunity"


def test_role_filter_excludes_unpermitted_skill():
    retriever = EmbeddingRetriever([CREATE_OPPORTUNITY, CREATE_TASK], embed=stub_embed)
    ranked = retriever.rank("crear una tarea interna", role="ops_user")
    assert all(c.skill.skill_id != "crm.create_opportunity" for c in ranked)


def test_injected_embedder_is_used_not_default_model():
    calls = []

    def counting_embed(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return stub_embed(texts)

    EmbeddingRetriever([CREATE_OPPORTUNITY], embed=counting_embed)
    assert len(calls) == 1
