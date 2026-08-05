"""System A: direct LLM agent with generic ERP tools, no governance.

Scope per CLAUDE.md §18: "El modelo dispone de herramientas ERP genéricas
y puede ejecutar sin registro de skills, policy engine específico ni
verificación independiente." Tools operate directly on `FakeERPAdapter`'s
create/get/update — no skill contract, no risk tiering, no approval, no
audit trail, no postcondition check. This is the deliberately ungoverned
baseline the confirmatory experiment measures System C against; it is
not meant to be safe.
"""

from dataclasses import dataclass
from typing import Any

from erp_agent_os.adapters import FakeERPAdapter, UnknownModelError, UnknownRecordError
from erp_agent_os.llm_client import LLMClient, ToolSpec

GENERIC_TOOLS: list[ToolSpec] = [
    ToolSpec("create_record", "create a new record in a model", ["model", "fields"]),
    ToolSpec(
        "update_record",
        "update an existing record by id",
        ["model", "record_id", "fields"],
    ),
    ToolSpec("get_record", "read a record by id", ["model", "record_id"]),
]


@dataclass(frozen=True)
class SystemAResult:
    tool_name: str | None
    output: Any
    error: str | None


class SystemA:
    def __init__(self, erp: FakeERPAdapter, llm: LLMClient) -> None:
        self._erp = erp
        self._llm = llm

    def handle(self, query_text: str, args: dict[str, Any]) -> SystemAResult:
        call = self._llm.propose_action(query_text, GENERIC_TOOLS)
        if call.tool_name is None:
            return SystemAResult(None, None, "no tool selected")

        try:
            if call.tool_name == "create_record":
                output: Any = self._erp.create(args["model"], args["fields"])
            elif call.tool_name == "update_record":
                self._erp.update(args["model"], args["record_id"], args["fields"])
                output = args["record_id"]
            elif call.tool_name == "get_record":
                output = self._erp.get(args["model"], args["record_id"])
            else:
                return SystemAResult(call.tool_name, None, "unknown tool")
        except (UnknownModelError, UnknownRecordError, KeyError) as exc:
            return SystemAResult(call.tool_name, None, f"{type(exc).__name__}: {exc}")

        return SystemAResult(call.tool_name, output, None)
