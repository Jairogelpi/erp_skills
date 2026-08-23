"""TDD for erp_agent_os.security_scenarios_v2_1 (v2.1 plan, Task 4B)."""

from collections import Counter

import pytest

from erp_agent_os.security_scenarios_v2_1 import (
    H4_ATTACK_CATEGORIES,
    N_SECURITY_DANGEROUS,
    SecurityScenarioError,
    generate_security_population,
)


def test_exactly_84_dangerous_unique_ids_twelve_per_category():
    """Was 96/8 categories; r4_operation retired 2026-08-20
    (docs/results-v2.1.md section 4) -- now 84/7."""
    dangerous, _ = generate_security_population()
    assert len(dangerous) == 84
    ids = [s.scenario_id for s in dangerous]
    assert len(ids) == len(set(ids))
    counts = Counter(s.attack_category for s in dangerous)
    assert set(counts) == set(H4_ATTACK_CATEGORIES)
    assert "r4_operation" not in counts
    for category in H4_ATTACK_CATEGORIES:
        assert counts[category] == 12


def test_84_safe_controls_one_to_one_with_dangerous():
    dangerous, safe = generate_security_population()
    assert len(safe) == len(dangerous) == 84
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
    dangerous, safe = generate_security_population(n_dangerous=105)
    assert len(dangerous) == len(safe) == 105
    counts = Counter(s.attack_category for s in dangerous)
    assert set(counts.values()) == {15}


def test_rejects_a_size_below_the_locked_protocol_minimum():
    with pytest.raises(SecurityScenarioError):
        generate_security_population(n_dangerous=48)


def test_rejects_a_size_that_does_not_divide_evenly_across_categories():
    with pytest.raises(SecurityScenarioError):
        generate_security_population(n_dangerous=100)


def test_locked_minimum_constant_is_84():
    assert N_SECURITY_DANGEROUS == 84


def test_generation_is_deterministic():
    first = generate_security_population()
    second = generate_security_population()
    assert first == second


def test_every_scenario_renders_and_validates_on_all_three_surfaces():
    """Regression: canonical_intent used to be a synthetic
    "security.{skill_id}" label absent from bench_intents.INTENTS_BY_ID,
    so surfaces_v2_1.render_surface KeyError'd on every single security
    scenario the instant anything tried to render one -- caught while
    wiring Task 8, not by any test the generator shipped with. Separately,
    four categories used to smuggle a synthetic boolean marker key into
    `arguments` that could never survive into rendered text, tripping
    validate_surface's own protected-slot check. Both are fixed; this
    locks the property in for the whole population, not just one sample."""
    from erp_agent_os.surfaces_v2_1 import SurfaceKind, render_surface, validate_surface

    dangerous, safe = generate_security_population()
    for scenario in dangerous + safe:
        for kind in SurfaceKind:
            surface = render_surface(scenario, kind)
            validate_surface(scenario, surface)


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
