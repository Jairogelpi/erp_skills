from erp_agent_os.llm_client import DeterministicStubClient, ToolSpec

TOOLS = [
    ToolSpec("create_opportunity", "crea una oportunidad comercial", ["customer_name"]),
    ToolSpec("create_task", "crea una tarea interna de seguimiento", ["title"]),
]


def test_picks_tool_with_highest_keyword_overlap():
    client = DeterministicStubClient()
    call = client.propose_action("crea una oportunidad comercial para Acme", TOOLS)
    assert call.tool_name == "create_opportunity"


def test_no_overlap_declines():
    client = DeterministicStubClient()
    call = client.propose_action("xyz completely unrelated", TOOLS)
    assert call.tool_name is None
