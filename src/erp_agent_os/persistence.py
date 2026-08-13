"""Durable audit and approval storage (roadmap P6.2).

Scope per CLAUDE.md §14 (Audit Store: "eventos append-only y resúmenes
consultables") and §27 (SQLAlchemy 2 / PostgreSQL): the same append-only
contract as the in-memory `AuditStore`, backed by a relational database.

Engine-agnostic SQLAlchemy Core — the test suite and CI run it against
in-memory SQLite (no service dependency); `docker-compose` supplies
PostgreSQL for a realistic deployment. Vector storage via pgvector is
**not** used: retrieval currently embeds in-process
(`retrieval.py`/`embeddings.py`) over a 12-skill catalog, so a vector
index would be unused infrastructure. That remains open work if the
catalog ever grows past in-process ranking.

Append-only is enforced the same way as in memory: no update or delete
method exists on the public surface.
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
    inspect,
    select,
)
from sqlalchemy.engine import Connection, Engine

from erp_agent_os.approval import Approval
from erp_agent_os.audit import AbstentionEvent, AuditEvent

metadata = MetaData()
LATEST_SCHEMA_VERSION = 1

schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("version", Integer, primary_key=True),
    Column("applied_at", DateTime(timezone=True), nullable=False),
)

audit_events = Table(
    "audit_events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("correlation_id", String(64), nullable=False, index=True),
    Column(
        "event_type",
        String(32),
        nullable=False,
        default="execution",
        server_default="execution",
    ),
    Column("skill_id", String(128), nullable=True),
    Column("skill_version", String(32), nullable=True),
    Column("role", String(64), nullable=True),
    Column("decision", String(32), nullable=False),
    Column("risk_score", Float, nullable=True),
    Column("reasons", Text, nullable=False),
    Column("idempotency_key", String(128), nullable=True),
    Column("idempotent_replay", Boolean, nullable=True),
    Column("postconditions_met", Boolean, nullable=True),
    Column(
        "verification_status",
        String(32),
        nullable=False,
        default="verifier_error",
        server_default="verifier_error",
    ),
    Column("check_results", Text, nullable=False, default="[]", server_default="[]"),
    Column("output", Text, nullable=True),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
)

approvals = Table(
    "approvals",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("actor", String(64), nullable=False),
    Column("scope", String(128), nullable=False, index=True),
    Column("granted_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)


def _sqlite_migrate_v1(connection: Connection, columns: set[str]) -> None:
    event_type = "event_type" if "event_type" in columns else "'execution'"
    verification_status = (
        "verification_status"
        if "verification_status" in columns
        else "'verifier_error'"
    )
    check_results = "check_results" if "check_results" in columns else "'[]'"
    connection.exec_driver_sql(
        """
        CREATE TABLE audit_events_migration_v1 (
            id INTEGER NOT NULL PRIMARY KEY,
            correlation_id VARCHAR(64) NOT NULL,
            event_type VARCHAR(32) NOT NULL DEFAULT 'execution',
            skill_id VARCHAR(128),
            skill_version VARCHAR(32),
            role VARCHAR(64),
            decision VARCHAR(32) NOT NULL,
            risk_score FLOAT,
            reasons TEXT NOT NULL,
            idempotency_key VARCHAR(128),
            idempotent_replay BOOLEAN,
            postconditions_met BOOLEAN,
            verification_status VARCHAR(32) NOT NULL DEFAULT 'verifier_error',
            check_results TEXT NOT NULL DEFAULT '[]',
            output TEXT,
            recorded_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        f"""
        INSERT INTO audit_events_migration_v1 (
            id, correlation_id, event_type, skill_id, skill_version, role,
            decision, risk_score, reasons, idempotency_key, idempotent_replay,
            postconditions_met, verification_status, check_results, output,
            recorded_at
        )
        SELECT
            id, correlation_id, {event_type}, skill_id, skill_version, role,
            decision, risk_score, reasons, idempotency_key, idempotent_replay,
            postconditions_met, {verification_status}, {check_results}, output,
            recorded_at
        FROM audit_events
        """
    )
    connection.exec_driver_sql("DROP TABLE audit_events")
    connection.exec_driver_sql(
        "ALTER TABLE audit_events_migration_v1 RENAME TO audit_events"
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_audit_events_correlation_id ON audit_events (correlation_id)"
    )


def _postgresql_v1_statements(columns: set[str]) -> tuple[str, ...]:
    statements: list[str] = []
    additions = {
        "event_type": (
            "ALTER TABLE audit_events ADD COLUMN event_type "
            "VARCHAR(32) NOT NULL DEFAULT 'execution'"
        ),
        "verification_status": (
            "ALTER TABLE audit_events ADD COLUMN verification_status "
            "VARCHAR(32) NOT NULL DEFAULT 'verifier_error'"
        ),
        "check_results": (
            "ALTER TABLE audit_events ADD COLUMN check_results "
            "TEXT NOT NULL DEFAULT '[]'"
        ),
    }
    statements.extend(
        statement for name, statement in additions.items() if name not in columns
    )
    statements.extend(
        f"ALTER TABLE audit_events ALTER COLUMN {name} DROP NOT NULL"
        for name in (
            "skill_id",
            "skill_version",
            "role",
            "risk_score",
            "idempotency_key",
            "idempotent_replay",
        )
    )
    return tuple(statements)


def _audit_schema_is_current(connection: Connection) -> bool:
    columns = {
        column["name"]: column
        for column in inspect(connection).get_columns("audit_events")
    }
    nullable_for_nonexecution = (
        "skill_id",
        "skill_version",
        "role",
        "risk_score",
        "idempotency_key",
        "idempotent_replay",
    )
    return {
        "event_type",
        "verification_status",
        "check_results",
    } <= columns.keys() and all(
        columns[name]["nullable"] is not False for name in nullable_for_nonexecution
    )


def migrate_schema(engine: Engine) -> None:
    """Upgrade the audit schema transactionally and record version 1."""
    metadata.create_all(engine)
    with engine.begin() as connection:
        versions = set(
            connection.execute(select(schema_migrations.c.version)).scalars()
        )
        if LATEST_SCHEMA_VERSION in versions:
            return

        columns = {
            column["name"] for column in inspect(connection).get_columns("audit_events")
        }
        if not _audit_schema_is_current(connection):
            dialect = connection.dialect.name
            if dialect == "sqlite":
                _sqlite_migrate_v1(connection, columns)
            elif dialect == "postgresql":
                for statement in _postgresql_v1_statements(columns):
                    connection.exec_driver_sql(statement)
            else:
                raise RuntimeError(f"unsupported audit migration dialect: {dialect}")

        connection.execute(
            insert(schema_migrations).values(
                version=LATEST_SCHEMA_VERSION, applied_at=datetime.now(UTC)
            )
        )


def create_schema(engine: Engine) -> None:
    migrate_schema(engine)


def in_memory_engine() -> Engine:
    """SQLite engine for tests/CI — no external service required."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_schema(engine)
    return engine


class SqlAuditStore:
    """Append-only audit persistence. No update/delete on the public surface."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        migrate_schema(engine)

    def record(self, event: AuditEvent | AbstentionEvent) -> None:
        check_results = json.dumps(
            [
                {
                    "check_id": check.check_id,
                    "passed": check.passed,
                    "detail": check.detail,
                }
                for check in event.check_results
            ],
            ensure_ascii=False,
            sort_keys=True,
        )
        if isinstance(event, AuditEvent):
            values = {
                "correlation_id": event.correlation_id,
                "event_type": "execution",
                "skill_id": event.skill_id,
                "skill_version": event.skill_version,
                "role": event.role,
                "decision": event.decision,
                "risk_score": event.risk_score,
                "reasons": "\n".join(event.reasons),
                "idempotency_key": event.idempotency_key,
                "idempotent_replay": event.idempotent_replay,
                "postconditions_met": event.postconditions_met,
                "verification_status": event.verification_status,
                "check_results": check_results,
                "output": None if event.output is None else str(event.output),
                "recorded_at": event.recorded_at,
            }
        else:
            values = {
                "correlation_id": event.correlation_id,
                "event_type": (
                    "clarification" if event.decision == "CLARIFY" else "abstention"
                ),
                "skill_id": None,
                "skill_version": None,
                "role": None,
                "decision": event.decision,
                "risk_score": None,
                "reasons": "\n".join(event.reasons),
                "idempotency_key": None,
                "idempotent_replay": None,
                "postconditions_met": event.postconditions_met,
                "verification_status": event.verification_status,
                "check_results": check_results,
                "output": None,
                "recorded_at": event.recorded_at,
            }
        with self._engine.begin() as conn:
            conn.execute(insert(audit_events).values(**values))

    def events(self, correlation_id: str | None = None) -> Sequence[dict[str, Any]]:
        stmt = select(audit_events).order_by(audit_events.c.id)
        if correlation_id is not None:
            stmt = stmt.where(audit_events.c.correlation_id == correlation_id)
        with self._engine.connect() as conn:
            rows = [dict(row._mapping) for row in conn.execute(stmt)]
        for row in rows:
            row["check_results"] = json.loads(row["check_results"])
        return rows


class SqlApprovalStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def grant(self, approval: Approval) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                insert(approvals).values(
                    actor=approval.actor,
                    scope=approval.scope,
                    granted_at=approval.granted_at,
                    expires_at=approval.expires_at,
                )
            )

    def is_valid(self, scope: str, *, now: datetime | None = None) -> bool:
        moment = now or datetime.now(UTC)
        stmt = select(approvals).where(approvals.c.scope == scope)
        with self._engine.connect() as conn:
            for row in conn.execute(stmt):
                granted_at = row.granted_at
                expires_at = row.expires_at
                # SQLite returns naive datetimes; normalize before comparing.
                if granted_at.tzinfo is None:
                    granted_at = granted_at.replace(tzinfo=UTC)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if granted_at <= moment < expires_at:
                    return True
        return False
