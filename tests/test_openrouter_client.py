import json
from unittest.mock import MagicMock

import httpx
import pytest

from erp_agent_os.llm_client import ToolCall, ToolSpec
from erp_agent_os.openrouter_client import (
    MissingApiKeyError,
    OpenRouterClient,
    OpenRouterConfig,
    _parse_tool_call,
    _retry_delay,
)

TOOLS = [
    ToolSpec("create_opportunity", "crea una oportunidad comercial", ["customer_name"]),
    ToolSpec("create_task", "crea una tarea interna", ["title"]),
]

URL = "https://openrouter.ai/api/v1/chat/completions"


def _fake_response(
    content: str, prompt_tokens: int = 42, completion_tokens: int = 7
) -> httpx.Response:
    body = {
        "choices": [{"message": {"content": content}}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }
    return httpx.Response(200, json=body, request=httpx.Request("POST", URL))


def test_missing_api_key_raises_not_falls_back(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        OpenRouterClient()


def test_config_defaults_are_low_temperature_and_registered():
    config = OpenRouterConfig()
    assert config.temperature == 0.0
    assert config.model
    assert config.max_retries >= 1


# --- _parse_tool_call: pure function, no network needed ---


def test_parse_tool_call_valid_json():
    content = json.dumps({"tool_name": "create_task", "arguments": {"title": "llamar"}})
    assert _parse_tool_call(content, TOOLS) == ToolCall(
        "create_task", {"title": "llamar"}
    )


def test_parse_tool_call_rejects_hallucinated_tool_name():
    content = json.dumps({"tool_name": "delete_everything", "arguments": {}})
    assert _parse_tool_call(content, TOOLS) == ToolCall(None, {})


def test_parse_tool_call_malformed_json_degrades_to_no_action():
    assert _parse_tool_call("not json at all", TOOLS) == ToolCall(None, {})


# --- propose_action: mocked httpx.Client.post, no real network call ---


def test_propose_action_returns_no_action_for_empty_tool_list(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = OpenRouterClient()
    assert client.propose_action("cualquier cosa", []) == ToolCall(None, {})


def test_propose_action_parses_a_successful_response(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = OpenRouterClient()
    client._client.post = MagicMock(
        return_value=_fake_response(
            json.dumps({"tool_name": "create_task", "arguments": {"title": "llamar"}})
        )
    )

    call = client.propose_action("crea una tarea para llamar", TOOLS)

    assert call == ToolCall("create_task", {"title": "llamar"}, 42, 7)
    client._client.post.assert_called_once()
    kwargs = client._client.post.call_args.kwargs
    assert kwargs["json"]["temperature"] == 0.0
    assert kwargs["json"]["model"] == client.config.model


def test_propose_action_retries_transient_failures_then_succeeds(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("erp_agent_os.openrouter_client.time.sleep", lambda _s: None)
    client = OpenRouterClient(OpenRouterConfig(max_retries=3))

    calls = {"n": 0}

    def flaky(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return _fake_response(json.dumps({"tool_name": None, "arguments": {}}))

    client._client.post = MagicMock(side_effect=flaky)

    result = client.propose_action("algo", TOOLS)

    assert result == ToolCall(None, {}, 42, 7)
    assert calls["n"] == 3


def test_propose_action_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("erp_agent_os.openrouter_client.time.sleep", lambda _s: None)
    client = OpenRouterClient(OpenRouterConfig(max_retries=2))
    client._client.post = MagicMock(side_effect=ConnectionError("always fails"))

    with pytest.raises(RuntimeError, match="failed after 2 attempts"):
        client.propose_action("algo", TOOLS)

    assert client._client.post.call_count == 2


def test_http_error_status_raises_and_is_retried(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("erp_agent_os.openrouter_client.time.sleep", lambda _s: None)
    client = OpenRouterClient(OpenRouterConfig(max_retries=2))
    client._client.post = MagicMock(
        return_value=httpx.Response(500, request=httpx.Request("POST", URL))
    )

    with pytest.raises(RuntimeError, match="failed after 2 attempts"):
        client.propose_action("algo", TOOLS)


def test_pace_sleeps_to_respect_min_interval(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = OpenRouterClient(OpenRouterConfig(min_interval_seconds=5.0))

    clock = {"t": 0.0}
    monkeypatch.setattr(
        "erp_agent_os.openrouter_client.time.monotonic", lambda: clock["t"]
    )
    sleeps = []
    monkeypatch.setattr(
        "erp_agent_os.openrouter_client.time.sleep", lambda s: sleeps.append(s)
    )

    client._pace()
    clock["t"] = 1.0
    client._pace()

    assert sleeps == [4.0]


def _fake_429(
    headers: dict[str, str] | None = None, text: str = ""
) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", URL)
    response = httpx.Response(429, headers=headers or {}, text=text, request=request)
    return httpx.HTTPStatusError("rate limited", request=request, response=response)


def test_retry_delay_honors_retry_after_header():
    exc = _fake_429({"retry-after": "7"})
    assert _retry_delay(exc, attempt=0) == 7.5


def test_retry_delay_falls_back_to_exponential_backoff_without_hint():
    exc = _fake_429({})
    assert _retry_delay(exc, attempt=2) == 4.0


def test_retry_delay_falls_back_for_non_rate_limit_errors():
    assert _retry_delay(ConnectionError("boom"), attempt=1) == 2.0
