"""Deterministic runtime: registered handlers, idempotency, postconditions.

Scope per CLAUDE.md §25: only registered handlers execute; a repeated
idempotency key replays the stored result instead of re-invoking the
handler; postconditions are checked after execution. Policy decisions other
than ALLOW never reach the handler (DENY/REQUIRE_APPROVAL block execution;
SIMULATE previews without mutating).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from erp_agent_os.adapters import ErpAdapter, UnknownModelError, UnknownRecordError
from erp_agent_os.policy import PolicyDecision, decide
from erp_agent_os.skills import SkillDefinition
from erp_agent_os.validation import Finding

# Runtime is generic over the concrete adapter type (FakeERPAdapter,
# Odoo19Adapter, ...): a handler written for FakeERPAdapter promises
# only to accept FakeERPAdapter, not "any ErpAdapter" -- Callable
# parameter types are contravariant, so binding Runtime to a fixed
# ErpAdapter type would reject those handlers even though they work
# correctly at runtime. Parametrizing per Runtime instance keeps mypy
# honest about which adapter a given registered handler was written for.
T = TypeVar("T", bound=ErpAdapter)

Handler = Callable[[T, dict[str, Any]], Any]
PostconditionCheck = Callable[[T, Any], bool]


class UnregisteredHandlerError(ValueError):
    """Raised when a skill's handler was never registered with the runtime."""


def preview_mutation(skill: SkillDefinition, args: dict[str, Any]) -> dict[str, Any]:
    """What a skill would change, described without executing it (RF-11).

    CLAUDE.md §12 CU-01 step 8 and RF-11 ask the system to show a
    preview of the mutation before it happens. This builds that preview
    from the skill contract -- its module, operation, declared
    postconditions and the arguments as validated -- so it is
    adapter-agnostic and, crucially, touches no ERP at all.
    """
    return {
        "skill_id": skill.skill_id,
        "skill_version": skill.version,
        "module": skill.module,
        "operation": skill.operation,
        "risk_class": skill.risk_class.value,
        "arguments": dict(args),
        "postconditions_to_verify": list(skill.postconditions),
    }


@dataclass(frozen=True)
class ExecutionResult:
    decision: PolicyDecision
    output: Any | None
    idempotent_replay: bool
    postconditions_met: bool | None
    handler_error: str | None = None
    # RF-11: populated only for SIMULATE, where the point is to show
    # what would happen instead of doing it.
    preview: dict[str, Any] | None = None


class Runtime(Generic[T]):
    def __init__(self, erp: T) -> None:
        self._erp = erp
        self._handlers: dict[tuple[str, str], Handler[T]] = {}
        self._idempotency_cache: dict[str, ExecutionResult] = {}

    def register(self, skill_id: str, version: str, handler: Handler[T]) -> None:
        self._handlers[(skill_id, version)] = handler

    def execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        role: str,
        idempotency_key: str,
        *,
        approval_granted: bool = False,
        postcondition_checks: tuple[PostconditionCheck[T], ...] = (),
        findings: list[Finding] | None = None,
    ) -> ExecutionResult:
        outcome = decide(
            skill, role, approval_granted=approval_granted, findings=findings
        )

        if outcome.decision in (PolicyDecision.DENY, PolicyDecision.REQUIRE_APPROVAL):
            return ExecutionResult(outcome.decision, None, False, None)

        if outcome.decision is PolicyDecision.SIMULATE:
            # RF-11: show what *would* change. Derived from the skill
            # contract and the normalized arguments, never by executing
            # and rolling back: a rollback-based preview would need
            # snapshot/restore, which `Odoo19Adapter` deliberately does
            # not offer, and would briefly mutate a real ERP.
            return ExecutionResult(
                outcome.decision,
                None,
                False,
                None,
                preview=preview_mutation(skill, args),
            )

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
