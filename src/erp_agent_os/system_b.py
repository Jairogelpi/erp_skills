"""System B: typed-tool agent, no retrieval/risk/approval/verification.

Scope per CLAUDE.md §18: "Las herramientas tienen esquemas y
validaciones de tipo, pero no existe recuperación semántica, memoria de
skills, taxonomía completa, aprobación estructurada, verificación por
postcondiciones." Reuses the 12-skill catalog's `input_schema` and
`handlers` — the same tool surface as System C — but the LLM picks the
tool directly (no TF-IDF/embedding ranking, no abstention threshold), and
execution has no risk-tiered policy decision, no audit trail, and no
postcondition check.
"""

from dataclasses import dataclass
from typing import Any

from erp_agent_os.adapters import FakeERPAdapter, UnknownModelError, UnknownRecordError
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.handlers import HANDLERS
from erp_agent_os.llm_client import LLMClient, ToolSpec

TYPED_TOOLS: list[ToolSpec] = [
    ToolSpec(skill.skill_id, skill.description, skill.input_schema["required"])
    for skill in CATALOG
]


@dataclass(frozen=True)
class SystemBResult:
    skill_id: str | None
    output: Any
    error: str | None
    prompt_tokens: int = 0
    completion_tokens: int = 0


class SystemB:
    def __init__(self, erp: FakeERPAdapter, llm: LLMClient) -> None:
        self._erp = erp
        self._llm = llm

    def handle(self, query_text: str, arguments: dict[str, Any]) -> SystemBResult:
        call = self._llm.propose_action(query_text, TYPED_TOOLS)
        tokens = (call.prompt_tokens, call.completion_tokens)
        if call.tool_name is None or call.tool_name not in CATALOG_BY_ID:
            return SystemBResult(None, None, "no matching tool", *tokens)

        skill = CATALOG_BY_ID[call.tool_name]
        required = skill.input_schema["required"]
        missing = [
            field
            for field in required
            if field not in arguments or not str(arguments[field]).strip()
        ]
        if missing:
            return SystemBResult(
                skill.skill_id, None, f"missing required fields: {missing}", *tokens
            )

        try:
            output = HANDLERS[skill.skill_id](self._erp, arguments)
        except (UnknownModelError, UnknownRecordError, KeyError) as exc:
            return SystemBResult(
                skill.skill_id, None, f"{type(exc).__name__}: {exc}", *tokens
            )

        return SystemBResult(skill.skill_id, output, None, *tokens)
