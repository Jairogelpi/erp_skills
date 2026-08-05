from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID, FAMILIES
from erp_agent_os.dataset import RiskClass
from erp_agent_os.skills import SkillState


def test_catalog_has_exactly_twelve_skills():
    assert len(CATALOG) == 12
    assert len(CATALOG_BY_ID) == 12


def test_catalog_covers_all_eight_families():
    assert len(FAMILIES) == 8
    assert {skill.module for skill in CATALOG} == set(FAMILIES)


def test_no_skill_is_r4():
    assert all(skill.risk_class is not RiskClass.R4 for skill in CATALOG)


def test_all_skills_are_active():
    assert all(skill.state is SkillState.ACTIVE for skill in CATALOG)


def test_skill_ids_are_unique():
    ids = [skill.skill_id for skill in CATALOG]
    assert len(ids) == len(set(ids))
