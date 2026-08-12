from datetime import UTC, datetime, timedelta

from erp_agent_os.approval import Approval
from erp_agent_os.audit import AuditEvent
from erp_agent_os.persistence import (
    SqlApprovalStore,
    SqlAuditStore,
    in_memory_engine,
)
from erp_agent_os.runtime import VerificationCheckResult

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)


def event(correlation_id: str = "corr-1", decision: str = "ALLOW") -> AuditEvent:
    return AuditEvent(
        correlation_id=correlation_id,
        skill_id="crm.create_opportunity",
        skill_version="1.0.0",
        role="erp_user",
        decision=decision,
        risk_score=0.2,
        reasons=("low risk",),
        idempotency_key="key-1",
        idempotent_replay=False,
        postconditions_met=None,
        output="42",
        recorded_at=NOW,
        verification_status="failed",
        check_results=(
            VerificationCheckResult("record_exists", False, "check failed"),
        ),
    )


def test_recorded_event_survives_a_new_store_instance():
    engine = in_memory_engine()
    SqlAuditStore(engine).record(event())

    # A different store object over the same engine still sees the row:
    # the state is in the database, not in the process's memory.
    rows = SqlAuditStore(engine).events()

    assert len(rows) == 1
    assert rows[0]["decision"] == "ALLOW"
    assert rows[0]["verification_status"] == "failed"
    assert rows[0]["postconditions_met"] is None
    assert rows[0]["check_results"] == [
        {
            "check_id": "record_exists",
            "passed": False,
            "detail": "check failed",
        }
    ]


def test_events_filtered_by_correlation_id():
    store = SqlAuditStore(in_memory_engine())
    store.record(event("corr-1"))
    store.record(event("corr-2", decision="DENY"))

    assert len(store.events("corr-1")) == 1
    assert store.events("corr-2")[0]["decision"] == "DENY"


def test_append_order_preserved():
    store = SqlAuditStore(in_memory_engine())
    store.record(event(decision="ALLOW"))
    store.record(event(decision="DENY"))

    assert [r["decision"] for r in store.events()] == ["ALLOW", "DENY"]


def test_audit_store_exposes_no_mutation_or_delete_method():
    public = {name for name in dir(SqlAuditStore) if not name.startswith("_")}
    assert public == {"record", "events"}


def test_approval_valid_before_expiry_and_invalid_after():
    store = SqlApprovalStore(in_memory_engine())
    store.grant(
        Approval(
            "manager1", "crm.update_expected_revenue", NOW, NOW + timedelta(minutes=1)
        )
    )

    assert store.is_valid("crm.update_expected_revenue", now=NOW) is True
    assert (
        store.is_valid("crm.update_expected_revenue", now=NOW + timedelta(minutes=2))
        is False
    )


def test_approval_scope_is_isolated():
    store = SqlApprovalStore(in_memory_engine())
    store.grant(Approval("manager1", "scope-a", NOW, NOW + timedelta(minutes=1)))

    assert store.is_valid("scope-b", now=NOW) is False
