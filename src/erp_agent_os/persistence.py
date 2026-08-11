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
    select,
)
from sqlalchemy.engine import Engine

from erp_agent_os.approval import Approval
from erp_agent_os.audit import AuditEvent

metadata = MetaData()

audit_events = Table(
    "audit_events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("correlation_id", String(64), nullable=False, index=True),
    Column("skill_id", String(128), nullable=False),
    Column("skill_version", String(32), nullable=False),
    Column("role", String(64), nullable=False),
    Column("decision", String(32), nullable=False),
    Column("risk_score", Float, nullable=False),
    Column("reasons", Text, nullable=False),
    Column("idempotency_key", String(128), nullable=False),
    Column("idempotent_replay", Boolean, nullable=False),
    Column("postconditions_met", Boolean, nullable=True),
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


def create_schema(engine: Engine) -> None:
    metadata.create_all(engine)


def in_memory_engine() -> Engine:
    """SQLite engine for tests/CI — no external service required."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_schema(engine)
    return engine


class SqlAuditStore:
    """Append-only audit persistence. No update/delete on the public surface."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record(self, event: AuditEvent) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                insert(audit_events).values(
                    correlation_id=event.correlation_id,
                    skill_id=event.skill_id,
                    skill_version=event.skill_version,
                    role=event.role,
                    decision=event.decision,
                    risk_score=event.risk_score,
                    reasons="\n".join(event.reasons),
                    idempotency_key=event.idempotency_key,
                    idempotent_replay=event.idempotent_replay,
                    postconditions_met=event.postconditions_met,
                    output=None if event.output is None else str(event.output),
                    recorded_at=event.recorded_at,
                )
            )

    def events(self, correlation_id: str | None = None) -> Sequence[dict[str, Any]]:
        stmt = select(audit_events).order_by(audit_events.c.id)
        if correlation_id is not None:
            stmt = stmt.where(audit_events.c.correlation_id == correlation_id)
        with self._engine.connect() as conn:
            return [dict(row._mapping) for row in conn.execute(stmt)]


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
