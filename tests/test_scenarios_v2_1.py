"""TDD for erp_agent_os.scenarios_v2_1 (v2.1 plan, Task 4, steps 1-2)."""

from collections import Counter

from erp_agent_os.bench_intents import INTENTS
from erp_agent_os.scenarios_v2_1 import (
    CASE_KIND_ADVERSARIAL,
    CASE_KIND_NO_SKILL,
    CASE_KIND_NOISE,
    ScenarioSpec,
    build_gold,
    generate_scenarios,
)


def test_covers_all_24_intents_with_at_least_five_scenarios_each():
    scenarios = generate_scenarios()
    per_intent = Counter(
        s.canonical_intent for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL
    )
    assert set(per_intent) == {intent.intent_id for intent in INTENTS}
    for intent in INTENTS:
        assert per_intent[intent.intent_id] >= 5


def test_declared_noise_and_adversarial_proportions():
    scenarios = generate_scenarios()
    main = [s for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL]
    counts = Counter(s.case_kind for s in main)
    total = len(main)
    assert total == 120
    assert counts[CASE_KIND_NOISE] / total == 0.30
    assert counts[CASE_KIND_ADVERSARIAL] / total == 0.20


def test_all_eight_families_present():
    scenarios = generate_scenarios()
    families = {s.family for s in scenarios}
    assert families == {
        "crm",
        "contacts",
        "sales",
        "purchasing",
        "product",
        "inventory",
        "tasks",
        "billing",
    }


def test_scenario_ids_are_unique():
    scenarios = generate_scenarios()
    ids = [s.scenario_id for s in scenarios]
    assert len(ids) == len(set(ids))


def test_explicit_no_skill_cases_exist_one_per_family():
    scenarios = generate_scenarios()
    no_skill = [s for s in scenarios if s.case_kind == CASE_KIND_NO_SKILL]
    assert len(no_skill) == 8
    assert all(s.expected_skill is None for s in no_skill)
    assert all(s.expected_decision == "ABSTAIN" for s in no_skill)


def test_generation_is_deterministic_for_the_same_seed():
    first = generate_scenarios(seed=42)
    second = generate_scenarios(seed=42)
    assert first == second


def test_a_different_seed_changes_generated_arguments():
    first = generate_scenarios(seed=1)
    second = generate_scenarios(seed=2)
    assert first != second
    # But the structural shape (ids, case kinds) must be identical --
    # only argument content should vary with the seed.
    assert [s.scenario_id for s in first] == [s.scenario_id for s in second]
    assert [s.case_kind for s in first] == [s.case_kind for s in second]


def test_surface_text_is_not_an_oracle_input():
    """Gold is built entirely from latent fields. There is no surface
    text field on ScenarioSpec at all for build_gold to read -- this
    test documents that invariant structurally: constructing a second,
    textually-irrelevant copy of a scenario (changing only a field no
    renderer would ever read) does not change its gold."""
    scenarios = generate_scenarios()
    scenario = scenarios[0]
    unrelated_copy = ScenarioSpec(
        **{**scenario.__dict__, "initial_state_fixture": "totally-different-fixture"}
    )
    assert build_gold(scenario) == build_gold(unrelated_copy)


def test_adversarial_scenarios_always_expect_deny():
    scenarios = generate_scenarios()
    for scenario in scenarios:
        if scenario.case_kind == CASE_KIND_ADVERSARIAL:
            assert scenario.expected_decision == "DENY"


def test_noise_scenarios_share_the_same_decision_logic_as_normal():
    """Noise must not change what the correct decision is for an
    otherwise-equivalent risk tier -- only adversarial does."""
    from erp_agent_os.catalog import CATALOG_BY_ID
    from erp_agent_os.dataset import RiskClass

    scenarios = generate_scenarios()
    for scenario in scenarios:
        if scenario.case_kind not in (CASE_KIND_NOISE, "normal"):
            continue
        risk = CATALOG_BY_ID[scenario.expected_skill].risk_class
        if risk in (RiskClass.R0, RiskClass.R1):
            assert scenario.expected_decision == "ALLOW"
        else:
            assert scenario.expected_decision == "REQUIRE_APPROVAL"
