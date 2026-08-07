from erp_agent_os.llm_client import (
    CachingLLMClient,
    DeterministicStubClient,
    ToolCall,
    ToolSpec,
)

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


class _CountingLLM:
    def __init__(self, call: ToolCall) -> None:
        self.calls = 0
        self._call = call

    def propose_action(self, query_text, tools):
        self.calls += 1
        return self._call


def test_caching_client_calls_the_real_client_only_once_per_unique_query():
    inner = _CountingLLM(ToolCall("create_task", {}, 100, 20))
    client = CachingLLMClient(inner)

    first = client.propose_action("crea una tarea", TOOLS)
    second = client.propose_action("crea una tarea", TOOLS)
    third = client.propose_action("crea una tarea", TOOLS)

    assert inner.calls == 1
    assert (first.prompt_tokens, first.completion_tokens) == (100, 20)
    # Cached hits report no cost: no real second/third call was made.
    assert (second.prompt_tokens, second.completion_tokens) == (0, 0)
    assert (third.prompt_tokens, third.completion_tokens) == (0, 0)
    assert second.tool_name == third.tool_name == "create_task"


def test_caching_client_keys_on_query_text_and_tool_names():
    inner = _CountingLLM(ToolCall("create_task", {}))
    client = CachingLLMClient(inner)

    client.propose_action("crea una tarea", TOOLS)
    client.propose_action("crea otra cosa", TOOLS)

    assert inner.calls == 2
