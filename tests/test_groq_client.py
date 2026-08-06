import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from erp_agent_os.groq_client import (
    GroqClient,
    GroqConfig,
    MissingApiKeyError,
    _parse_tool_call,
)
from erp_agent_os.llm_client import ToolCall, ToolSpec

TOOLS = [
    ToolSpec("create_opportunity", "crea una oportunidad comercial", ["customer_name"]),
    ToolSpec("create_task", "crea una tarea interna", ["title"]),
]


def _fake_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_missing_api_key_raises_not_falls_back(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        GroqClient()


def test_config_defaults_are_low_temperature_and_registered():
    config = GroqConfig()
    assert config.temperature == 0.0
    assert config.model
    assert config.max_retries >= 1


# --- _parse_tool_call: pure function, no network needed ---


def test_parse_tool_call_valid_json():
    content = json.dumps({"tool_name": "create_task", "arguments": {"title": "llamar"}})
    call = _parse_tool_call(content, TOOLS)
    assert call == ToolCall("create_task", {"title": "llamar"})


def test_parse_tool_call_rejects_hallucinated_tool_name():
    # A tool name the model invented, not in the offered list, must not
    # be trusted -- CLAUDE.md section 23: no execution from free text.
    content = json.dumps({"tool_name": "delete_everything", "arguments": {}})
    assert _parse_tool_call(content, TOOLS) == ToolCall(None, {})


def test_parse_tool_call_malformed_json_degrades_to_no_action():
    assert _parse_tool_call("not json at all", TOOLS) == ToolCall(None, {})


def test_parse_tool_call_missing_arguments_defaults_to_empty_dict():
    content = json.dumps({"tool_name": "create_task"})
    assert _parse_tool_call(content, TOOLS) == ToolCall("create_task", {})


def test_parse_tool_call_null_tool_name_is_no_action():
    content = json.dumps({"tool_name": None, "arguments": {}})
    assert _parse_tool_call(content, TOOLS) == ToolCall(None, {})


# --- propose_action: mocked Groq SDK, no real network call ---


def test_propose_action_returns_no_action_for_empty_tool_list(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    client = GroqClient()
    assert client.propose_action("cualquier cosa", []) == ToolCall(None, {})


def test_propose_action_parses_a_successful_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    client = GroqClient()
    client._client.chat.completions.create = MagicMock(
        return_value=_fake_response(
            json.dumps({"tool_name": "create_task", "arguments": {"title": "llamar"}})
        )
    )

    call = client.propose_action("crea una tarea para llamar", TOOLS)

    assert call == ToolCall("create_task", {"title": "llamar"})
    client._client.chat.completions.create.assert_called_once()
    kwargs = client._client.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.0
    assert kwargs["model"] == client.config.model


def test_propose_action_retries_transient_failures_then_succeeds(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr("erp_agent_os.groq_client.time.sleep", lambda _seconds: None)
    client = GroqClient(GroqConfig(max_retries=3))

    calls = {"n": 0}

    def flaky(**_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return _fake_response(json.dumps({"tool_name": None, "arguments": {}}))

    client._client.chat.completions.create = MagicMock(side_effect=flaky)

    result = client.propose_action("algo", TOOLS)

    assert result == ToolCall(None, {})
    assert calls["n"] == 3


def test_propose_action_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr("erp_agent_os.groq_client.time.sleep", lambda _seconds: None)
    client = GroqClient(GroqConfig(max_retries=2))
    client._client.chat.completions.create = MagicMock(
        side_effect=ConnectionError("always fails")
    )

    with pytest.raises(RuntimeError, match="failed after 2 attempts"):
        client.propose_action("algo", TOOLS)

    assert client._client.chat.completions.create.call_count == 2
