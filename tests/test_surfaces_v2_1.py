"""TDD for erp_agent_os.surfaces_v2_1 (v2.1 plan, Task 4, steps 3-4)."""

from collections import Counter

import pytest

from erp_agent_os.scenarios_v2_1 import CASE_KIND_NO_SKILL, generate_scenarios
from erp_agent_os.surfaces_v2_1 import (
    Surface,
    SurfaceKind,
    SurfaceRejectedError,
    primary_surface_kind,
    render_all,
    render_surface,
    validate_surface,
)


def _main_scenarios():
    return [s for s in generate_scenarios() if s.case_kind != CASE_KIND_NO_SKILL]


def test_all_three_surfaces_render_and_preserve_protected_slots():
    for scenario in _main_scenarios()[:20]:
        for surface in render_all(scenario):
            validate_surface(scenario, surface)  # must not raise


def test_s1_s2_s3_produce_visibly_different_text():
    scenario = _main_scenarios()[0]
    s1, s2, s3 = render_all(scenario)
    texts = {s1.text, s2.text, s3.text}
    assert len(texts) == 3


def test_altering_a_protected_slot_is_rejected():
    scenario = _main_scenarios()[0]
    s1, _, _ = render_all(scenario)
    tampered = Surface(s1.scenario_id, s1.kind, s1.text.replace("Acme", "Wrongco"))
    # Only meaningful when the original slot text actually appears; use a
    # scenario whose customer_name we know is in the template.
    real_value = next(iter(scenario.arguments.values()))
    tampered = Surface(
        s1.scenario_id, s1.kind, s1.text.replace(str(real_value), "TAMPERED")
    )
    with pytest.raises(SurfaceRejectedError):
        validate_surface(scenario, tampered)


def test_leaking_the_skill_id_is_rejected():
    scenario = _main_scenarios()[0]
    s1, _, _ = render_all(scenario)
    leaked = Surface(s1.scenario_id, s1.kind, s1.text + f" ({scenario.expected_skill})")
    with pytest.raises(SurfaceRejectedError):
        validate_surface(scenario, leaked)


def test_leaking_the_expected_decision_word_is_rejected():
    scenario = _main_scenarios()[0]
    s1, _, _ = render_all(scenario)
    leaked = Surface(s1.scenario_id, s1.kind, s1.text + " -> ALLOW")
    with pytest.raises(SurfaceRejectedError):
        validate_surface(scenario, leaked)


def test_near_duplicate_of_v1_or_development_text_is_rejected():
    scenario = _main_scenarios()[0]
    s1, _, _ = render_all(scenario)
    v1_texts = frozenset({s1.text.strip().casefold()})
    with pytest.raises(SurfaceRejectedError):
        validate_surface(scenario, s1, v1_texts=v1_texts)


def test_no_skill_scenarios_render_a_plausible_out_of_catalog_request():
    no_skill = [s for s in generate_scenarios() if s.case_kind == CASE_KIND_NO_SKILL]
    assert no_skill
    for scenario in no_skill:
        for surface in render_all(scenario):
            assert surface.text
            validate_surface(scenario, surface)


def test_primary_surface_rotation_is_balanced_within_one_across_three_slots():
    counts = Counter(
        primary_surface_kind("irrelevant", ordinal) for ordinal in range(5)
    )
    values = list(counts.values())
    assert max(values) - min(values) <= 1


def test_primary_surface_rotation_is_deterministic():
    first = [primary_surface_kind("scn-0001-0", i) for i in range(9)]
    second = [primary_surface_kind("scn-0001-0", i) for i in range(9)]
    assert first == second


def test_render_surface_is_deterministic():
    scenario = _main_scenarios()[0]
    first = render_surface(scenario, SurfaceKind.S2_GRAMMAR)
    second = render_surface(scenario, SurfaceKind.S2_GRAMMAR)
    assert first == second
