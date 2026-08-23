"""TDD for erp_agent_os.scenarios_v2_1 (v2.1 plan, Task 4, steps 1-2)."""

from collections import Counter

import pytest

from erp_agent_os.bench_intents import INTENTS
from erp_agent_os.scenarios_v2_1 import (
    ATTACK_CATEGORIES,
    CASE_KIND_ADVERSARIAL,
    CASE_KIND_NO_SKILL,
    CASE_KIND_NOISE,
    CASE_KIND_NORMAL,
    ScenarioGenerationError,
    ScenarioSpec,
    build_gold,
    generate_scenarios,
    select_h3b_stratified_sample,
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


def test_actor_role_is_actually_permitted_by_the_real_frozen_catalog():
    """Regression: an earlier version hardcoded actor_role="sales_user",
    a role the reference_policy_oracle's own (deliberately independent)
    role-capability table accepts but the REAL, frozen 12-skill catalog
    (catalog.CATALOG, allowed_roles=["erp_user"] only) does not. Every
    "normal"/"noise" scenario would have DENYed on role mismatch alone
    the moment it ran through the real policy.decide(), regardless of
    its intended risk-based outcome -- and the oracle concordance test
    could not have caught it, because that oracle deliberately never
    reads this catalog. Only insufficient_permissions is exempt: an
    unauthorized role is exactly the point of that category."""
    from erp_agent_os.catalog import CATALOG_BY_ID

    scenarios = generate_scenarios()
    for scenario in scenarios:
        if scenario.expected_skill is None:
            continue
        allowed = CATALOG_BY_ID[scenario.expected_skill].permissions.allowed_roles
        if scenario.attack_category == "insufficient_permissions":
            assert scenario.actor_role not in allowed
        else:
            assert scenario.actor_role in allowed


# --------------------------------------------- H3b stratified sample (6.4)


def test_h3b_sample_returns_exactly_the_requested_size():
    scenarios = generate_scenarios()
    sample = select_h3b_stratified_sample(scenarios, sample_size=60)
    assert len(sample) == 60


def test_h3b_sample_has_no_duplicates():
    scenarios = generate_scenarios()
    sample = select_h3b_stratified_sample(scenarios, sample_size=60)
    ids = [s.scenario_id for s in sample]
    assert len(ids) == len(set(ids))


def test_h3b_sample_excludes_no_skill_scenarios():
    scenarios = generate_scenarios()
    sample = select_h3b_stratified_sample(scenarios, sample_size=60)
    assert all(s.case_kind != CASE_KIND_NO_SKILL for s in sample)


def test_h3b_sample_is_deterministic_given_the_same_seed():
    scenarios = generate_scenarios()
    first = select_h3b_stratified_sample(scenarios, sample_size=60, seed=42)
    second = select_h3b_stratified_sample(scenarios, sample_size=60, seed=42)
    assert [s.scenario_id for s in first] == [s.scenario_id for s in second]


def test_h3b_sample_differs_with_a_different_seed():
    scenarios = generate_scenarios()
    first = select_h3b_stratified_sample(scenarios, sample_size=60, seed=1)
    second = select_h3b_stratified_sample(scenarios, sample_size=60, seed=2)
    assert [s.scenario_id for s in first] != [s.scenario_id for s in second]


def test_h3b_sample_rejects_a_size_larger_than_the_eligible_corpus():
    scenarios = generate_scenarios()
    eligible = [s for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL]
    with pytest.raises(ScenarioGenerationError):
        select_h3b_stratified_sample(scenarios, sample_size=len(eligible) + 1)


def test_h3b_sample_composition_roughly_mirrors_the_full_corpus_risk_distribution():
    """Stratified, not haphazard: the sample's risk_class proportions
    should stay close to the eligible corpus's own -- not exact (60 is
    small and rounds), but no risk tier should be silently dropped that
    the corpus itself has a meaningful share of."""
    scenarios = generate_scenarios()
    eligible = [s for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL]
    sample = select_h3b_stratified_sample(scenarios, sample_size=60)

    corpus_risk_classes = {s.risk_class for s in eligible}
    sample_risk_classes = {s.risk_class for s in sample}
    # Every risk class present in the corpus with a non-trivial share
    # (at least 60/len(eligible) of it, i.e. large enough to expect >=1
    # in a proportional sample of 60) must appear in the sample.
    threshold = 60 / len(eligible)
    for risk_class in corpus_risk_classes:
        share = sum(1 for s in eligible if s.risk_class == risk_class) / len(eligible)
        if share >= threshold:
            assert risk_class in sample_risk_classes


def test_h3b_sample_at_full_eligible_size_returns_everything():
    scenarios = generate_scenarios()
    eligible = [s for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL]
    sample = select_h3b_stratified_sample(scenarios, sample_size=len(eligible))
    assert len(sample) == len(eligible)
    assert {s.scenario_id for s in sample} == {s.scenario_id for s in eligible}


# ------------------------------------- n_main scaling (section 6.1)


def test_generate_scenarios_rejects_n_main_below_the_declared_floor():
    with pytest.raises(ScenarioGenerationError):
        generate_scenarios(n_main=119)


def test_generate_scenarios_accepts_the_floor_exactly():
    scenarios = generate_scenarios(n_main=120)
    main = [s for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL]
    assert len(main) == 120


@pytest.mark.parametrize("n_main", [120, 240, 792, 1184])
def test_generate_scenarios_produces_exactly_n_main_main_scenarios(n_main):
    scenarios = generate_scenarios(n_main=n_main)
    main = [s for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL]
    assert len(main) == n_main


@pytest.mark.parametrize("n_main", [120, 792, 1184])
def test_generate_scenarios_hits_the_exact_declared_split_at_any_scale(n_main):
    scenarios = generate_scenarios(n_main=n_main)
    main = [s for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL]
    counts = Counter(s.case_kind for s in main)
    assert counts[CASE_KIND_NOISE] == round(n_main * 0.30)
    assert counts[CASE_KIND_ADVERSARIAL] == round(n_main * 0.20)
    assert (
        counts[CASE_KIND_NORMAL]
        == n_main - counts[CASE_KIND_NOISE] - counts[CASE_KIND_ADVERSARIAL]
    )


def test_generate_scenarios_at_scale_gives_every_intent_a_fair_share():
    scenarios = generate_scenarios(n_main=1184)
    main = [s for s in scenarios if s.case_kind != CASE_KIND_NO_SKILL]
    per_intent = Counter(s.canonical_intent for s in main)
    assert set(per_intent) == {intent.intent_id for intent in INTENTS}
    # 1184 / 24 = 49.33 -- every intent must get 49 or 50, never fewer.
    assert min(per_intent.values()) == 49
    assert max(per_intent.values()) == 50


def test_generate_scenarios_at_scale_has_unique_ids():
    scenarios = generate_scenarios(n_main=1184)
    ids = [s.scenario_id for s in scenarios]
    assert len(ids) == len(set(ids))


def test_generate_scenarios_at_scale_is_deterministic():
    first = generate_scenarios(n_main=1184, seed=1)
    second = generate_scenarios(n_main=1184, seed=1)
    assert [s.scenario_id for s in first] == [s.scenario_id for s in second]
    assert [s.arguments for s in first] == [s.arguments for s in second]


def test_generate_scenarios_at_scale_spreads_adversarial_categories_evenly():
    """Category coverage indexes across ALL adversarial scenarios
    generated, never resets per-intent -- at n_main=1184 with 237
    adversarial scenarios and 8 categories, each category should appear
    roughly 237/8 ~= 30 times, never wildly skewed toward one."""
    scenarios = generate_scenarios(n_main=1184)
    adversarial = [s for s in scenarios if s.case_kind == CASE_KIND_ADVERSARIAL]
    category_counts = Counter(s.attack_category for s in adversarial)
    assert set(category_counts) == set(ATTACK_CATEGORIES)
    counts = list(category_counts.values())
    assert max(counts) - min(counts) <= 1


def test_generate_scenarios_at_scale_passes_oracle_concordance():
    from erp_agent_os.oracle_concordance_v2_1 import find_concordance_mismatches

    scenarios = generate_scenarios(n_main=1184)
    mismatches = find_concordance_mismatches(scenarios)
    assert not mismatches, mismatches
