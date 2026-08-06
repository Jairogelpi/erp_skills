from datetime import UTC, datetime

from erp_agent_os.audit import AuditEvent
from erp_agent_os.traceability import (
    WEIGHTS,
    score_governed_execution,
    score_ungoverned_execution,
)


def _event(**overrides):
    defaults = dict(
        correlation_id="r0001",
        skill_id="crm.create_opportunity",
        skill_version="1.0.0",
        role="erp_user",
        decision="ALLOW",
        risk_score=0.1,
        reasons=(),
        idempotency_key="key-1",
        idempotent_replay=False,
        postconditions_met=True,
        output={"id": "OPP-1"},
        recorded_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return AuditEvent(**defaults)


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_full_allow_execution_scores_full_marks():
    score = score_governed_execution(
        correlation_id="r0001",
        has_interpretation=True,
        ranked_skill_ids=("crm.create_opportunity",),
        abstention_reasons=(),
        audit_event=_event(),
    )
    assert score.total == 1.0


def test_abstention_gets_no_credit_for_policy_decision_but_scores_component_seven():
    score = score_governed_execution(
        correlation_id="r0001",
        has_interpretation=True,
        ranked_skill_ids=(),
        abstention_reasons=("no confident candidate",),
        audit_event=None,
    )
    assert score.components["policy_decision"] is False
    assert score.components["skill_version_and_key"] is False
    assert score.components["postcondition_or_block_evidence"] is True
    assert score.total == WEIGHTS["request_identity"] + WEIGHTS["interpretation"] + (
        WEIGHTS["candidate_or_abstention"] + WEIGHTS["postcondition_or_block_evidence"]
    )


def test_a_blocked_denied_execution_with_no_evidence_scores_zero_for_that_case():
    score = score_governed_execution(
        correlation_id="",
        has_interpretation=False,
        ranked_skill_ids=(),
        abstention_reasons=(),
        audit_event=None,
    )
    assert score.total == 0.0


def test_ungoverned_system_never_earns_policy_or_postcondition_credit():
    score = score_ungoverned_execution(
        correlation_id="r0001", tool_or_skill_id="create_record", output_present=True
    )
    assert score.components["policy_decision"] is False
    assert score.components["skill_version_and_key"] is False
    assert score.components["postcondition_or_block_evidence"] is False
    # It CAN earn identity, candidate, and result credit -- it is not
    # scored zero everywhere, only where CLAUDE.md §18 says it lacks
    # governance infrastructure.
    assert score.total == (
        WEIGHTS["request_identity"]
        + WEIGHTS["candidate_or_abstention"]
        + WEIGHTS["result_and_effects"]
    )
