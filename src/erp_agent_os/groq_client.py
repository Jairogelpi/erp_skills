"""Groq-backed LLMClient (CLAUDE.md §18, D-03).

The free-tier real provider used for the confirmatory A/B/C comparison.
CLAUDE.md does not mandate a specific commercial provider — D-03 only
requires that A, B, and C share "el mismo modelo, proveedor, versión/
configuración". A free model satisfies that as long as it is used
identically across all three systems and its limits are declared
honestly in the memoria (it is not a frontier/production-grade model).

The API key is read from the `GROQ_API_KEY` environment variable and is
never read from, or written to, any file this repository commits. If the
variable is absent, constructing this client raises immediately rather
than silently falling back to a stub — a confirmatory run must fail
loudly, not produce numbers from `DeterministicStubClient` by accident.
"""

import json
import os
import time
from dataclasses import dataclass

from groq import Groq

from erp_agent_os.llm_client import ToolCall, ToolSpec

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TEMPERATURE = 0.0  # low temperature: CLAUDE.md §23 ("temperatura baja")
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 30


class MissingApiKeyError(RuntimeError):
    """Raised when GROQ_API_KEY is not set. Never falls back silently."""


@dataclass(frozen=True)
class GroqConfig:
    """Registered, reproducible provider configuration (CLAUDE.md D-03)."""

    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


_SYSTEM_PROMPT = (
    "Eres un selector de herramientas para un ERP. Dada una peticion en "
    "espanol y una lista de herramientas disponibles, elige como maximo "
    "una herramienta y propone sus argumentos. Responde EXCLUSIVAMENTE "
    "con un objeto JSON de la forma "
    '{"tool_name": "<nombre o null>", "arguments": {}}. '
    "No inventes argumentos que no puedas inferir del texto: dejalos "
    "fuera del objeto si no hay evidencia textual clara. No ejecutes "
    "nada, no expliques tu razonamiento, no anadas texto fuera del JSON."
)


def _tool_menu(tools: list[ToolSpec]) -> str:
    lines = [
        f"- {t.name}: {t.description} (campos: {', '.join(t.required_arguments)})"
        for t in tools
    ]
    return "\n".join(lines)


class GroqClient:
    """Real LLMClient over the Groq API. See module docstring for scope."""

    def __init__(self, config: GroqConfig | None = None) -> None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise MissingApiKeyError(
                "GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com/keys and export it "
                "(e.g. in a local .env file, never committed) before "
                "constructing GroqClient."
            )
        self._config = config or GroqConfig()
        self._client = Groq(api_key=api_key, timeout=self._config.timeout_seconds)

    @property
    def config(self) -> GroqConfig:
        return self._config

    def propose_action(self, query_text: str, tools: list[ToolSpec]) -> ToolCall:
        if not tools:
            return ToolCall(None, {})

        user_prompt = (
            f"Peticion: {query_text}\n\nHerramientas disponibles:\n{_tool_menu(tools)}"
        )

        last_error: Exception | None = None
        for attempt in range(self._config.max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self._config.model,
                    temperature=self._config.temperature,
                    max_tokens=300,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = response.choices[0].message.content or "{}"
                return _parse_tool_call(content, tools)
            except Exception as exc:  # noqa: BLE001 - retry any transient failure
                last_error = exc
                if attempt < self._config.max_retries - 1:
                    time.sleep(2**attempt)  # exponential backoff

        raise RuntimeError(
            f"Groq call failed after {self._config.max_retries} attempts"
        ) from last_error


def _parse_tool_call(content: str, tools: list[ToolSpec]) -> ToolCall:
    """Structured-output parsing, never free-text execution (CLAUDE.md §23).

    Malformed or hallucinated output degrades to ToolCall(None, {}) --
    "no action" -- rather than raising or guessing, since a model output
    that does not fit the schema must not be trusted with an ERP mutation.
    """
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return ToolCall(None, {})

    tool_name = parsed.get("tool_name")
    valid_names = {t.name for t in tools}
    if tool_name not in valid_names:
        return ToolCall(None, {})

    arguments = parsed.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}
    return ToolCall(tool_name, arguments)
