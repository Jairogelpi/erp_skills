from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.handlers import SKILL_MODELS
from erp_agent_os.llm_client import ToolCall
from erp_agent_os.system_b import SystemB


class _StubLLM:
    def __init__(self, call: ToolCall) -> None:
        self._call = call

    def propose_action(self, query_text, tools):
        return self._call


def test_typed_tool_executes_when_arguments_complete():
    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    system = SystemB(erp, _StubLLM(ToolCall("crm.create_opportunity", {})))

    result = system.handle(
        "crea una oportunidad para Acme",
        {"customer_name": "Acme", "expected_revenue": "1000"},
    )

    assert result.error is None
    assert result.skill_id == "crm.create_opportunity"


def test_missing_required_field_rejected_without_approval_or_retrieval():
    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    system = SystemB(erp, _StubLLM(ToolCall("crm.create_opportunity", {})))

    result = system.handle("crea una oportunidad", {"customer_name": "Acme"})

    assert result.error is not None
    assert "expected_revenue" in result.error


def test_no_matching_tool_returns_error_not_exception():
    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    system = SystemB(erp, _StubLLM(ToolCall(None, {})))

    result = system.handle("algo fuera de catalogo", {})

    assert result.skill_id is None
    assert result.error is not None


def test_no_risk_tiering_high_risk_skill_still_executes_directly():
    # System B has no policy engine: an R2 skill (crm.update_expected_revenue)
    # executes immediately given complete arguments, unlike System C which
    # would require approval first. This is the documented governance gap.
    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    erp.create("crm.opportunity", {"seeded": True}, record_id="OPP-1")
    system = SystemB(erp, _StubLLM(ToolCall("crm.update_expected_revenue", {})))

    result = system.handle(
        "actualiza el importe", {"opportunity_id": "OPP-1", "expected_revenue": "99999"}
    )

    assert result.error is None
    assert erp.get("crm.opportunity", "OPP-1")["expected_revenue"] == "99999"
