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

from dataclasses import dataclass, replace
from typing import Any, Protocol


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


class LLMClient(Protocol):
    def propose_action(self, query_text: str, tools: list[ToolSpec]) -> ToolCall: ...


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

    def propose_action(self, query_text: str, tools: list[ToolSpec]) -> ToolCall:
        key = (query_text, tuple(t.name for t in tools))
        cached = self._cache.get(key)
        if cached is not None:
            return replace(cached, prompt_tokens=0, completion_tokens=0)
        result = self._inner.propose_action(query_text, tools)
        self._cache[key] = result
        return result
