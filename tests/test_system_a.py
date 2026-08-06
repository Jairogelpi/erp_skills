from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.llm_client import ToolCall
from erp_agent_os.system_a import SystemA


class _StubLLM:
    def __init__(self, call: ToolCall) -> None:
        self._call = call

    def propose_action(self, query_text, tools):
        return self._call


def test_create_record_executes_directly_no_governance():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    system = SystemA(erp, _StubLLM(ToolCall("create_record", {})))

    result = system.handle(
        "crea un lead", {"model": "crm.lead", "fields": {"name": "Acme"}}
    )

    assert result.error is None
    assert erp.get("crm.lead", result.output) == {"name": "Acme"}


def test_no_tool_selected_returns_error_not_exception():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    system = SystemA(erp, _StubLLM(ToolCall(None, {})))

    result = system.handle("algo irrelevante", {})

    assert result.tool_name is None
    assert result.error is not None


def test_disallowed_model_surfaces_error_not_exception():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    system = SystemA(erp, _StubLLM(ToolCall("create_record", {})))

    result = system.handle(
        "crea algo fuera de alcance", {"model": "res.partner", "fields": {}}
    )

    assert result.error is not None


def test_token_usage_from_the_llm_call_is_carried_onto_the_result():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    system = SystemA(erp, _StubLLM(ToolCall("create_record", {}, 100, 20)))

    result = system.handle(
        "crea un lead", {"model": "crm.lead", "fields": {"name": "Acme"}}
    )

    assert (result.prompt_tokens, result.completion_tokens) == (100, 20)
