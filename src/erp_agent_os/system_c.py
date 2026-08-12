"""System C: parser -> retriever -> policy -> runtime -> audit, end to end.

Scope per CLAUDE.md §14 (architecture diagram) and roadmap P5.4: the only
path through which ERP Agent OS's governed system executes a request.
Abstention short-circuits before any policy/runtime call and is still
audited (CLAUDE.md §25: every terminal decision is recorded). No LLM call
here — `IntentProposal` is taken as already produced (work unit 7's scope).
"""

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from erp_agent_os.adapters import ErpAdapter
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditStore
from erp_agent_os.dataset import RiskClass
from erp_agent_os.handlers import SKILL_MODELS
from erp_agent_os.parser import IntentProposal
from erp_agent_os.policy import decide
from erp_agent_os.postconditions import build_checks
from erp_agent_os.retrieval import TfidfRetriever, should_abstain
from erp_agent_os.runtime import (
    ExecutionResult,
    Runtime,
    VerificationCheck,
    VerificationCheckResult,
    VerificationStatus,
)
from erp_agent_os.validation import (
    detect_text_signals,
    normalize_arguments,
    validate_arguments,
)


@dataclass(frozen=True)
class SystemCResult:
    decision: str
    selected_skill_id: str | None
    execution: ExecutionResult | None
    reasons: tuple[str, ...]
    verification_status: VerificationStatus = VerificationStatus.VERIFIER_ERROR
    postconditions_met: bool | None = None
    check_results: tuple[VerificationCheckResult, ...] = ()


def _normalize_snapshot_value(value: Any) -> Any:
    """Deep-copy and deterministically order structural ERP values."""
    if isinstance(value, dict):
        return {
            key: _normalize_snapshot_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        normalized = [_normalize_snapshot_value(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, default=str
            ),
        )
    return deepcopy(value)


def _snapshot(
    erp: ErpAdapter, monitored_models: frozenset[str]
) -> dict[str, Any]:
    """Read complete allowlisted state through the adapter protocol only."""
    records: dict[str, Any] = {}
    for model in sorted(monitored_models):
        listed = erp.list(model)
        if not isinstance(listed, dict):
            raise TypeError("adapter list result must be a mapping")
        records[model] = _normalize_snapshot_value(listed)
    return {"records": records}


def _error_check(check_id: str) -> VerificationCheck[ErpAdapter]:
    def unavailable(_erp: ErpAdapter, _output: Any) -> bool:
        raise RuntimeError("verification input unavailable")

    return VerificationCheck(check_id, unavailable)


def _state_check(
    before: dict[str, Any],
    monitored_models: frozenset[str],
    *,
    check_id: str,
    excluded_models: frozenset[str] = frozenset(),
) -> VerificationCheck[ErpAdapter]:
    baseline = {
        model: deepcopy(records)
        for model, records in before["records"].items()
        if model not in excluded_models
    }

    def unchanged(erp: ErpAdapter, _output: Any) -> bool:
        after = _snapshot(erp, monitored_models)["records"]
        return all(after[model] == records for model, records in baseline.items())

    return VerificationCheck(check_id, unchanged)


def _verify_nonexecution(
    erp: ErpAdapter,
    monitored_models: frozenset[str],
    before: dict[str, Any] | None,
) -> tuple[
    VerificationStatus,
    bool | None,
    tuple[VerificationCheckResult, ...],
]:
    check_id = "complete_state_unchanged"
    if before is None:
        return (
            VerificationStatus.VERIFIER_ERROR,
            None,
            (VerificationCheckResult(check_id, None, "check raised an exception"),),
        )
    try:
        unchanged = _snapshot(erp, monitored_models) == before
    except Exception:
        return (
            VerificationStatus.VERIFIER_ERROR,
            None,
            (VerificationCheckResult(check_id, None, "check raised an exception"),),
        )
    return (
        (
            VerificationStatus.NOT_RUN_CLEAN
            if unchanged
            else VerificationStatus.NOT_RUN_DIRTY
        ),
        unchanged,
        (
            VerificationCheckResult(
                check_id, unchanged, "check passed" if unchanged else "check failed"
            ),
        ),
    )


class SystemC:
    def __init__(
        self,
        erp: ErpAdapter,
        runtime: Runtime,
        retriever: TfidfRetriever,
        audit: AuditStore,
        approval: ApprovalService | None = None,
        *,
        monitored_models: set[str] | frozenset[str] | None = None,
        skill_models: dict[str, str] | None = None,
    ) -> None:
        self._erp = erp
        self._runtime = runtime
        self._retriever = retriever
        self._audit = audit
        self._approval = approval
        self._monitored_models = frozenset(
            SKILL_MODELS.values() if monitored_models is None else monitored_models
        )
        self._skill_models = dict(
            SKILL_MODELS if skill_models is None else skill_models
        )

    def handle(
        self,
        correlation_id: str,
        query_text: str,
        proposal: IntentProposal,
        role: str,
        idempotency_key: str,
    ) -> SystemCResult:
        try:
            before = _snapshot(self._erp, self._monitored_models)
        except Exception:
            before = None

        ranked = self._retriever.rank(query_text, role=role)

        # Missing required data is a *clarification* request, not an
        # abstention: the system knows what it needs and can ask for it.
        # Abstention is reserved for "no candidate is trustworthy enough"
        # (CLAUDE.md §17 distinguishes `CLARIFY` from `sin_skill/abstención`).
        if proposal.missing_fields:
            reasons = [f"missing field: {f}" for f in proposal.missing_fields]
            status, met, evidence = _verify_nonexecution(
                self._erp, self._monitored_models, before
            )
            self._audit.record_abstention(
                correlation_id,
                reasons,
                decision="CLARIFY",
                verification_status=status,
                postconditions_met=met,
                check_results=evidence,
            )
            return SystemCResult(
                "CLARIFY", None, None, tuple(reasons), status, met, evidence
            )

        if should_abstain(ranked, proposal.missing_fields):
            reasons = ["no confident candidate"]
            status, met, evidence = _verify_nonexecution(
                self._erp, self._monitored_models, before
            )
            self._audit.record_abstention(
                correlation_id,
                reasons,
                decision="ABSTAIN",
                verification_status=status,
                postconditions_met=met,
                check_results=evidence,
            )
            return SystemCResult(
                "ABSTAIN", None, None, tuple(reasons), status, met, evidence
            )

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

        checks: tuple[VerificationCheck[ErpAdapter], ...]
        if before is None:
            checks = (_error_check("complete_state_snapshot"),)
        elif outcome.decision.value != "ALLOW":
            checks = (
                _state_check(
                    before,
                    self._monitored_models,
                    check_id="complete_state_unchanged",
                ),
            )
        else:
            model = self._skill_models.get(skill.skill_id)
            if model is None or model not in self._monitored_models:
                checks = (_error_check("skill_model_mapping"),)
            else:
                try:
                    checks = build_checks(skill, arguments, before, model=model)
                except Exception:
                    checks = (_error_check("declared_postconditions"),)
                else:
                    if skill.risk_class is RiskClass.R0:
                        checks += (
                            _state_check(
                                before,
                                self._monitored_models,
                                check_id="complete_state_unchanged",
                            ),
                        )
                    else:
                        checks += (
                            _state_check(
                                before,
                                self._monitored_models,
                                check_id="no_cross_model_side_effects",
                                excluded_models=frozenset({model}),
                            ),
                        )

        execution = self._runtime.execute(
            skill,
            arguments,
            role,
            idempotency_key,
            approval_granted=approval_granted,
            postcondition_checks=checks,
            findings=findings,
        )
        self._audit.record(
            correlation_id, skill, role, outcome, execution, idempotency_key
        )

        return SystemCResult(
            execution.decision.value,
            skill.skill_id,
            execution,
            tuple(outcome.reasons),
            execution.verification_status,
            execution.postconditions_met,
            execution.check_results,
        )
