"""Persistent, versioned skill registry (RF-03, CLAUDE.md §14/§15).

RF-03 requires registering, querying, versioning, approving, activating,
deprecating and quarantining skills. `skills.py` already defines the
lifecycle and its legal transitions; `catalog.py` holds the frozen
twelve as a Python list. What was missing is the thing RF-03 actually
asks for: a **registry** where a skill's state can change at runtime and
survive a restart.

Design notes:

- **The lifecycle is not re-implemented here.** Transitions go through
  `skills.transition()`, so the rule that `DRAFT` cannot jump straight
  to `ACTIVE` (and that `QUARANTINED` is reachable from anywhere) has
  exactly one definition.
- **Every transition is recorded, not just the current state.** §15's
  lifecycle is auditable only if you can see how a skill got where it
  is; storing just `state` would lose that. The history table is
  append-only, like the audit store.
- **The frozen catalog is unaffected.** Seeding a registry from
  `CATALOG` is opt-in (`seed_from_catalog`); the confirmatory
  experiment keeps using the immutable list, so §19's freeze is not
  touched by anything here.
- Engine-agnostic SQLAlchemy Core against SQLite in tests and CI, per
  the same reasoning as `persistence.py`.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

from erp_agent_os.skills import SkillDefinition, SkillState, transition

metadata = MetaData()

registered_skills = Table(
    "registered_skills",
    metadata,
    Column("skill_id", String(128), primary_key=True),
    Column("version", String(32), primary_key=True),
    Column("state", String(32), nullable=False),
    Column("definition", Text, nullable=False),
    Column("registered_at", DateTime(timezone=True), nullable=False),
)

# Append-only: how each skill reached its current state.
skill_transitions = Table(
    "skill_transitions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("skill_id", String(128), nullable=False),
    Column("version", String(32), nullable=False),
    Column("from_state", String(32), nullable=False),
    Column("to_state", String(32), nullable=False),
    Column("actor", String(128), nullable=False),
    Column("reason", Text, nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
)


class UnknownSkillError(KeyError):
    """Raised when an operation targets a skill/version never registered."""


class DuplicateSkillError(ValueError):
    """Raised when registering a (skill_id, version) that already exists."""


def create_registry_schema(engine: Engine) -> None:
    metadata.create_all(engine)


class SqlSkillRegistry:
    """Skills, their versions, their state, and how they got there."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # --- registration -------------------------------------------------

    def register(
        self, skill: SkillDefinition, *, actor: str = "system"
    ) -> SkillDefinition:
        """Register a new (skill_id, version).

        A skill always enters at the state its definition declares; the
        contract itself forbids nothing here, but `activate()` will
        refuse an illegal jump because it goes through
        `skills.transition()`.
        """
        if self._row(skill.skill_id, skill.version) is not None:
            raise DuplicateSkillError(f"{skill.skill_id}@{skill.version}")
        now = datetime.now(UTC)
        with self._engine.begin() as connection:
            connection.execute(
                insert(registered_skills).values(
                    skill_id=skill.skill_id,
                    version=skill.version,
                    state=skill.state.value,
                    definition=skill.model_dump_json(),
                    registered_at=now,
                )
            )
            connection.execute(
                insert(skill_transitions).values(
                    skill_id=skill.skill_id,
                    version=skill.version,
                    from_state="",
                    to_state=skill.state.value,
                    actor=actor,
                    reason="registered",
                    recorded_at=now,
                )
            )
        return skill

    def seed_from_catalog(
        self, skills: Sequence[SkillDefinition], *, actor: str = "system"
    ) -> int:
        """Load an existing catalog, skipping versions already present."""
        loaded = 0
        for skill in skills:
            if self._row(skill.skill_id, skill.version) is None:
                self.register(skill, actor=actor)
                loaded += 1
        return loaded

    # --- querying -----------------------------------------------------

    def get(self, skill_id: str, version: str) -> SkillDefinition:
        row = self._row(skill_id, version)
        if row is None:
            raise UnknownSkillError(f"{skill_id}@{version}")
        return SkillDefinition.model_validate_json(row.definition)

    def state_of(self, skill_id: str, version: str) -> SkillState:
        row = self._row(skill_id, version)
        if row is None:
            raise UnknownSkillError(f"{skill_id}@{version}")
        return SkillState(row.state)

    def versions(self, skill_id: str) -> list[str]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(registered_skills.c.version).where(
                    registered_skills.c.skill_id == skill_id
                )
            ).all()
        return sorted(row.version for row in rows)

    def active(self) -> list[SkillDefinition]:
        """Only ACTIVE skills -- what a runtime should ever execute."""
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(registered_skills.c.definition).where(
                    registered_skills.c.state == SkillState.ACTIVE.value
                )
            ).all()
        return [SkillDefinition.model_validate_json(row.definition) for row in rows]

    def history(self, skill_id: str, version: str) -> list[dict[str, Any]]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(skill_transitions)
                .where(skill_transitions.c.skill_id == skill_id)
                .where(skill_transitions.c.version == version)
                .order_by(skill_transitions.c.id)
            ).all()
        return [
            {
                "from_state": row.from_state,
                "to_state": row.to_state,
                "actor": row.actor,
                "reason": row.reason,
                "recorded_at": row.recorded_at,
            }
            for row in rows
        ]

    # --- lifecycle ----------------------------------------------------

    def transition_to(
        self,
        skill_id: str,
        version: str,
        target: SkillState,
        *,
        actor: str,
        reason: str = "",
    ) -> SkillState:
        """Move a skill's state, refusing illegal transitions.

        Legality is decided by `skills.transition()` -- the single
        definition of the §15 lifecycle -- so this cannot drift from the
        contract or from the property tests that pin it.
        """
        current = self.state_of(skill_id, version)
        new_state = transition(current, target)  # raises on an illegal move
        with self._engine.begin() as connection:
            connection.execute(
                update(registered_skills)
                .where(registered_skills.c.skill_id == skill_id)
                .where(registered_skills.c.version == version)
                .values(state=new_state.value)
            )
            connection.execute(
                insert(skill_transitions).values(
                    skill_id=skill_id,
                    version=version,
                    from_state=current.value,
                    to_state=new_state.value,
                    actor=actor,
                    reason=reason,
                    recorded_at=datetime.now(UTC),
                )
            )
        return new_state

    def approve(self, skill_id: str, version: str, *, actor: str) -> SkillState:
        return self.transition_to(
            skill_id, version, SkillState.APPROVED, actor=actor, reason="approved"
        )

    def activate(self, skill_id: str, version: str, *, actor: str) -> SkillState:
        return self.transition_to(
            skill_id, version, SkillState.ACTIVE, actor=actor, reason="activated"
        )

    def deprecate(self, skill_id: str, version: str, *, actor: str) -> SkillState:
        return self.transition_to(
            skill_id, version, SkillState.DEPRECATED, actor=actor, reason="deprecated"
        )

    def quarantine(
        self, skill_id: str, version: str, *, actor: str, reason: str
    ) -> SkillState:
        """Reachable from any state (§15) -- the emergency stop."""
        return self.transition_to(
            skill_id, version, SkillState.QUARANTINED, actor=actor, reason=reason
        )

    # --- internals ----------------------------------------------------

    def _row(self, skill_id: str, version: str) -> Any:
        with self._engine.begin() as connection:
            return connection.execute(
                select(registered_skills)
                .where(registered_skills.c.skill_id == skill_id)
                .where(registered_skills.c.version == version)
            ).first()
