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
import logging
import os
import time
from dataclasses import dataclass, replace

from groq import Groq, RateLimitError

from erp_agent_os.llm_client import (
    EXTRACTION_SYSTEM_PROMPT,
    SELECTION_SYSTEM_PROMPT,
    ArgumentExtraction,
    ToolCall,
    ToolSpec,
    build_extraction_prompt,
    parse_extraction,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_TEMPERATURE = 0.0  # low temperature: CLAUDE.md §23 ("temperatura baja")
DEFAULT_MAX_RETRIES = 5
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MIN_INTERVAL_SECONDS = 2.0  # paces calls to stay under free-tier RPM


class MissingApiKeyError(RuntimeError):
    """Raised when GROQ_API_KEY is not set. Never falls back silently."""


@dataclass(frozen=True)
class GroqConfig:
    """Registered, reproducible provider configuration (CLAUDE.md D-03)."""

    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS


_SYSTEM_PROMPT = SELECTION_SYSTEM_PROMPT


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
        self._last_call_at: float | None = None

    @property
    def config(self) -> GroqConfig:
        return self._config

    def _pace(self) -> None:
        """Sleep so consecutive calls stay under the free-tier RPM limit."""
        if self._last_call_at is not None:
            elapsed = time.monotonic() - self._last_call_at
            remaining = self._config.min_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_call_at = time.monotonic()

    def _completion(self, system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
        """One retried, paced chat completion. Returns (content, in, out)."""
        last_error: Exception | None = None
        for attempt in range(self._config.max_retries):
            self._pace()
            logger.info(
                "groq call attempt=%d/%d query=%r",
                attempt + 1,
                self._config.max_retries,
                user_prompt[:60],
            )
            call_started = time.monotonic()
            try:
                response = self._client.chat.completions.create(
                    model=self._config.model,
                    temperature=self._config.temperature,
                    max_tokens=300,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = response.choices[0].message.content or "{}"
                logger.info("groq call ok in %.2fs", time.monotonic() - call_started)
                usage = response.usage
                if usage is None:
                    return content, 0, 0
                return content, usage.prompt_tokens, usage.completion_tokens
            except Exception as exc:  # noqa: BLE001 - retry any transient failure
                last_error = exc
                if attempt < self._config.max_retries - 1:
                    delay = _retry_delay(exc, attempt)
                    logger.warning(
                        "groq call failed (%s: %s), retrying in %.1fs",
                        type(exc).__name__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "groq call failed (%s: %s), no attempts left",
                        type(exc).__name__,
                        exc,
                    )

        raise RuntimeError(
            f"Groq call failed after {self._config.max_retries} attempts"
        ) from last_error

    def propose_action(self, query_text: str, tools: list[ToolSpec]) -> ToolCall:
        if not tools:
            return ToolCall(None, {})

        content, prompt_tokens, completion_tokens = self._completion(
            _SYSTEM_PROMPT,
            f"Peticion: {query_text}\n\nHerramientas disponibles:\n{_tool_menu(tools)}",
        )
        return replace(
            _parse_tool_call(content, tools),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def extract_arguments(
        self, query_text: str, fields: list[str]
    ) -> ArgumentExtraction:
        if not fields:
            return ArgumentExtraction({})
        content, prompt_tokens, completion_tokens = self._completion(
            EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt(query_text, fields)
        )
        return ArgumentExtraction(
            parse_extraction(content, fields), prompt_tokens, completion_tokens
        )


def _retry_delay(exc: Exception, attempt: int) -> float:
    """Honor the server's Retry-After header on 429s; else back off."""
    if isinstance(exc, RateLimitError):
        retry_after = exc.response.headers.get("retry-after")
        if retry_after is not None:
            try:
                return float(retry_after) + 0.5
            except ValueError:
                pass
    return float(2**attempt)


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
