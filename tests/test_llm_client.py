from erp_agent_os.llm_client import (
    ArgumentExtraction,
    CachingLLMClient,
    DeterministicStubClient,
    ToolCall,
    ToolSpec,
    build_extraction_prompt,
    parse_extraction,
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
        self.extractions = 0
        self._call = call

    def propose_action(self, query_text, tools):
        self.calls += 1
        return self._call

    def extract_arguments(self, query_text, fields):
        self.extractions += 1
        return ArgumentExtraction(dict.fromkeys(fields, "x"), 50, 10)


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


def test_caching_client_also_caches_argument_extraction():
    # Repetitions of a case re-ask the identical extraction; paying for
    # it three times would overcount H2 spend the same way tool
    # selection would.
    inner = _CountingLLM(ToolCall("create_task", {}))
    client = CachingLLMClient(inner)

    first = client.extract_arguments("crea una tarea", ["title"])
    second = client.extract_arguments("crea una tarea", ["title"])

    assert inner.extractions == 1
    assert (first.prompt_tokens, first.completion_tokens) == (50, 10)
    assert (second.prompt_tokens, second.completion_tokens) == (0, 0)
    assert second.arguments == {"title": "x"}


def test_stub_extracts_nothing_because_it_is_not_a_language_model():
    result = DeterministicStubClient().extract_arguments("crea una tarea", ["title"])
    assert result.arguments == {}
    assert (result.prompt_tokens, result.completion_tokens) == (0, 0)


def test_parse_extraction_keeps_only_requested_non_empty_fields():
    content = '{"customer_name": "Acme", "expected_revenue": 15000, "injected": "x"}'
    parsed = parse_extraction(content, ["customer_name", "expected_revenue"])
    # `injected` was never requested: an extractor that volunteers extra
    # fields must not be able to widen what a skill gets validated against.
    assert parsed == {"customer_name": "Acme", "expected_revenue": 15000}


def test_parse_extraction_drops_empty_and_null_values():
    content = '{"customer_name": "", "expected_revenue": null, "title": "  "}'
    assert (
        parse_extraction(content, ["customer_name", "expected_revenue", "title"]) == {}
    )


def test_parse_extraction_degrades_to_empty_on_malformed_json():
    assert parse_extraction("not json", ["customer_name"]) == {}
    assert parse_extraction('["a", "list"]', ["customer_name"]) == {}


def test_extraction_prompt_names_every_requested_field():
    prompt = build_extraction_prompt("crea algo", ["customer_name", "expected_revenue"])
    assert "customer_name" in prompt
    assert "expected_revenue" in prompt
    assert "crea algo" in prompt
