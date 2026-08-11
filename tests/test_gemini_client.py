import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.genai import errors

from erp_agent_os.gemini_client import (
    GeminiClient,
    GeminiConfig,
    MissingApiKeyError,
    _parse_tool_call,
    _retry_delay,
)
from erp_agent_os.llm_client import ToolCall, ToolSpec

TOOLS = [
    ToolSpec("create_opportunity", "crea una oportunidad comercial", ["customer_name"]),
    ToolSpec("create_task", "crea una tarea interna", ["title"]),
]


def _fake_response(
    content: str, prompt_tokens: int = 42, completion_tokens: int = 7
) -> SimpleNamespace:
    return SimpleNamespace(
        text=content,
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt_tokens, candidates_token_count=completion_tokens
        ),
    )


def _fake_resource_exhausted(retry_hint: str = "Please retry in 7s.") -> Exception:
    return errors.ClientError(
        429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": retry_hint}}
    )


def test_missing_api_key_raises_not_falls_back(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        GeminiClient()


def test_config_defaults_are_low_temperature_and_registered():
    config = GeminiConfig()
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


# --- propose_action: mocked Gemini SDK, no real network call ---


def test_propose_action_returns_no_action_for_empty_tool_list(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = GeminiClient()
    assert client.propose_action("cualquier cosa", []) == ToolCall(None, {})


def test_propose_action_parses_a_successful_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = GeminiClient()
    client._client.models.generate_content = MagicMock(
        return_value=_fake_response(
            json.dumps({"tool_name": "create_task", "arguments": {"title": "llamar"}})
        )
    )

    call = client.propose_action("crea una tarea para llamar", TOOLS)

    assert call == ToolCall("create_task", {"title": "llamar"}, 42, 7)
    client._client.models.generate_content.assert_called_once()
    kwargs = client._client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == client.config.model
    assert kwargs["config"].temperature == 0.0


def test_propose_action_retries_transient_failures_then_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("erp_agent_os.gemini_client.time.sleep", lambda _s: None)
    client = GeminiClient(GeminiConfig(max_retries=3))

    calls = {"n": 0}

    def flaky(**_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return _fake_response(json.dumps({"tool_name": None, "arguments": {}}))

    client._client.models.generate_content = MagicMock(side_effect=flaky)

    result = client.propose_action("algo", TOOLS)

    assert result == ToolCall(None, {}, 42, 7)
    assert calls["n"] == 3


def test_propose_action_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("erp_agent_os.gemini_client.time.sleep", lambda _s: None)
    client = GeminiClient(GeminiConfig(max_retries=2))
    client._client.models.generate_content = MagicMock(
        side_effect=ConnectionError("always fails")
    )

    with pytest.raises(RuntimeError, match="failed after 2 attempts"):
        client.propose_action("algo", TOOLS)

    assert client._client.models.generate_content.call_count == 2


def test_pace_sleeps_to_respect_min_interval(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = GeminiClient(GeminiConfig(min_interval_seconds=5.0))

    clock = {"t": 0.0}
    monkeypatch.setattr("erp_agent_os.gemini_client.time.monotonic", lambda: clock["t"])
    sleeps = []
    monkeypatch.setattr(
        "erp_agent_os.gemini_client.time.sleep", lambda s: sleeps.append(s)
    )

    client._pace()
    clock["t"] = 1.0
    client._pace()

    assert sleeps == [4.0]


def test_retry_delay_honors_the_retry_hint_in_the_error_message():
    exc = _fake_resource_exhausted("Please retry in 7.2s.")
    assert _retry_delay(exc, attempt=0) == pytest.approx(7.7)


def test_retry_delay_falls_back_to_exponential_backoff_without_hint():
    exc = _fake_resource_exhausted("no hint here")
    assert _retry_delay(exc, attempt=2) == 4.0


def test_retry_delay_falls_back_for_non_quota_errors():
    assert _retry_delay(ConnectionError("boom"), attempt=1) == 2.0
