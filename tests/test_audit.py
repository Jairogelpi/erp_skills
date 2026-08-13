from datetime import UTC, datetime

from erp_agent_os.audit import REDACTED, AuditStore
from erp_agent_os.dataset import RiskClass
from erp_agent_os.policy import PolicyDecision, PolicyOutcome
from erp_agent_os.runtime import (
    ExecutionResult,
    VerificationCheckResult,
    VerificationStatus,
)
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState

FIXED_TIME = datetime(2026, 8, 5, tzinfo=UTC)


def skill() -> SkillDefinition:
    return SkillDefinition(
        skill_id="crm.create_opportunity",
        version="1.0.0",
        module="crm",
        operation="create",
        description="Crea una oportunidad.",
        risk_class=RiskClass.R1,
        input_schema={"type": "object"},
        permissions=Permissions(allowed_roles=["sales_user"]),
        preconditions=[],
        execution=Execution(
            handler="erp_agent_os.skills.crm.create_opportunity",
            timeout_seconds=10,
            max_retries=1,
            idempotent=True,
        ),
        postconditions=["exactly_one_new_opportunity"],
        state=SkillState.ACTIVE,
    )


def outcome() -> PolicyOutcome:
    return PolicyOutcome(PolicyDecision.ALLOW, 0.2, ["low risk"])


def execution(output=None, replay=False, met=True) -> ExecutionResult:
    return ExecutionResult(
        PolicyDecision.ALLOW,
        output,
        replay,
        met,
        verification_status=VerificationStatus.PASSED,
        check_results=(VerificationCheckResult("record_exists", True, "check passed"),),
    )


def test_record_appends_and_returns_event():
    store = AuditStore(clock=lambda: FIXED_TIME)
    event = store.record(
        "corr-1", skill(), "sales_user", outcome(), execution("1"), "key-1"
    )

    assert event.correlation_id == "corr-1"
    assert event.decision == "ALLOW"
    assert event.verification_status == "passed"
    assert event.postconditions_met is True
    assert event.check_results == (
        VerificationCheckResult("record_exists", True, "check passed"),
    )
    assert event.recorded_at == FIXED_TIME
    assert store.events() == (event,)


def test_abstention_records_aggregate_and_named_non_sensitive_evidence():
    store = AuditStore(clock=lambda: FIXED_TIME)
    checks = (
        VerificationCheckResult("complete_state_unchanged", False, "check failed"),
    )

    event = store.record_abstention(
        "corr-abstain",
        ["no confident candidate"],
        decision="CLARIFY",
        verification_status=VerificationStatus.NOT_RUN_DIRTY,
        postconditions_met=False,
        check_results=checks,
    )

    assert event.verification_status == "not_run_dirty"
    assert event.decision == "CLARIFY"
    assert event.postconditions_met is False
    assert event.check_results == checks


def test_events_filtered_by_correlation_id():
    store = AuditStore(clock=lambda: FIXED_TIME)
    store.record("corr-1", skill(), "sales_user", outcome(), execution("1"), "key-1")
    store.record("corr-2", skill(), "sales_user", outcome(), execution("2"), "key-2")

    filtered = store.events("corr-1")

    assert len(filtered) == 1
    assert filtered[0].correlation_id == "corr-1"


def test_redaction_masks_configured_keys_in_output():
    store = AuditStore(redact_keys=frozenset({"email"}), clock=lambda: FIXED_TIME)
    store.record(
        "corr-1",
        skill(),
        "sales_user",
        outcome(),
        execution({"name": "Acme", "email": "a@b.com"}),
        "key-1",
    )

    event = store.events()[0]

    assert event.output == {"name": "Acme", "email": REDACTED}


def test_events_return_is_independent_copy():
    store = AuditStore(clock=lambda: FIXED_TIME)
    store.record("corr-1", skill(), "sales_user", outcome(), execution("1"), "key-1")

    returned = list(store.events())
    returned.clear()

    assert len(store.events()) == 1


def test_multiple_records_preserve_append_order():
    store = AuditStore(clock=lambda: FIXED_TIME)
    store.record("corr-1", skill(), "sales_user", outcome(), execution("1"), "key-1")
    store.record("corr-1", skill(), "sales_user", outcome(), execution("2"), "key-2")

    assert [e.output for e in store.events()] == ["1", "2"]
