"""System C: parser -> retriever -> policy -> runtime -> audit, end to end.

Scope per CLAUDE.md §14 (architecture diagram) and roadmap P5.4: the only
path through which ERP Agent OS's governed system executes a request.
Abstention short-circuits before any policy/runtime call and is still
audited (CLAUDE.md §25: every terminal decision is recorded). No LLM call
here — `IntentProposal` is taken as already produced (work unit 7's scope).
"""

from collections.abc import Callable
from dataclasses import dataclass

from erp_agent_os.adapters import ErpAdapter
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditStore
from erp_agent_os.parser import IntentProposal
from erp_agent_os.policy import decide
from erp_agent_os.retrieval import RetrievalCandidate, TfidfRetriever, should_abstain
from erp_agent_os.runtime import ExecutionResult, Runtime
from erp_agent_os.validation import (
    detect_text_signals,
    normalize_arguments,
    validate_arguments,
)

AbstainFn = Callable[[list[RetrievalCandidate], list[str]], bool]


@dataclass(frozen=True)
class SystemCResult:
    decision: str
    selected_skill_id: str | None
    execution: ExecutionResult | None
    reasons: tuple[str, ...]


class SystemC:
    def __init__(
        self,
        erp: ErpAdapter,
        runtime: Runtime,
        retriever: TfidfRetriever,
        audit: AuditStore,
        approval: ApprovalService | None = None,
        *,
        abstain: AbstainFn = should_abstain,
    ) -> None:
        self._erp = erp
        self._runtime = runtime
        self._retriever = retriever
        self._audit = audit
        self._approval = approval
        # v2.1 Task 8's C_NO_ABSTENTION ablation (docs/tfm-closure-no-
        # human-v2.1.md section 6.1/8): the ONLY permitted difference from
        # C is disabling the confidence/abstention gate -- everything else
        # (parser, retriever, candidates, policy, runtime, state) stays
        # identical because it is the same SystemC class and the same
        # `handle()` method, just called with a different `abstain`
        # callable. Defaults to the real gate, so every existing caller
        # (and every test that constructs SystemC positionally) is
        # unaffected.
        self._abstain = abstain

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

        if self._abstain(ranked, proposal.missing_fields):
            reasons = ["no confident candidate"]
            self._audit.record_abstention(correlation_id, reasons)
            return SystemCResult("ABSTAIN", None, None, tuple(reasons))

        skill = ranked[0].skill
        approval_granted = bool(
            self._approval and self._approval.is_valid(skill.skill_id)
        )

        # Normalize before validating and before executing (CLAUDE.md
        # §20, "entrada normalizada"): "27600 euros" is the right number
        # carrying its unit, not a type error. Validation still sees --
        # and rejects -- anything that is not a plain number.
        arguments = normalize_arguments(skill, proposal.arguments)

        findings = detect_text_signals(query_text) + validate_arguments(
            skill, arguments
        )

        outcome = decide(
            skill, role, approval_granted=approval_granted, findings=findings
        )
        execution = self._runtime.execute(
            skill,
            arguments,
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
