"""Gemini-backed LLMClient (CLAUDE.md §18, D-03).

Second real free-tier provider, alongside `groq_client.py`. CLAUDE.md
does not mandate a specific commercial provider — D-03 only requires
that A, B, and C share "el mismo modelo, proveedor, versión/
configuración" within one run. Whichever provider a run uses, it is used
identically across all three systems; a run's manifest records which one
(see `ExperimentManifest.selector`).

`gemini-2.5-flash-lite` was picked over the newer `gemini-flash-latest`
alias (which resolved to `gemini-3.6-flash` when this was written)
because the newest flagship model's free tier turned out to carry a
20-requests-PER-DAY quota on this key -- unusable for ~240 real calls
per confirmatory run. `gemini-2.5-flash-lite` is stable (not an alias
that can silently repoint to a low-quota model) and has a free-tier
daily quota this workload actually fits in.

The API key is read from the `GEMINI_API_KEY` environment variable and is
never read from, or written to, any file this repository commits. If the
variable is absent, constructing this client raises immediately rather
than silently falling back to a stub.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, replace

from google import genai
from google.genai import errors, types

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

DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_TEMPERATURE = 0.0  # low temperature: CLAUDE.md §23 ("temperatura baja")
DEFAULT_MAX_RETRIES = 5
# gemini-2.5-flash-lite's free tier is 10 requests PER MINUTE (not per
# day, unlike Groq): 6s/call already clears it, 7s leaves margin.
DEFAULT_MIN_INTERVAL_SECONDS = 7.0
# Flash-tier Gemini models spend part of the output budget on internal
# "thinking" tokens before the visible JSON answer; too small a budget
# truncates the answer to nothing (observed: 100 tokens -> empty text).
DEFAULT_MAX_OUTPUT_TOKENS = 500

_RETRY_AFTER_RE = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)


class MissingApiKeyError(RuntimeError):
    """Raised when GEMINI_API_KEY is not set. Never falls back silently."""


@dataclass(frozen=True)
class GeminiConfig:
    """Registered, reproducible provider configuration (CLAUDE.md D-03)."""

    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_retries: int = DEFAULT_MAX_RETRIES
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS


_SYSTEM_PROMPT = SELECTION_SYSTEM_PROMPT


def _tool_menu(tools: list[ToolSpec]) -> str:
    lines = [
        f"- {t.name}: {t.description} (campos: {', '.join(t.required_arguments)})"
        for t in tools
    ]
    return "\n".join(lines)


class GeminiClient:
    """Real LLMClient over the Gemini API. See module docstring for scope."""

    def __init__(self, config: GeminiConfig | None = None) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise MissingApiKeyError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey and export it "
                "(e.g. in a local .env file, never committed) before "
                "constructing GeminiClient."
            )
        self._config = config or GeminiConfig()
        self._client = genai.Client(api_key=api_key)
        self._last_call_at: float | None = None

    @property
    def config(self) -> GeminiConfig:
        return self._config

    def _pace(self) -> None:
        """Sleep so consecutive calls stay under the free-tier RPM limit."""
        if self._last_call_at is not None:
            elapsed = time.monotonic() - self._last_call_at
            remaining = self._config.min_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_call_at = time.monotonic()

    def _completion(self, prompt: str) -> tuple[str, int, int]:
        """One retried, paced generate_content call. Returns (content, in, out)."""
        config = types.GenerateContentConfig(
            temperature=self._config.temperature,
            max_output_tokens=self._config.max_output_tokens,
            response_mime_type="application/json",
        )

        last_error: Exception | None = None
        for attempt in range(self._config.max_retries):
            self._pace()
            logger.info(
                "gemini call attempt=%d/%d query=%r",
                attempt + 1,
                self._config.max_retries,
                prompt[:60],
            )
            call_started = time.monotonic()
            try:
                response = self._client.models.generate_content(
                    model=self._config.model, contents=prompt, config=config
                )
                content = response.text or "{}"
                usage = response.usage_metadata
                logger.info("gemini call ok in %.2fs", time.monotonic() - call_started)
                if usage is None:
                    return content, 0, 0
                return (
                    content,
                    usage.prompt_token_count or 0,
                    usage.candidates_token_count or 0,
                )
            except Exception as exc:  # noqa: BLE001 - retry any transient failure
                last_error = exc
                if attempt < self._config.max_retries - 1:
                    delay = _retry_delay(exc, attempt)
                    logger.warning(
                        "gemini call failed (%s: %s), retrying in %.1fs",
                        type(exc).__name__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "gemini call failed (%s: %s), no attempts left",
                        type(exc).__name__,
                        exc,
                    )

        raise RuntimeError(
            f"Gemini call failed after {self._config.max_retries} attempts"
        ) from last_error

    def propose_action(self, query_text: str, tools: list[ToolSpec]) -> ToolCall:
        if not tools:
            return ToolCall(None, {})

        content, prompt_tokens, completion_tokens = self._completion(
            f"{_SYSTEM_PROMPT}\n\nPeticion: {query_text}\n\n"
            f"Herramientas disponibles:\n{_tool_menu(tools)}"
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
            f"{EXTRACTION_SYSTEM_PROMPT}\n\n"
            f"{build_extraction_prompt(query_text, fields)}"
        )
        return ArgumentExtraction(
            parse_extraction(content, fields), prompt_tokens, completion_tokens
        )


def _retry_delay(exc: Exception, attempt: int) -> float:
    """Honor the server's "Please retry in Xs" hint on 429s; else back off."""
    if isinstance(exc, errors.ClientError) and exc.status == "RESOURCE_EXHAUSTED":
        match = _RETRY_AFTER_RE.search(exc.message or "")
        if match:
            return float(match.group(1)) + 0.5
    return float(2**attempt)


def _parse_tool_call(content: str, tools: list[ToolSpec]) -> ToolCall:
    """Structured-output parsing, never free-text execution (CLAUDE.md §23).

    Malformed or hallucinated output degrades to ToolCall(None, {}) --
    "no action" -- rather than raising or guessing.
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
