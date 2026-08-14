"""TDD for erp_agent_os.security_scenarios_v2_1 (v2.1 plan, Task 4B)."""

from collections import Counter

import pytest

from erp_agent_os.scenarios_v2_1 import ATTACK_CATEGORIES
from erp_agent_os.security_scenarios_v2_1 import (
    N_SECURITY_DANGEROUS,
    SecurityScenarioError,
    generate_security_population,
)


def test_exactly_96_dangerous_unique_ids_twelve_per_category():
    dangerous, _ = generate_security_population()
    assert len(dangerous) == 96
    ids = [s.scenario_id for s in dangerous]
    assert len(ids) == len(set(ids))
    counts = Counter(s.attack_category for s in dangerous)
    assert set(counts) == set(ATTACK_CATEGORIES)
    for category in ATTACK_CATEGORIES:
        assert counts[category] == 12


def test_96_safe_controls_one_to_one_with_dangerous():
    dangerous, safe = generate_security_population()
    assert len(safe) == len(dangerous) == 96
    dangerous_pairs = {s.scenario_id.removesuffix("-dangerous") for s in dangerous}
    safe_pairs = {s.scenario_id.removesuffix("-safe") for s in safe}
    assert dangerous_pairs == safe_pairs


def test_pairs_match_module_operation_and_differ_only_in_danger():
    dangerous, safe = generate_security_population()
    for d, s in zip(dangerous, safe, strict=True):
        assert d.family == s.family
        assert d.expected_skill == s.expected_skill
        assert d.operation == s.operation
        assert d.expected_decision == "DENY"
        assert s.expected_decision != "DENY"


def test_all_twelve_catalog_skills_appear_in_every_category():
    from erp_agent_os.catalog import CATALOG

    dangerous, _ = generate_security_population()
    by_category: dict[str, set[str]] = {}
    for scenario in dangerous:
        by_category.setdefault(scenario.attack_category, set()).add(
            scenario.expected_skill
        )
    all_skill_ids = {s.skill_id for s in CATALOG}
    for category, skills_seen in by_category.items():
        assert skills_seen == all_skill_ids, category


def test_safe_controls_never_counted_as_dangerous():
    dangerous, safe = generate_security_population()
    dangerous_ids = {s.scenario_id for s in dangerous}
    safe_ids = {s.scenario_id for s in safe}
    assert dangerous_ids.isdisjoint(safe_ids)
    assert all(s.case_kind != "adversarial" for s in safe)


def test_larger_power_selected_size_distributes_evenly():
    dangerous, safe = generate_security_population(n_dangerous=120)
    assert len(dangerous) == len(safe) == 120
    counts = Counter(s.attack_category for s in dangerous)
    assert set(counts.values()) == {15}


def test_rejects_a_size_below_the_locked_protocol_minimum():
    with pytest.raises(SecurityScenarioError):
        generate_security_population(n_dangerous=48)


def test_rejects_a_size_that_does_not_divide_evenly_across_categories():
    with pytest.raises(SecurityScenarioError):
        generate_security_population(n_dangerous=100)


def test_locked_minimum_constant_is_96():
    assert N_SECURITY_DANGEROUS == 96


def test_generation_is_deterministic():
    first = generate_security_population()
    second = generate_security_population()
    assert first == second


def test_safe_control_role_is_actually_permitted_by_the_real_frozen_catalog():
    """Same regression as scenarios_v2_1's own: a safe control's role must
    be one the real catalog actually grants, or it would DENY on role
    mismatch alone and never reach the risk-based decision it is meant
    to exercise. Dangerous rows are exempt -- for insufficient_permissions
    an unauthorized role is exactly the attack being modeled, and every
    other category's dangerous row is expected to DENY regardless."""
    from erp_agent_os.catalog import CATALOG_BY_ID

    _, safe = generate_security_population()
    for scenario in safe:
        allowed = CATALOG_BY_ID[scenario.expected_skill].permissions.allowed_roles
        assert scenario.actor_role in allowed
