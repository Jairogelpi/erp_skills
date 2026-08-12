"""Deterministic runtime: registered handlers, idempotency, postconditions.

Scope per CLAUDE.md §25: only registered handlers execute; a repeated
idempotency key replays the stored result instead of re-invoking the
handler; postconditions are checked after execution. Policy decisions other
than ALLOW never reach the handler (DENY/REQUIRE_APPROVAL block execution;
SIMULATE previews without mutating).
"""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from erp_agent_os.adapters import ErpAdapter
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


class VerificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN_CLEAN = "not_run_clean"
    NOT_RUN_DIRTY = "not_run_dirty"
    REPLAYED = "replayed"
    VERIFIER_ERROR = "verifier_error"


@dataclass(frozen=True)
class VerificationCheck(Generic[T]):
    """A stable audit identifier bound to one executable verification."""

    check_id: str
    evaluate: PostconditionCheck[T]

    def __post_init__(self) -> None:
        if not self.check_id.strip():
            raise ValueError("verification check_id must not be empty")

    def __call__(self, erp: T, output: Any) -> bool:
        return self.evaluate(erp, output)


@dataclass(frozen=True)
class VerificationCheckResult:
    """Non-sensitive evidence produced by one named verification check."""

    check_id: str
    passed: bool | None
    detail: str


def _evaluate_checks(
    erp: T,
    output: Any,
    checks: tuple[object, ...],
) -> tuple[
    VerificationStatus,
    bool | None,
    tuple[VerificationCheckResult, ...],
]:
    """Evaluate every valid named check and reduce its complete evidence.

    Bare callables are deliberately not executed: without a stable identifier
    their outcome cannot support an auditable verification claim. Exceptions
    are represented by a fixed message so ERP data and secrets in exception
    text never enter verification evidence.
    """
    if not checks:
        return VerificationStatus.VERIFIER_ERROR, None, ()

    malformed = False
    results: list[VerificationCheckResult] = []
    for candidate in checks:
        if not isinstance(candidate, VerificationCheck):
            malformed = True
            continue
        try:
            passed = bool(candidate(erp, output))
        except Exception:
            results.append(
                VerificationCheckResult(
                    candidate.check_id, None, "check raised an exception"
                )
            )
        else:
            results.append(
                VerificationCheckResult(
                    candidate.check_id,
                    passed,
                    "check passed" if passed else "check failed",
                )
            )

    evidence = tuple(results)
    if malformed or any(item.passed is None for item in evidence):
        return VerificationStatus.VERIFIER_ERROR, None, evidence
    if all(item.passed is True for item in evidence):
        return VerificationStatus.PASSED, True, evidence
    return VerificationStatus.FAILED, False, evidence


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
    verification_status: VerificationStatus = VerificationStatus.VERIFIER_ERROR
    check_results: tuple[VerificationCheckResult, ...] = ()


class Runtime(Generic[T]):
    def __init__(self, erp: T) -> None:
        self._erp = erp
        self._handlers: dict[tuple[str, str], Handler[T]] = {}
        # This ledger prevents a completed handler attempt from ever running
        # twice. Entries are not necessarily trusted verification: replayed
        # results preserve False/None and their exact evidence.
        self._idempotency_ledger: dict[str, ExecutionResult] = {}

    def register(self, skill_id: str, version: str, handler: Handler[T]) -> None:
        self._handlers[(skill_id, version)] = handler

    def _record_attempt(
        self, idempotency_key: str, result: ExecutionResult
    ) -> ExecutionResult:
        self._idempotency_ledger[idempotency_key] = ExecutionResult(
            result.decision,
            deepcopy(result.output),
            result.idempotent_replay,
            result.postconditions_met,
            handler_error=result.handler_error,
            preview=deepcopy(result.preview),
            verification_status=result.verification_status,
            check_results=result.check_results,
        )
        return result

    def execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        role: str,
        idempotency_key: str,
        *,
        approval_granted: bool = False,
        postcondition_checks: tuple[VerificationCheck[T], ...] = (),
        findings: list[Finding] | None = None,
    ) -> ExecutionResult:
        outcome = decide(
            skill, role, approval_granted=approval_granted, findings=findings
        )

        if outcome.decision is not PolicyDecision.ALLOW:
            verification_status, postconditions_met, check_results = _evaluate_checks(
                self._erp, None, postcondition_checks
            )
            if verification_status is VerificationStatus.PASSED:
                verification_status = VerificationStatus.NOT_RUN_CLEAN
            elif verification_status is VerificationStatus.FAILED:
                verification_status = VerificationStatus.NOT_RUN_DIRTY

            # RF-11: show what *would* change. Derived from the skill
            # contract and the normalized arguments, never by executing
            # and rolling back: a rollback-based preview would need
            # snapshot/restore, which `Odoo19Adapter` deliberately does
            # not offer, and would briefly mutate a real ERP.
            return ExecutionResult(
                outcome.decision,
                None,
                False,
                postconditions_met,
                preview=(
                    preview_mutation(skill, args)
                    if outcome.decision is PolicyDecision.SIMULATE
                    else None
                ),
                verification_status=verification_status,
                check_results=check_results,
            )

        cached = self._idempotency_ledger.get(idempotency_key)
        if cached is not None:
            return ExecutionResult(
                cached.decision,
                deepcopy(cached.output),
                True,
                cached.postconditions_met,
                handler_error=cached.handler_error,
                preview=deepcopy(cached.preview),
                verification_status=VerificationStatus.REPLAYED,
                check_results=cached.check_results,
            )

        handler = self._handlers.get((skill.skill_id, skill.version))
        if handler is None:
            raise UnregisteredHandlerError(f"{skill.skill_id}@{skill.version}")

        try:
            output = handler(self._erp, args)
        except Exception as exc:
            error_message = f"{type(exc).__name__}: handler execution failed"
            result = ExecutionResult(
                outcome.decision,
                None,
                False,
                None,
                handler_error=error_message,
                verification_status=VerificationStatus.VERIFIER_ERROR,
            )
            return self._record_attempt(idempotency_key, result)

        verification_status, postconditions_met, check_results = _evaluate_checks(
            self._erp, output, postcondition_checks
        )
        result = ExecutionResult(
            outcome.decision,
            output,
            False,
            postconditions_met,
            verification_status=verification_status,
            check_results=check_results,
        )
        return self._record_attempt(idempotency_key, result)
