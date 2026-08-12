"""Append-only audit trail with correlation and field redaction.

Scope per CLAUDE.md §14 (Audit Store) and §15/§30 (redaction): record one
immutable event per policy decision + execution outcome, queryable by
correlation id. No mutation or delete method is exposed — append-only is
enforced by the module's public surface, not by a caller-checked flag.
"""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from erp_agent_os.policy import PolicyOutcome
from erp_agent_os.runtime import (
    ExecutionResult,
    VerificationCheckResult,
    VerificationStatus,
)
from erp_agent_os.skills import SkillDefinition

REDACTED = "***REDACTED***"


def _redact(value: Any, redact_keys: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if key in redact_keys else _redact(val, redact_keys)
            for key, val in value.items()
        }
    return value


@dataclass(frozen=True)
class AuditEvent:
    correlation_id: str
    skill_id: str
    skill_version: str
    role: str
    decision: str
    risk_score: float
    reasons: tuple[str, ...]
    idempotency_key: str
    idempotent_replay: bool
    postconditions_met: bool | None
    output: Any
    recorded_at: datetime
    verification_status: str = VerificationStatus.VERIFIER_ERROR.value
    check_results: tuple[VerificationCheckResult, ...] = ()


@dataclass(frozen=True)
class AbstentionEvent:
    correlation_id: str
    reasons: tuple[str, ...]
    recorded_at: datetime
    verification_status: str = VerificationStatus.VERIFIER_ERROR.value
    postconditions_met: bool | None = None
    check_results: tuple[VerificationCheckResult, ...] = ()


class AuditStore:
    def __init__(
        self,
        *,
        redact_keys: frozenset[str] = frozenset(),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._redact_keys = redact_keys
        self._clock = clock
        self._events: list[AuditEvent] = []
        self._abstentions: list[AbstentionEvent] = []

    def record(
        self,
        correlation_id: str,
        skill: SkillDefinition,
        role: str,
        outcome: PolicyOutcome,
        execution: ExecutionResult,
        idempotency_key: str,
    ) -> AuditEvent:
        event = AuditEvent(
            correlation_id=correlation_id,
            skill_id=skill.skill_id,
            skill_version=skill.version,
            role=role,
            decision=outcome.decision.value,
            risk_score=outcome.risk_score,
            reasons=tuple(outcome.reasons),
            idempotency_key=idempotency_key,
            idempotent_replay=execution.idempotent_replay,
            postconditions_met=execution.postconditions_met,
            output=_redact(deepcopy(execution.output), self._redact_keys),
            recorded_at=self._clock(),
            verification_status=execution.verification_status.value,
            check_results=execution.check_results,
        )
        self._events.append(event)
        return event

    def events(self, correlation_id: str | None = None) -> tuple[AuditEvent, ...]:
        if correlation_id is None:
            return tuple(self._events)
        return tuple(e for e in self._events if e.correlation_id == correlation_id)

    def record_abstention(
        self,
        correlation_id: str,
        reasons: list[str],
        *,
        verification_status: VerificationStatus | str = (
            VerificationStatus.VERIFIER_ERROR
        ),
        postconditions_met: bool | None = None,
        check_results: tuple[VerificationCheckResult, ...] = (),
    ) -> AbstentionEvent:
        status = (
            verification_status.value
            if isinstance(verification_status, VerificationStatus)
            else verification_status
        )
        event = AbstentionEvent(
            correlation_id,
            tuple(reasons),
            self._clock(),
            status,
            postconditions_met,
            check_results,
        )
        self._abstentions.append(event)
        return event

    def abstentions(
        self, correlation_id: str | None = None
    ) -> tuple[AbstentionEvent, ...]:
        if correlation_id is None:
            return tuple(self._abstentions)
        return tuple(e for e in self._abstentions if e.correlation_id == correlation_id)
