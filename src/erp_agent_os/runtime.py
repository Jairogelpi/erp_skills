"""Deterministic runtime: registered handlers, idempotency, postconditions.

Scope per CLAUDE.md §25: only registered handlers execute; a repeated
idempotency key replays the stored result instead of re-invoking the
handler; postconditions are checked after execution. Policy decisions other
than ALLOW never reach the handler (DENY/REQUIRE_APPROVAL block execution;
SIMULATE previews without mutating).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from erp_agent_os.adapters import (
    FakeERPAdapter,
    UnknownModelError,
    UnknownRecordError,
)
from erp_agent_os.policy import PolicyDecision, decide
from erp_agent_os.skills import SkillDefinition
from erp_agent_os.validation import Finding

Handler = Callable[[FakeERPAdapter, dict[str, Any]], Any]
PostconditionCheck = Callable[[FakeERPAdapter, Any], bool]


class UnregisteredHandlerError(ValueError):
    """Raised when a skill's handler was never registered with the runtime."""


@dataclass(frozen=True)
class ExecutionResult:
    decision: PolicyDecision
    output: Any | None
    idempotent_replay: bool
    postconditions_met: bool | None
    handler_error: str | None = None


class Runtime:
    def __init__(self, erp: FakeERPAdapter) -> None:
        self._erp = erp
        self._handlers: dict[tuple[str, str], Handler] = {}
        self._idempotency_cache: dict[str, ExecutionResult] = {}

    def register(self, skill_id: str, version: str, handler: Handler) -> None:
        self._handlers[(skill_id, version)] = handler

    def execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        role: str,
        idempotency_key: str,
        *,
        approval_granted: bool = False,
        postcondition_checks: tuple[PostconditionCheck, ...] = (),
        findings: list[Finding] | None = None,
    ) -> ExecutionResult:
        outcome = decide(
            skill, role, approval_granted=approval_granted, findings=findings
        )

        if outcome.decision in (PolicyDecision.DENY, PolicyDecision.REQUIRE_APPROVAL):
            return ExecutionResult(outcome.decision, None, False, None)

        if outcome.decision is PolicyDecision.SIMULATE:
            return ExecutionResult(outcome.decision, None, False, None)

        cached = self._idempotency_cache.get(idempotency_key)
        if cached is not None:
            return ExecutionResult(
                cached.decision, cached.output, True, cached.postconditions_met
            )

        handler = self._handlers.get((skill.skill_id, skill.version))
        if handler is None:
            raise UnregisteredHandlerError(f"{skill.skill_id}@{skill.version}")

        try:
            output = handler(self._erp, args)
        except (UnknownModelError, UnknownRecordError, KeyError) as exc:
            error_message = f"{type(exc).__name__}: {exc}"
            return ExecutionResult(
                outcome.decision, None, False, None, handler_error=error_message
            )

        postconditions_met = (
            all(check(self._erp, output) for check in postcondition_checks)
            if postcondition_checks
            else None
        )
        result = ExecutionResult(outcome.decision, output, False, postconditions_met)
        self._idempotency_cache[idempotency_key] = result
        return result
