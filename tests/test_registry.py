import pytest
from sqlalchemy import create_engine

from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.registry import (
    DuplicateSkillError,
    SqlSkillRegistry,
    UnknownSkillError,
    create_registry_schema,
)
from erp_agent_os.skills import InvalidTransitionError, SkillState

SKILL_ID = "crm.create_opportunity"


@pytest.fixture
def registry():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_registry_schema(engine)
    return SqlSkillRegistry(engine)


def _draft(skill_id=SKILL_ID, version="2.0.0"):
    return CATALOG_BY_ID[SKILL_ID].model_copy(
        update={"skill_id": skill_id, "version": version, "state": SkillState.DRAFT}
    )


def test_register_then_read_back_the_same_definition(registry):
    skill = _draft()
    registry.register(skill, actor="tester")

    stored = registry.get(SKILL_ID, "2.0.0")
    assert stored.skill_id == SKILL_ID
    assert stored.version == "2.0.0"
    assert registry.state_of(SKILL_ID, "2.0.0") is SkillState.DRAFT


def test_registering_the_same_version_twice_is_refused(registry):
    registry.register(_draft())
    with pytest.raises(DuplicateSkillError):
        registry.register(_draft())


def test_unknown_skill_raises_rather_than_returning_none(registry):
    with pytest.raises(UnknownSkillError):
        registry.get(SKILL_ID, "9.9.9")


def test_versions_are_listed_per_skill(registry):
    registry.register(_draft(version="1.5.0"))
    registry.register(_draft(version="2.0.0"))
    assert registry.versions(SKILL_ID) == ["1.5.0", "2.0.0"]


def test_draft_cannot_jump_straight_to_active(registry):
    # §15's central lifecycle rule, enforced here by delegating to
    # skills.transition() rather than reimplementing the graph.
    registry.register(_draft())
    with pytest.raises(InvalidTransitionError):
        registry.activate(SKILL_ID, "2.0.0", actor="tester")
    assert registry.state_of(SKILL_ID, "2.0.0") is SkillState.DRAFT


def test_full_lifecycle_reaches_active_and_is_recorded(registry):
    registry.register(_draft(), actor="author")
    for target in (SkillState.VALIDATED, SkillState.TESTED):
        registry.transition_to(SKILL_ID, "2.0.0", target, actor="ci")
    registry.approve(SKILL_ID, "2.0.0", actor="admin")
    registry.activate(SKILL_ID, "2.0.0", actor="admin")

    assert registry.state_of(SKILL_ID, "2.0.0") is SkillState.ACTIVE

    # The history is what makes the lifecycle auditable: storing only
    # the current state would lose how it got there.
    history = registry.history(SKILL_ID, "2.0.0")
    assert [h["to_state"] for h in history] == [
        "DRAFT",
        "VALIDATED",
        "TESTED",
        "APPROVED",
        "ACTIVE",
    ]
    assert history[0]["actor"] == "author"
    assert history[-1]["actor"] == "admin"


def test_quarantine_is_reachable_from_any_state(registry):
    registry.register(_draft())
    registry.quarantine(SKILL_ID, "2.0.0", actor="oncall", reason="incident 42")

    assert registry.state_of(SKILL_ID, "2.0.0") is SkillState.QUARANTINED
    assert registry.history(SKILL_ID, "2.0.0")[-1]["reason"] == "incident 42"


def test_active_returns_only_active_skills(registry):
    registry.register(_draft(version="2.0.0"))
    registry.register(
        CATALOG_BY_ID[SKILL_ID].model_copy(update={"version": "3.0.0"})
    )  # ACTIVE in the catalog

    active = registry.active()
    assert [s.version for s in active] == ["3.0.0"]


def test_seeding_from_the_catalog_is_idempotent(registry):
    assert registry.seed_from_catalog(CATALOG) == len(CATALOG)
    # Running it again must add nothing rather than fail.
    assert registry.seed_from_catalog(CATALOG) == 0
    assert len(registry.active()) == len(CATALOG)


def test_a_quarantined_skill_disappears_from_active(registry):
    registry.seed_from_catalog(CATALOG)
    registry.quarantine(
        SKILL_ID, CATALOG_BY_ID[SKILL_ID].version, actor="oncall", reason="bad handler"
    )
    active_ids = {s.skill_id for s in registry.active()}
    assert SKILL_ID not in active_ids
