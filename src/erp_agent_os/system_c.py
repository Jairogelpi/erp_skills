"""System C: parser -> retriever -> policy -> runtime -> audit, end to end.

Scope per CLAUDE.md §14 (architecture diagram) and roadmap P5.4: the only
path through which ERP Agent OS's governed system executes a request.
Abstention short-circuits before any policy/runtime call and is still
audited (CLAUDE.md §25: every terminal decision is recorded). No LLM call
here — `IntentProposal` is taken as already produced (work unit 7's scope).
"""

from dataclasses import dataclass

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditStore
from erp_agent_os.parser import IntentProposal
from erp_agent_os.policy import decide
from erp_agent_os.retrieval import TfidfRetriever, should_abstain
from erp_agent_os.runtime import ExecutionResult, Runtime
from erp_agent_os.validation import detect_text_signals, validate_arguments


@dataclass(frozen=True)
class SystemCResult:
    decision: str
    selected_skill_id: str | None
    execution: ExecutionResult | None
    reasons: tuple[str, ...]


class SystemC:
    def __init__(
        self,
        erp: FakeERPAdapter,
        runtime: Runtime,
        retriever: TfidfRetriever,
        audit: AuditStore,
        approval: ApprovalService | None = None,
    ) -> None:
        self._erp = erp
        self._runtime = runtime
        self._retriever = retriever
        self._audit = audit
        self._approval = approval

    def handle(
        self,
        correlation_id: str,
        query_text: str,
        proposal: IntentProposal,
        role: str,
        idempotency_key: str,
    ) -> SystemCResult:
        ranked = self._retriever.rank(query_text, role=role)

        # Missing required data is a *clarification* request, not an
        # abstention: the system knows what it needs and can ask for it.
        # Abstention is reserved for "no candidate is trustworthy enough"
        # (CLAUDE.md §17 distinguishes `CLARIFY` from `sin_skill/abstención`).
        if proposal.missing_fields:
            reasons = [f"missing field: {f}" for f in proposal.missing_fields]
            self._audit.record_abstention(correlation_id, reasons)
            return SystemCResult("CLARIFY", None, None, tuple(reasons))

        if should_abstain(ranked, proposal.missing_fields):
            reasons = ["no confident candidate"]
            self._audit.record_abstention(correlation_id, reasons)
            return SystemCResult("ABSTAIN", None, None, tuple(reasons))

        skill = ranked[0].skill
        approval_granted = bool(
            self._approval and self._approval.is_valid(skill.skill_id)
        )

        findings = detect_text_signals(query_text) + validate_arguments(
            skill, proposal.arguments
        )

        outcome = decide(
            skill, role, approval_granted=approval_granted, findings=findings
        )
        execution = self._runtime.execute(
            skill,
            proposal.arguments,
            role,
            idempotency_key,
            approval_granted=approval_granted,
            findings=findings,
        )
        self._audit.record(
            correlation_id, skill, role, outcome, execution, idempotency_key
        )

        return SystemCResult(
            execution.decision.value, skill.skill_id, execution, tuple(outcome.reasons)
        )
