"""Pluggable LLM client interface shared by Systems A and B.

Scope per CLAUDE.md §18: both baselines delegate "pick a tool, propose
arguments" to an LLM. No provider is called from this repository — a
real comparative run needs a real client (e.g. wrapping the Anthropic
SDK) reading its API key from the environment, never committed here.

`DeterministicStubClient` is a keyword-overlap stand-in for tests and
local plumbing checks ONLY. It is not an LLM. CLAUDE.md D-03 requires A,
B, and C to share "el mismo modelo, proveedor, versión/configuración" —
using this stub to produce confirmatory A/B/C results would invalidate
the comparison outright, not merely weaken it. It exists so this
repository's systems are testable and demonstrable without requiring
API credentials in CI.
"""

import json
from dataclasses import dataclass, replace
from typing import Any, Protocol

# Shared by every real client so the three providers are prompted
# identically for argument extraction (CLAUDE.md D-03: A/B/C must share
# the same configuration in everything comparable).
EXTRACTION_SYSTEM_PROMPT = (
    "Eres un extractor de datos para un ERP. Dada una peticion en espanol "
    "y una lista de campos, devuelve el valor de cada campo tal como "
    "aparece en el texto. Responde EXCLUSIVAMENTE con un objeto JSON "
    'de la forma {"<campo>": "<valor>"}. Omite por completo cualquier '
    "campo cuyo valor no puedas inferir del texto con evidencia clara: "
    "no inventes, no rellenes con marcadores, no expliques nada."
)


def build_extraction_prompt(query_text: str, fields: list[str]) -> str:
    return f"Peticion: {query_text}\n\nCampos a extraer: {', '.join(fields)}"


def parse_extraction(content: str, fields: list[str]) -> dict[str, Any]:
    """Keep only requested, non-empty fields from the model's JSON.

    Anything the model volunteered that was not asked for is dropped:
    an extractor that invents fields must not be able to widen the
    argument set a skill will be validated against.
    """
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    wanted = set(fields)
    return {
        key: value
        for key, value in parsed.items()
        if key in wanted and value is not None and str(value).strip()
    }


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    required_arguments: list[str]


@dataclass(frozen=True)
class ToolCall:
    tool_name: str | None
    arguments: dict[str, Any]
    # Real per-call token counts (CLAUDE.md H2/H8). 0 for any client that
    # made no real LLM call -- DeterministicStubClient always, System C
    # never (its retrieval is TF-IDF), so 0 here means "no cost", not
    # "unmeasured".
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class ArgumentExtraction:
    """Structured arguments an LLM read out of raw request text.

    Exists to remove a real measurement bias in the H2 (token) result:
    the paired experiment originally handed every system
    `case.expected_arguments` -- a *perfect* parse nobody paid for -- so
    A and B spent tokens only on tool selection and System C spent zero
    tokens overall. That made C look free when in a real deployment it
    would still need an LLM to turn "Crea una oportunidad para Acme por
    15000 euros" into `{"customer_name": "Acme", "expected_revenue":
    15000}`. With this step, all three systems pay the same
    argument-extraction cost and the token comparison isolates what the
    thesis actually claims: that retrieval replaces the tool-selection
    LLM call.
    """

    arguments: dict[str, Any]
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient(Protocol):
    def propose_action(self, query_text: str, tools: list[ToolSpec]) -> ToolCall: ...

    def extract_arguments(
        self, query_text: str, fields: list[str]
    ) -> ArgumentExtraction: ...


class DeterministicStubClient:
    """Keyword-overlap tool picker. Test/dev plumbing only — see module docstring."""

    def propose_action(self, query_text: str, tools: list[ToolSpec]) -> ToolCall:
        query_tokens = set(query_text.lower().split())
        best: tuple[int, ToolSpec] | None = None
        for tool in tools:
            overlap = len(query_tokens & set(tool.description.lower().split()))
            if best is None or overlap > best[0]:
                best = (overlap, tool)
        if best is None or best[0] == 0:
            return ToolCall(None, {})
        return ToolCall(best[1].name, {})

    def extract_arguments(
        self, query_text: str, fields: list[str]
    ) -> ArgumentExtraction:
        """Extracts nothing: this stub is not a language model.

        Returning empty (rather than guessing) is deliberate -- a run
        that uses the stub for argument extraction would score every
        system at zero, which is obviously wrong and therefore obviously
        not confirmatory. `scripts/run_experiment.py` refuses the
        combination rather than letting it produce a plausible-looking
        but meaningless number.
        """
        return ArgumentExtraction({})


class CachingLLMClient:
    """Caches propose_action by (query_text, tool names) within one process.

    The paired experiment calls the same case 3 times (once per
    repetition, CLAUDE.md §19); with `temperature=0.0` (§23) two
    independent real runs already showed the result is reproducible
    (H3 = 1.0 both times). Rather than pay for and wait on the same real
    LLM call three times, only the first call per unique query is real --
    the rest are served from cache. Cached calls report 0 tokens: no
    second call was actually made, so reporting real usage again would
    overcount actual spend for H2/H8.
    """

    def __init__(self, inner: LLMClient) -> None:
        self._inner = inner
        self._cache: dict[tuple[str, tuple[str, ...]], ToolCall] = {}
        self._extraction_cache: dict[
            tuple[str, tuple[str, ...]], ArgumentExtraction
        ] = {}

    def propose_action(self, query_text: str, tools: list[ToolSpec]) -> ToolCall:
        key = (query_text, tuple(t.name for t in tools))
        cached = self._cache.get(key)
        if cached is not None:
            return replace(cached, prompt_tokens=0, completion_tokens=0)
        result = self._inner.propose_action(query_text, tools)
        self._cache[key] = result
        return result

    def extract_arguments(
        self, query_text: str, fields: list[str]
    ) -> ArgumentExtraction:
        key = (query_text, tuple(fields))
        cached = self._extraction_cache.get(key)
        if cached is not None:
            return replace(cached, prompt_tokens=0, completion_tokens=0)
        result = self._inner.extract_arguments(query_text, fields)
        self._extraction_cache[key] = result
        return result
