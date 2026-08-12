from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, inspect, text

import erp_agent_os.persistence as persistence
from erp_agent_os.approval import Approval
from erp_agent_os.audit import AuditEvent, AuditStore
from erp_agent_os.persistence import (
    SqlApprovalStore,
    SqlAuditStore,
    in_memory_engine,
)
from erp_agent_os.runtime import VerificationCheckResult

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)


def legacy_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE audit_events (
                id INTEGER NOT NULL PRIMARY KEY,
                correlation_id VARCHAR(64) NOT NULL,
                skill_id VARCHAR(128) NOT NULL,
                skill_version VARCHAR(32) NOT NULL,
                role VARCHAR(64) NOT NULL,
                decision VARCHAR(32) NOT NULL,
                risk_score FLOAT NOT NULL,
                reasons TEXT NOT NULL,
                idempotency_key VARCHAR(128) NOT NULL,
                idempotent_replay BOOLEAN NOT NULL,
                postconditions_met BOOLEAN,
                output TEXT,
                recorded_at DATETIME NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            "CREATE INDEX ix_audit_events_correlation_id "
            "ON audit_events (correlation_id)"
        )
        connection.execute(
            text(
                """
                INSERT INTO audit_events (
                    id, correlation_id, skill_id, skill_version, role,
                    decision, risk_score, reasons, idempotency_key,
                    idempotent_replay, postconditions_met, output, recorded_at
                ) VALUES (
                    7, 'legacy-corr', 'crm.create_opportunity', '1.0.0',
                    'erp_user', 'ALLOW', 0.2, 'legacy reason', 'legacy-key',
                    0, NULL, 'legacy-output', :recorded_at
                )
                """
            ),
            {"recorded_at": NOW.isoformat()},
        )
    return engine


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


@pytest.mark.parametrize(
    ("decision", "event_type", "status", "met"),
    [
        ("CLARIFY", "clarification", "not_run_clean", True),
        ("ABSTAIN", "abstention", "verifier_error", None),
    ],
)
def test_abstention_and_clarification_evidence_round_trips(
    decision, event_type, status, met
):
    evidence = (
        VerificationCheckResult(
            "complete_state_unchanged",
            met,
            "check passed" if met else "check raised an exception",
        ),
    )
    memory = AuditStore(clock=lambda: NOW)
    event = memory.record_abstention(
        f"corr-{decision.lower()}",
        [f"{decision.lower()} reason"],
        decision=decision,
        verification_status=status,
        postconditions_met=met,
        check_results=evidence,
    )
    store = SqlAuditStore(in_memory_engine())

    store.record(event)
    row = store.events(event.correlation_id)[0]

    assert row["event_type"] == event_type
    assert row["decision"] == decision
    assert row["reasons"] == f"{decision.lower()} reason"
    assert row["verification_status"] == status
    assert row["postconditions_met"] is met
    assert row["check_results"] == [
        {
            "check_id": "complete_state_unchanged",
            "passed": met,
            "detail": "check passed" if met else "check raised an exception",
        }
    ]
    assert row["skill_id"] is None
    assert row["skill_version"] is None
    assert row["role"] is None


def test_legacy_sqlite_schema_migrates_without_data_loss_and_is_idempotent():
    engine = legacy_engine()

    store = SqlAuditStore(engine)
    legacy = store.events("legacy-corr")[0]

    assert legacy["id"] == 7
    assert legacy["event_type"] == "execution"
    assert legacy["verification_status"] == "verifier_error"
    assert legacy["check_results"] == []
    assert legacy["output"] == "legacy-output"
    columns = {
        column["name"]: column
        for column in inspect(engine).get_columns("audit_events")
    }
    assert columns["skill_id"]["nullable"] is True
    assert columns["skill_version"]["nullable"] is True

    store.record(event("new-execution"))
    abstention = AuditStore(clock=lambda: NOW).record_abstention(
        "new-abstention",
        ["no confident candidate"],
        decision="ABSTAIN",
        verification_status="not_run_clean",
        postconditions_met=True,
        check_results=(
            VerificationCheckResult(
                "complete_state_unchanged", True, "check passed"
            ),
        ),
    )
    store.record(abstention)

    persistence.migrate_schema(engine)
    persistence.migrate_schema(engine)

    assert [row["correlation_id"] for row in store.events()] == [
        "legacy-corr",
        "new-execution",
        "new-abstention",
    ]
    with engine.connect() as connection:
        versions = connection.execute(
            text("SELECT version FROM schema_migrations ORDER BY version")
        ).scalars().all()
    assert versions == [persistence.LATEST_SCHEMA_VERSION]


def test_fresh_schema_records_current_migration_version():
    engine = in_memory_engine()

    with engine.connect() as connection:
        versions = connection.execute(
            text("SELECT version FROM schema_migrations ORDER BY version")
        ).scalars().all()

    assert versions == [persistence.LATEST_SCHEMA_VERSION]


def test_postgresql_migration_branch_emits_add_and_nullability_ddl():
    statements = persistence._postgresql_v1_statements(
        {
            "id",
            "correlation_id",
            "skill_id",
            "skill_version",
            "role",
            "decision",
            "risk_score",
            "reasons",
            "idempotency_key",
            "idempotent_replay",
            "postconditions_met",
            "output",
            "recorded_at",
        }
    )
    ddl = "\n".join(statements)

    assert "ADD COLUMN event_type" in ddl
    assert "ADD COLUMN verification_status" in ddl
    assert "ADD COLUMN check_results" in ddl
    assert "ALTER COLUMN skill_id DROP NOT NULL" in ddl
    assert "ALTER COLUMN skill_version DROP NOT NULL" in ddl


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
