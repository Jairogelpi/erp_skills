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

from dataclasses import dataclass
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
