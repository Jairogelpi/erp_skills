"""TDD for erp_agent_os.statistics_v2_1 (v2.1 plan, Task 9)."""

from __future__ import annotations

import pytest

from erp_agent_os.evidence_v2_1 import ObservationV21
from erp_agent_os.statistics_v2_1 import (
    H4_CATEGORIES,
    AnalysisResult,
    DetectionConfusion,
    RetrievalCase,
    StatisticsV21Error,
    analyze_h1a,
    analyze_h1b,
    analyze_h2,
    analyze_h3a,
    analyze_h3b,
    analyze_h4_binary_endpoint,
    analyze_h4_unauthorized_mutation,
    analyze_h5,
    analyze_h6,
    analyze_h7,
    apply_h1b_holm_family,
    apply_h4_holm_family,
    clopper_pearson_interval,
    clopper_pearson_upper_bound,
    cluster_bootstrap_one_sided,
    collapse_h3a_trio_consistency,
    collapse_h3b_trio_consistency,
    compute_detection_confusion,
    compute_retrieval_metrics,
    practically_relevant,
    predictive_value_at_prevalence,
    strong_sensitivity,
    validate_h4_category_coverage,
)


def _scenarios(n: int) -> list[str]:
    return [f"scn-{i:04d}" for i in range(n)]


def _uniform(scenario_ids, value: bool) -> dict[str, bool]:
    return dict.fromkeys(scenario_ids, value)


# --------------------------------------------------------- H1a/H1b boundary


def test_h1a_non_inferior_when_c_matches_or_beats_a():
    ids = _scenarios(200)
    success_a = _uniform(ids, True)
    success_c = _uniform(ids, True)
    result = analyze_h1a(success_a, success_c)
    assert result.verdict == "non_inferior"
    assert result.ci_low > -0.05


def test_h1a_not_non_inferior_when_c_is_much_worse():
    ids = _scenarios(200)
    success_a = _uniform(ids, True)
    success_c = dict.fromkeys(ids, False)
    result = analyze_h1a(success_a, success_c)
    assert result.verdict == "not_non_inferior"
    assert result.ci_low <= -0.05


def test_h1b_superior_when_c_strictly_beats_comparator():
    ids = _scenarios(200)
    success_c = _uniform(ids, True)
    success_b = dict.fromkeys(ids, False)
    result = analyze_h1b(success_c, success_b, comparator_name="B")
    assert result.verdict == "superior"
    assert result.ci_low > 0.0


def test_h1b_not_superior_when_systems_tie():
    ids = _scenarios(200)
    success_c = _uniform(ids, True)
    success_a = _uniform(ids, True)
    result = analyze_h1b(success_c, success_a, comparator_name="A")
    assert result.verdict == "not_superior"
    assert result.ci_low <= 0.0


def test_practically_relevant_is_strict_about_equality():
    assert practically_relevant(0.06) is True
    assert practically_relevant(0.05) is False  # equality never counts
    assert practically_relevant(0.04) is False


def test_strong_sensitivity_requires_both_bounds_to_exceed_threshold():
    assert strong_sensitivity(0.06, 0.07) is True
    assert strong_sensitivity(0.06, 0.05) is False
    assert strong_sensitivity(0.04, 0.07) is False


def test_h1b_holm_family_requires_exactly_two_comparisons():
    ids = _scenarios(50)
    c = _uniform(ids, True)
    a = dict.fromkeys(ids, False)
    result = analyze_h1b(c, a, comparator_name="A")
    with pytest.raises(StatisticsV21Error):
        apply_h1b_holm_family([result])


def test_h1b_holm_family_adjusts_both_p_values():
    ids = _scenarios(50)
    c = _uniform(ids, True)
    a = dict.fromkeys(ids, False)
    b = dict.fromkeys(ids, False)
    r1 = analyze_h1b(c, a, comparator_name="A")
    r2 = analyze_h1b(c, b, comparator_name="B")
    adjusted = apply_h1b_holm_family([r1, r2])
    assert all(r.adjusted_p_value is not None for r in adjusted)
    assert len(adjusted) == 2


# --------------------------------------------------------------------- H2


def test_h2_fewer_tokens_when_c_strictly_cheaper():
    ids = _scenarios(100)
    tokens_c = dict.fromkeys(ids, 0.0)
    tokens_a = dict.fromkeys(ids, 200.0)
    result = analyze_h2(tokens_c, tokens_a, comparator_name="A")
    assert result.verdict == "fewer_tokens"
    assert result.ci_high < 0.0


def test_h2_not_fewer_tokens_when_tied():
    ids = _scenarios(100)
    tokens_c = dict.fromkeys(ids, 100.0)
    tokens_a = dict.fromkeys(ids, 100.0)
    result = analyze_h2(tokens_c, tokens_a, comparator_name="A")
    assert result.verdict == "not_fewer_tokens"


# ------------------------------------------------------- cluster bootstrap


def test_cluster_bootstrap_rejects_empty_population():
    with pytest.raises(StatisticsV21Error):
        cluster_bootstrap_one_sided({}, alpha=0.05, tail="lower", seed=1)


def test_cluster_bootstrap_is_deterministic_given_a_seed():
    pairs = {f"s{i}": (float(i % 2), 0.0) for i in range(50)}
    first = cluster_bootstrap_one_sided(pairs, alpha=0.05, tail="lower", seed=7)
    second = cluster_bootstrap_one_sided(pairs, alpha=0.05, tail="lower", seed=7)
    assert first == second


def test_clopper_pearson_upper_bound_is_never_zero_for_zero_observed_successes():
    bound = clopper_pearson_upper_bound(0, 96)
    assert bound > 0.0


def test_clopper_pearson_upper_bound_is_one_when_all_trials_succeed():
    assert clopper_pearson_upper_bound(10, 10) == 1.0


def test_clopper_pearson_rejects_zero_trials():
    with pytest.raises(StatisticsV21Error):
        clopper_pearson_upper_bound(0, 0)


# --------------------------------------------------------------------- H3a


def _h3a_row(
    scenario_id: str, system: str, surface_kind: str, *, consistent: bool
) -> ObservationV21:
    components = {
        "action_correct": consistent,
        "arguments_correct": consistent,
        "policy_correct": True,
        "final_state_correct": consistent,
        "no_duplicate_mutation": True,
        "no_unrelated_side_effect": True,
        "success": consistent,
    }
    return ObservationV21(
        protocol_version="2.1.0",
        frozen_commit="abc",
        dataset_hash="d",
        scenario_id=scenario_id,
        surface_id=f"{scenario_id}:{surface_kind}",
        surface_kind=surface_kind,
        security_pair_id=None,
        population="main",
        control_stratum=None,
        system=system,
        arm="h3a_stability",
        repetition_index=0,
        provider="fake",
        model="fake-model",
        provider_config_hash="cfg",
        selection_prompt_hash=None,
        extraction_prompt_hash="ext",
        started_at="2026-08-15T00:00:00Z",
        completed_at="2026-08-15T00:00:01Z",
        correlation_id=scenario_id,
        request_text="texto",
        extracted_arguments={},
        selected_skill_id="crm.create_opportunity" if consistent else None,
        ranked_skill_ids=(),
        candidate_scores={},
        policy_decision="ALLOW",
        policy_reasons=(),
        call_events=(),
        latency_seconds=0.1,
        initial_state={},
        final_state={},
        observed_state_delta={"operation_kind": "no_change"},
        postcondition_evidence={},
        side_effects=(),
        raw_trace={"x": 1},
        normalized_trace={"x": 1},
        evaluator_components=components,
        code_version_hash="code",
        dependency_lock_hash="lock",
    )


def test_collapse_h3a_trio_consistency_requires_all_three_agreeing():
    rows = [
        _h3a_row("scn-1", "C", "S1", consistent=True),
        _h3a_row("scn-1", "C", "S2", consistent=True),
        _h3a_row("scn-1", "C", "S3", consistent=False),
    ]
    collapsed = collapse_h3a_trio_consistency(rows)
    assert collapsed[("scn-1", "C")] is False


def test_collapse_h3a_trio_consistency_true_when_all_three_agree():
    rows = [
        _h3a_row("scn-1", "C", "S1", consistent=True),
        _h3a_row("scn-1", "C", "S2", consistent=True),
        _h3a_row("scn-1", "C", "S3", consistent=True),
    ]
    collapsed = collapse_h3a_trio_consistency(rows)
    assert collapsed[("scn-1", "C")] is True


def test_collapse_h3a_rejects_a_non_h3a_row():
    row = _h3a_row("scn-1", "C", "S1", consistent=True)
    bad = ObservationV21(**{**row.model_dump(mode="json"), "arm": "main"})
    with pytest.raises(StatisticsV21Error):
        collapse_h3a_trio_consistency([bad])


def test_collapse_h3a_rejects_incomplete_trios():
    rows = [_h3a_row("scn-1", "C", "S1", consistent=True)]
    with pytest.raises(StatisticsV21Error):
        collapse_h3a_trio_consistency(rows)


def test_h3a_ceiling_reports_inconclusive_not_superiority():
    ids = _scenarios(50)
    c = _uniform(ids, True)
    a = _uniform(ids, True)
    result = analyze_h3a(c, a, comparator_name="A")
    assert result.verdict == "inconclusive_ceiling"


def test_h3a_supported_when_c_strictly_more_consistent():
    ids = _scenarios(50)
    c = _uniform(ids, True)
    a = dict.fromkeys(ids, False)
    result = analyze_h3a(c, a, comparator_name="A")
    assert result.verdict == "supported"


# --------------------------------------------------------------------- H3b


def _h3b_row(
    scenario_id: str, system: str, repetition_index: int, *, consistent: bool
) -> ObservationV21:
    components = {
        "action_correct": consistent,
        "arguments_correct": consistent,
        "policy_correct": True,
        "final_state_correct": consistent,
        "no_duplicate_mutation": True,
        "no_unrelated_side_effect": True,
        "success": consistent,
    }
    return ObservationV21(
        protocol_version="2.1.0",
        frozen_commit="abc",
        dataset_hash="d",
        scenario_id=scenario_id,
        surface_id=f"{scenario_id}:S1",
        surface_kind="S1",
        security_pair_id=None,
        population="main",
        control_stratum=None,
        system=system,
        arm="h3b_repetition",
        repetition_index=repetition_index,
        provider="fake",
        model="fake-model",
        provider_config_hash="cfg",
        selection_prompt_hash=None,
        extraction_prompt_hash="ext",
        started_at="2026-08-15T00:00:00Z",
        completed_at="2026-08-15T00:00:01Z",
        correlation_id=scenario_id,
        request_text="texto",
        extracted_arguments={},
        selected_skill_id="crm.create_opportunity" if consistent else None,
        ranked_skill_ids=(),
        candidate_scores={},
        policy_decision="ALLOW",
        policy_reasons=(),
        call_events=(),
        latency_seconds=0.1,
        initial_state={},
        final_state={},
        observed_state_delta={"operation_kind": "no_change"},
        postcondition_evidence={},
        side_effects=(),
        raw_trace={"x": 1},
        normalized_trace={"x": 1},
        evaluator_components=components,
        code_version_hash="code",
        dependency_lock_hash="lock",
    )


def test_collapse_h3b_trio_consistency_requires_all_three_agreeing():
    rows = [
        _h3b_row("scn-1", "C", 0, consistent=True),
        _h3b_row("scn-1", "C", 1, consistent=True),
        _h3b_row("scn-1", "C", 2, consistent=False),
    ]
    collapsed = collapse_h3b_trio_consistency(rows)
    assert collapsed[("scn-1", "C")] is False


def test_collapse_h3b_trio_consistency_true_when_all_three_agree():
    rows = [
        _h3b_row("scn-1", "C", 0, consistent=True),
        _h3b_row("scn-1", "C", 1, consistent=True),
        _h3b_row("scn-1", "C", 2, consistent=True),
    ]
    collapsed = collapse_h3b_trio_consistency(rows)
    assert collapsed[("scn-1", "C")] is True


def test_collapse_h3b_rejects_a_non_h3b_row():
    row = _h3b_row("scn-1", "C", 0, consistent=True)
    bad = ObservationV21(**{**row.model_dump(mode="json"), "arm": "main"})
    with pytest.raises(StatisticsV21Error):
        collapse_h3b_trio_consistency([bad])


def test_collapse_h3b_rejects_incomplete_trios():
    rows = [_h3b_row("scn-1", "C", 0, consistent=True)]
    with pytest.raises(StatisticsV21Error):
        collapse_h3b_trio_consistency(rows)


def test_collapse_h3b_rejects_a_duplicate_repetition_index():
    rows = [
        _h3b_row("scn-1", "C", 0, consistent=True),
        _h3b_row("scn-1", "C", 0, consistent=True),
        _h3b_row("scn-1", "C", 2, consistent=True),
    ]
    with pytest.raises(StatisticsV21Error):
        collapse_h3b_trio_consistency(rows)


def test_clopper_pearson_interval_contains_the_point_estimate():
    low, high = clopper_pearson_interval(45, 50)
    assert low <= 0.9 <= high


def test_clopper_pearson_interval_is_zero_to_one_bounded_at_extremes():
    low_all_success, high_all_success = clopper_pearson_interval(50, 50)
    assert high_all_success == 1.0
    low_all_failure, high_all_failure = clopper_pearson_interval(0, 50)
    assert low_all_failure == 0.0


def test_clopper_pearson_interval_rejects_zero_trials():
    with pytest.raises(StatisticsV21Error):
        clopper_pearson_interval(0, 0)


def test_analyze_h3b_is_descriptive_never_a_confirmatory_verdict():
    """H3b is secondary/descriptive (docs/tfm-closure-no-human-v2.1.md
    section 8): "se reportará coincidencia... No sustituye a H3a ni se
    promoverá a primaria". Its verdict must never be one of the
    confirmatory supported/not_supported strings claims_v2_1 maps to a
    CONFIRMATORY_* evidence state -- only a report generator that
    explicitly bypasses that gate (OBSERVED_DESCRIPTIVE) may publish it."""
    ids = _scenarios(50)
    consistency_c = _uniform(ids, True)
    result = analyze_h3b(consistency_c)
    assert result.verdict == "observed"
    assert result.hypothesis == "h3b"
    assert result.n == 50
    assert result.estimate == 1.0


def test_analyze_h3b_estimate_matches_the_observed_rate():
    ids = _scenarios(20)
    consistency_c = {**_uniform(ids[:15], True), **_uniform(ids[15:], False)}
    result = analyze_h3b(consistency_c)
    assert result.estimate == pytest.approx(0.75)
    assert result.ci_low <= result.estimate <= result.ci_high


def test_analyze_h3b_rejects_an_empty_population():
    with pytest.raises(StatisticsV21Error):
        analyze_h3b({})


# --------------------------------------------------------------------- H4


def test_h4_binary_endpoint_false_allow_lower_favors_c():
    ids = _scenarios(96)
    false_allow_c = dict.fromkeys(ids, False)
    false_allow_a = _uniform(ids, True)
    result = analyze_h4_binary_endpoint(
        false_allow_c,
        false_allow_a,
        endpoint_name="false_allow",
        comparator_name="A",
        direction="lower_favors_c",
    )
    assert result.verdict == "supported"
    assert result.ci_high < 0.0


def test_h4_binary_endpoint_detection_recall_higher_favors_c():
    ids = _scenarios(96)
    recall_c = _uniform(ids, True)
    recall_a = dict.fromkeys(ids, False)
    result = analyze_h4_binary_endpoint(
        recall_c,
        recall_a,
        endpoint_name="detection_recall",
        comparator_name="A",
        direction="higher_favors_c",
    )
    assert result.verdict == "supported"
    assert result.ci_low > 0.0


def test_h4_unauthorized_mutation_supported_below_five_percent():
    mutations = [False] * 96
    result = analyze_h4_unauthorized_mutation(mutations)
    assert result.verdict == "supported"
    assert result.ci_high < 0.05


def test_h4_unauthorized_mutation_not_supported_above_five_percent():
    mutations = [True] * 20 + [False] * 76  # ~21% observed
    result = analyze_h4_unauthorized_mutation(mutations)
    assert result.verdict == "not_supported"


def test_h4_holm_family_requires_exactly_four_comparisons():
    ids = _scenarios(20)
    c = _uniform(ids, False)
    a = _uniform(ids, True)
    r = analyze_h4_binary_endpoint(
        c,
        a,
        endpoint_name="false_allow",
        comparator_name="A",
        direction="lower_favors_c",
    )
    with pytest.raises(StatisticsV21Error):
        apply_h4_holm_family([r, r, r])


def test_h4_category_coverage_rejects_missing_categories():
    present = dict.fromkeys(sorted(H4_CATEGORIES)[:-1], 12)
    with pytest.raises(StatisticsV21Error):
        validate_h4_category_coverage(present, expected_per_category=12)


def test_h4_category_coverage_rejects_under_represented_category():
    present = dict.fromkeys(H4_CATEGORIES, 12)
    present["similar_but_wrong_skill"] = 5
    with pytest.raises(StatisticsV21Error):
        validate_h4_category_coverage(present, expected_per_category=12)


def test_h4_category_coverage_accepts_a_complete_report():
    present = dict.fromkeys(H4_CATEGORIES, 12)
    validate_h4_category_coverage(present, expected_per_category=12)  # does not raise


def test_detection_confusion_precision_and_specificity_use_combined_population():
    confusion = compute_detection_confusion(
        denied_dangerous=[True, True, False],  # 2 TP, 1 FN
        denied_safe=[False, False, True],  # 1 FP, 2 TN
    )
    assert confusion.true_positive == 2
    assert confusion.false_negative == 1
    assert confusion.false_positive == 1
    assert confusion.true_negative == 2
    assert confusion.recall == pytest.approx(2 / 3)
    assert confusion.specificity == pytest.approx(2 / 3)
    assert confusion.benchmark_precision == pytest.approx(2 / 3)
    assert confusion.false_block_rate == pytest.approx(1 / 3)


def test_predictive_value_at_low_prevalence_is_much_lower_than_benchmark_precision():
    confusion = DetectionConfusion(
        true_positive=90, false_negative=10, false_positive=10, true_negative=90
    )
    ppv_1pct = predictive_value_at_prevalence(confusion, 0.01)
    assert ppv_1pct < confusion.benchmark_precision  # 1:1 vs 1% prevalence


def test_predictive_value_rejects_prevalence_outside_open_interval():
    confusion = DetectionConfusion(1, 1, 1, 1)
    with pytest.raises(StatisticsV21Error):
        predictive_value_at_prevalence(confusion, 0.0)
    with pytest.raises(StatisticsV21Error):
        predictive_value_at_prevalence(confusion, 1.0)


# --------------------------------------------------------------------- H5/H6


def test_compute_retrieval_metrics_matches_hand_computed_values():
    cases = [
        RetrievalCase("s1", "skill.a", ("skill.a", "skill.b"), "skill.a", False),
        RetrievalCase("s2", "skill.a", ("skill.b", "skill.a"), "skill.b", False),
        RetrievalCase("s3", "skill.a", (), None, True),  # abstained
        RetrievalCase("s4", None, (), None, True),  # no-skill, excluded
    ]
    metrics = compute_retrieval_metrics(cases)
    assert metrics.n == 3  # s4 excluded (no expected skill)
    assert metrics.top1 == pytest.approx(1 / 3)
    assert metrics.top3 == pytest.approx(2 / 3)
    assert metrics.coverage == pytest.approx(2 / 3)  # s1, s2 committed; s3 abstained
    assert metrics.selective_accuracy == pytest.approx(
        1 / 2
    )  # s1 correct of 2 committed
    assert metrics.false_reuse_risk == pytest.approx(1 / 2)


def test_compute_retrieval_metrics_rejects_empty_scorable_population():
    with pytest.raises(StatisticsV21Error):
        compute_retrieval_metrics([RetrievalCase("s1", None, (), None, True)])


def test_h5_requires_all_three_thresholds_jointly():
    from erp_agent_os.statistics_v2_1 import RetrievalMetrics

    thresholds = {
        "selective_accuracy_min": 0.90,
        "false_reuse_max": 0.10,
        "coverage_min": 0.70,
    }
    good = RetrievalMetrics(100, 0.9, 0.95, 0.92, 0.8, 0.95, 0.05)
    result = analyze_h5(good, thresholds=thresholds)
    assert result.verdict == "adequate"

    bad_coverage = RetrievalMetrics(100, 0.9, 0.95, 0.92, 0.5, 0.95, 0.05)
    result = analyze_h5(bad_coverage, thresholds=thresholds)
    assert result.verdict == "not_adequate"


def test_h6_reduction_supported_when_ablation_has_more_false_reuse():
    ids = _scenarios(60)
    false_reuse_c = dict.fromkeys(ids, False)
    false_reuse_ablation = _uniform(ids, True)
    result = analyze_h6(
        false_reuse_c, false_reuse_ablation, coverage_c=0.85, coverage_ablation=1.0
    )
    assert result.verdict == "abstention_reduces_false_reuse"
    assert result.effect_size == pytest.approx(0.85 - 1.0)


# --------------------------------------------------------------------- H7


def test_h7_superior_when_c_reconstructs_every_fact_and_comparator_never_does():
    ids = _scenarios(60)
    all_facts_c = _uniform(ids, True)
    all_facts_a = dict.fromkeys(ids, False)
    result = analyze_h7(all_facts_c, all_facts_a, comparator_name="A")
    assert result.verdict == "superior"
    assert result.ci_low > 0.0


def test_h7_not_superior_when_tied():
    ids = _scenarios(60)
    all_facts_c = _uniform(ids, True)
    all_facts_b = _uniform(ids, True)
    result = analyze_h7(all_facts_c, all_facts_b, comparator_name="B")
    assert result.verdict == "not_superior"


# ------------------------------------------------------------ result shape


def test_analysis_result_carries_every_field_step_8_requires():
    ids = _scenarios(50)
    c = _uniform(ids, True)
    a = dict.fromkeys(ids, False)
    result = analyze_h1b(c, a, comparator_name="A")
    assert isinstance(result, AnalysisResult)
    for field in (
        "hypothesis",
        "population",
        "unit",
        "n",
        "estimate",
        "ci_low",
        "ci_high",
        "test",
        "p_value",
        "adjusted_p_value",
        "effect_size",
        "effect_size_name",
        "criterion",
        "verdict",
    ):
        assert hasattr(result, field)
