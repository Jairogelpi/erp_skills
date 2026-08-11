"""Traceability rubric (CLAUDE.md §20, docs/traceability-rubric.md).

"La trazabilidad se puntuará con una rúbrica ponderada y auditable, no
por volumen de logs" -- each of the seven weighted components requires
concrete, checkable evidence in the trace; its absence scores zero, no
partial credit for "something was logged". This module is the executable
form of that rubric.

System A and B structurally cannot provide most of this evidence: they
have no policy decision, no skill version, no idempotency key, no audit
trail at all (CLAUDE.md §18 -- that is the documented governance gap,
not an oversight here). Their low score is itself part of what H7 is
supposed to show, not a bug in the scorer.
"""

from dataclasses import dataclass

from erp_agent_os.audit import AuditEvent

WEIGHTS: dict[str, float] = {
    "request_identity": 0.10,
    "interpretation": 0.15,
    "candidate_or_abstention": 0.15,
    "policy_decision": 0.15,
    "skill_version_and_key": 0.15,
    "result_and_effects": 0.15,
    "postcondition_or_block_evidence": 0.15,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


@dataclass(frozen=True)
class TraceabilityScore:
    components: dict[str, bool]

    @property
    def total(self) -> float:
        return sum(
            WEIGHTS[name] for name, present in self.components.items() if present
        )


def score_governed_execution(
    *,
    correlation_id: str,
    has_interpretation: bool,
    ranked_skill_ids: tuple[str, ...],
    abstention_reasons: tuple[str, ...],
    audit_event: AuditEvent | None,
) -> TraceabilityScore:
    """Score one System C execution against the seven rubric components.

    `audit_event` is `None` for CLARIFY/ABSTAIN, which never reach the
    policy engine (CLAUDE.md §17 distinguishes CLARIFY from abstention) --
    components 4-6 require a policy decision, so they score 0 there by
    construction; component 7 credits the abstention reasons instead, per
    the rubric's "o la aprobación/denegación que impidió ejecutar".
    """
    components = {
        "request_identity": bool(correlation_id),
        "interpretation": has_interpretation,
        "candidate_or_abstention": bool(ranked_skill_ids) or bool(abstention_reasons),
        "policy_decision": audit_event is not None and bool(audit_event.decision),
        "skill_version_and_key": (
            audit_event is not None
            and bool(audit_event.skill_version)
            and bool(audit_event.idempotency_key)
        ),
        "result_and_effects": audit_event is not None,
        "postcondition_or_block_evidence": (
            audit_event is not None and audit_event.postconditions_met is not None
        )
        or (audit_event is None and bool(abstention_reasons)),
    }
    return TraceabilityScore(components)


def score_ungoverned_execution(
    *, correlation_id: str, tool_or_skill_id: str | None, output_present: bool
) -> TraceabilityScore:
    """Score a System A/B execution: no policy engine, no audit store.

    Reflects what CLAUDE.md §18 says these baselines lack, not a weaker
    implementation of the same rubric -- components 4, 5 and 7 are
    structurally unavailable to them.
    """
    components = {
        "request_identity": bool(correlation_id),
        "interpretation": False,  # no IntentProposal / missing_fields tracking
        "candidate_or_abstention": bool(tool_or_skill_id),
        "policy_decision": False,  # no policy engine
        "skill_version_and_key": False,  # no versioned skill, no idempotency key
        "result_and_effects": output_present,
        "postcondition_or_block_evidence": False,  # no postcondition check
    }
    return TraceabilityScore(components)
