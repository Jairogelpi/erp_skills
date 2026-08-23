"""OpenRouter-backed LLMClient (CLAUDE.md §18, D-03).

Third real provider option, alongside `groq_client.py` and
`gemini_client.py`. CLAUDE.md D-03 only requires that A, B, and C share
"el mismo modelo, proveedor, versión/configuración" within one run --
this repository tried Groq (500k-tokens/day free tier, exhausted by
earlier interrupted runs) and Gemini (a 20-requests/day free-tier cap on
every model tested, too small for this workload) before this one.

Uses `httpx` directly against OpenRouter's OpenAI-compatible REST
endpoint rather than adding the `openai` SDK as a dependency for one
call shape this repository already knows how to make (see
`groq_client.py`, `gemini_client.py`).

The API key is read from the `OPENROUTER_API_KEY` environment variable
and is never read from, or written to, any file this repository commits.

**Model choice (v2.1 confirmatory campaign, n_main=1184).** `openai/
gpt-oss-20b:free` (used for the v1 confirmatory run) is replaced by
`deepseek/deepseek-v4-flash`, a paid, materially more capable model
(DeepSeek V4 generation, GA 2026-08-13) -- chosen deliberately over a
cheaper/weaker model: a stronger baseline model makes System B (which
depends entirely on the model's own tool selection and argument
extraction) a harder system for C to outperform, so any STSR advantage
C still holds is a stronger claim, not a weaker one. This repository's
own data already shows model quality shifts B's STSR by double digits
(0.333 stub -> 0.483-0.517 across real providers) and can shrink or
erase a fragile task-success gap -- see docs/results.md's "amenaza
3b/3c". Declared risk, not hidden: OpenRouter previously produced 429
storms at this project's campaign scale (~3h with interruptions vs
~50min on Groq for a smaller v1 run); this module's per-arm checkpoint/
resume (erp_agent_os.experiment_v2_1) is the mitigation, not a fix --
expect this run may need more than one sitting.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, replace

import httpx

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

# deepseek/deepseek-v4-flash: paid, not the ":free" suffix -- the free
# variant carries harsher/less predictable OpenRouter rate limits than
# a funded paid model does, on top of the reliability risk already
# declared in the module docstring above. See that docstring for why
# this replaced openai/gpt-oss-20b:free (used for the v1 confirmatory
# run).
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_TEMPERATURE = 0.0  # low temperature: CLAUDE.md §23 ("temperatura baja")
DEFAULT_MAX_RETRIES = 5
DEFAULT_TIMEOUT_SECONDS = 30
# Paid models carry no OpenRouter-side hard RPM cap (the underlying
# provider's own ceiling applies instead, unknown in advance) -- 3.0s
# was calibrated for the ":free" tier's own throttle, not this one.
# 1.0s is a moderate speedup, not a measured-safe number: _retry_delay
# already honors a 429's Retry-After header, so an operator who sees
# real throttling can lower aggressiveness by raising
# OPENROUTER_MIN_INTERVAL_SECONDS (scripts/run_confirmatory_v2_1.py)
# without a code change or re-freeze.
DEFAULT_MIN_INTERVAL_SECONDS = 1.0
# This model reasons before answering (visible in `message.reasoning`);
# too small a budget truncates the final JSON answer.
DEFAULT_MAX_TOKENS = 400

_RETRY_AFTER_RE = re.compile(r"retry.{0,10}?(\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


class MissingApiKeyError(RuntimeError):
    """Raised when OPENROUTER_API_KEY is not set. Never falls back silently."""


@dataclass(frozen=True)
class OpenRouterConfig:
    """Registered, reproducible provider configuration (CLAUDE.md D-03)."""

    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_tokens: int = DEFAULT_MAX_TOKENS
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS


_SYSTEM_PROMPT = SELECTION_SYSTEM_PROMPT


def _tool_menu(tools: list[ToolSpec]) -> str:
    lines = [
        f"- {t.name}: {t.description} (campos: {', '.join(t.required_arguments)})"
        for t in tools
    ]
    return "\n".join(lines)


class OpenRouterClient:
    """Real LLMClient over the OpenRouter API. See module docstring."""

    def __init__(self, config: OpenRouterConfig | None = None) -> None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise MissingApiKeyError(
                "OPENROUTER_API_KEY is not set. Get a free key at "
                "https://openrouter.ai/keys and export it "
                "(e.g. in a local .env file, never committed) before "
                "constructing OpenRouterClient."
            )
        self._config = config or OpenRouterConfig()
        self._client = httpx.Client(
            base_url="https://openrouter.ai/api/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self._config.timeout_seconds,
        )
        self._last_call_at: float | None = None

    @property
    def config(self) -> OpenRouterConfig:
        return self._config

    def _pace(self) -> None:
        """Sleep so consecutive calls stay under the free-tier rate limit."""
        if self._last_call_at is not None:
            elapsed = time.monotonic() - self._last_call_at
            remaining = self._config.min_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_call_at = time.monotonic()

    def _completion(self, system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
        """One retried, paced chat completion. Returns (content, in, out)."""
        payload = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        last_error: Exception | None = None
        for attempt in range(self._config.max_retries):
            self._pace()
            logger.info(
                "openrouter call attempt=%d/%d query=%r",
                attempt + 1,
                self._config.max_retries,
                user_prompt[:60],
            )
            call_started = time.monotonic()
            try:
                response = self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"].get("content") or "{}"
                usage = data.get("usage") or {}
                logger.info(
                    "openrouter call ok in %.2fs", time.monotonic() - call_started
                )
                return (
                    content,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                )
            except Exception as exc:  # noqa: BLE001 - retry any transient failure
                last_error = exc
                if attempt < self._config.max_retries - 1:
                    delay = _retry_delay(exc, attempt)
                    logger.warning(
                        "openrouter call failed (%s: %s), retrying in %.1fs",
                        type(exc).__name__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "openrouter call failed (%s: %s), no attempts left",
                        type(exc).__name__,
                        exc,
                    )

        raise RuntimeError(
            f"OpenRouter call failed after {self._config.max_retries} attempts"
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
    """Honor a 429 response's Retry-After header or body hint; else back off."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        retry_after = exc.response.headers.get("retry-after")
        if retry_after is not None:
            try:
                return float(retry_after) + 0.5
            except ValueError:
                pass
        match = _RETRY_AFTER_RE.search(exc.response.text or "")
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
