"""Approval service: actor, scope, instant, expiration.

Scope per CLAUDE.md §14 (Approval Service) and roadmap P6.3: record who
approved what, and for how long, so `REQUIRE_APPROVAL`/R2-R3 policy
decisions can be re-checked as `approval_granted=True`. No persistence,
no linkage to the policy engine call site (that wiring is API-layer work).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Approval:
    actor: str
    scope: str
    granted_at: datetime
    expires_at: datetime


class ApprovalService:
    def __init__(
        self, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._clock = clock
        self._approvals: list[Approval] = []

    def grant(self, actor: str, scope: str, ttl_seconds: int) -> Approval:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = self._clock()
        approval = Approval(actor, scope, now, now + timedelta(seconds=ttl_seconds))
        self._approvals.append(approval)
        return approval

    @property
    def grants(self) -> list[Approval]:
        """Read-only view of every grant issued, oldest first -- so a
        UI (Approval Center) can list "ERP execution approvals granted"
        without this service growing a second, parallel storage concept."""
        return list(self._approvals)

    def is_valid(self, scope: str) -> bool:
        now = self._clock()
        return any(
            approval.scope == scope and approval.granted_at <= now < approval.expires_at
            for approval in self._approvals
        )
