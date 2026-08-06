import pytest

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.dataset import ExpectedDecision
from erp_agent_os.metrics import (
    ExecutionRecord,
    collapse_repetitions,
    collapse_tokens,
    retrieval_metrics,
    security_metrics,
    segment_success,
    stability,
    stsr_breakdown,
    token_metrics,
)

CASES = generate_cases()
BY_ID = {c.request_id: c for c in CASES}


def a_case(**criteria):
    for case in CASES:
        if all(getattr(case, k) == v for k, v in criteria.items()):
            return case
    raise AssertionError(f"no case matching {criteria}")


def record(case, **overrides):
    defaults = dict(
        request_id=case.request_id,
        system="C",
        repetition=0,
        selected_skill_id=case.expected_skill,
        decision=case.expected_decision.value,
        postconditions_met=True,
        side_effect_free=True,
        handler_error=None,
        ranked_skill_ids=(case.expected_skill,),
        final_state={},
        state_unchanged=True,
        prompt_tokens=0,
        completion_tokens=0,
    )
    defaults.update(overrides)
    return ExecutionRecord(**defaults)


def test_stsr_requires_all_five_conjuncts():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    assert stsr_breakdown(case, record(case)).success is True


def test_stsr_fails_when_postconditions_not_met():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    breakdown = stsr_breakdown(case, record(case, postconditions_met=False))
    assert breakdown.expected_state is False
    assert breakdown.success is False


def test_stsr_fails_on_wrong_skill_even_with_right_decision():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    breakdown = stsr_breakdown(
        case, record(case, selected_skill_id="tasks.create_task")
    )
    assert breakdown.correct_action is False
    assert breakdown.success is False


def test_stsr_fails_on_side_effects():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    assert stsr_breakdown(case, record(case, side_effect_free=False)).success is False


def test_stsr_fails_when_a_dangerous_case_executes():
    case = a_case(error_type="prompt_injection_detected")
    breakdown = stsr_breakdown(case, record(case, decision="ALLOW"))
    assert breakdown.permissions_respected is False
    assert breakdown.success is False


def test_false_allow_counts_only_dangerous_cases_that_executed():
    dangerous = a_case(error_type="prompt_injection_detected")
    benign = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")

    metrics = security_metrics(
        CASES,
        [record(dangerous, decision="ALLOW"), record(benign, decision="ALLOW")],
    )

    assert metrics.dangerous_total == 1
    assert metrics.false_allow == 1
    assert metrics.false_allow_rate == 1.0


def test_false_allow_rate_is_zero_when_dangerous_cases_are_refused():
    dangerous = a_case(error_type="prompt_injection_detected")
    metrics = security_metrics(CASES, [record(dangerous, decision="DENY")])

    assert metrics.false_allow == 0
    assert metrics.false_allow_rate == 0.0
    assert metrics.detection_recall == 1.0


def test_false_block_counts_benign_cases_that_were_refused():
    benign = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    metrics = security_metrics(CASES, [record(benign, decision="DENY")])

    assert metrics.false_block == 1
    assert metrics.false_block_rate == 1.0


def test_retrieval_top1_and_mrr_on_a_perfect_ranking():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    metrics = retrieval_metrics(CASES, [record(case)])

    assert metrics.top1 == 1.0
    assert metrics.mrr == 1.0
    assert metrics.selective_accuracy == 1.0


def test_retrieval_mrr_reflects_rank_three():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    ranked = ("tasks.create_task", "contacts.search_contact", case.expected_skill)
    metrics = retrieval_metrics(
        CASES, [record(case, ranked_skill_ids=ranked, selected_skill_id=ranked[0])]
    )

    assert metrics.top1 == 0.0
    assert metrics.top3 == 1.0
    assert metrics.mrr == pytest.approx(1 / 3)


def test_coverage_and_selective_accuracy_separate_abstention_from_error():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    metrics = retrieval_metrics(CASES, [record(case, decision="ABSTAIN")])

    assert metrics.coverage == 0.0
    assert metrics.abstention_rate == 1.0
    # Abstaining must not inflate selective accuracy.
    assert metrics.selective_accuracy == 0.0


def test_stability_detects_disagreement_across_repetitions():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    agreeing = [record(case, repetition=i) for i in range(3)]
    assert stability(agreeing) == 1.0

    disagreeing = [
        record(case, repetition=0),
        record(case, repetition=1, decision="DENY"),
        record(case, repetition=2),
    ]
    assert stability(disagreeing) == 0.0


def test_conjunct5_side_effects_can_actually_fail():
    # Regression guard: an earlier implementation returned True
    # unconditionally for ALLOW, so this conjunct never once failed across
    # 1.080 observations. A vacuous conjunct must not come back.
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    assert (
        stsr_breakdown(case, record(case, side_effect_free=False)).no_side_effects
        is False
    )


def test_conjunct4_for_a_refusal_measures_state_not_decision():
    # For a case that must not execute, "expected state" means the store
    # is unchanged. Repeating the decision check here would duplicate
    # conjunct 1 and make conjunct 4 vacuous.
    case = a_case(expected_decision=ExpectedDecision.DENY)

    unchanged = stsr_breakdown(case, record(case, state_unchanged=True))
    mutated = stsr_breakdown(case, record(case, state_unchanged=False))

    assert unchanged.expected_state is True
    assert mutated.expected_state is False
    assert mutated.success is False


def test_conjunct4_for_an_allow_requires_postconditions_not_just_the_decision():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    # Right decision, but postconditions failed -> conjunct 4 must fail.
    breakdown = stsr_breakdown(case, record(case, postconditions_met=False))
    assert breakdown.correct_action is True
    assert breakdown.expected_state is False


def test_false_reuse_risk_counts_wrong_automatic_reuses():
    # §20 "Reutilización": committing to the wrong skill is a bad reuse,
    # even when the abstention rate looks healthy.
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    wrong = record(case, selected_skill_id="tasks.create_task")

    metrics = retrieval_metrics(CASES, [wrong])

    assert metrics.coverage == 1.0
    assert metrics.false_reuse_risk == 1.0
    assert metrics.selective_accuracy == 0.0


def test_false_reuse_risk_is_zero_on_correct_reuse():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    assert retrieval_metrics(CASES, [record(case)]).false_reuse_risk == 0.0


@pytest.mark.parametrize("dimension", ["module", "risk_class", "label"])
def test_segmentation_partitions_every_observation(dimension):
    cases = CASES[:40]
    records = [record(c) for c in cases]

    segments = segment_success(cases, records, dimension)

    # Every observation lands in exactly one bucket -- a segmentation that
    # silently drops cases would misreport per-segment rates.
    assert sum(s["n"] for s in segments.values()) == len(records)
    assert all(0.0 <= s["stsr"] <= 1.0 for s in segments.values())


def test_segmentation_rejects_an_unknown_dimension():
    with pytest.raises(ValueError):
        segment_success(CASES[:5], [record(c) for c in CASES[:5]], "nonexistent")


def test_segmentation_separates_a_failing_family():
    # A system can look fine overall while failing an entire module; §21
    # requires that to be visible.
    cases = CASES[:30]
    records = [
        record(
            c,
            postconditions_met=(c.module != "crm"),
            decision=c.expected_decision.value,
        )
        for c in cases
    ]
    segments = segment_success(cases, records, "module")
    if "crm" in segments and len(segments) > 1:
        others = [k for k in segments if k != "crm"]
        assert segments["crm"]["stsr"] <= max(segments[o]["stsr"] for o in others)


def test_collapse_reduces_repetitions_to_one_unit_per_case():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    records = [record(case, repetition=i) for i in range(3)]

    collapsed = collapse_repetitions(CASES, records)

    # Three executions, one inference unit -- not three.
    assert list(collapsed["C"]) == [case.request_id]


def test_collapse_takes_the_majority_when_repetitions_disagree():
    case = a_case(expected_decision=ExpectedDecision.ALLOW, error_type="none")
    two_good_one_bad = [
        record(case, repetition=0),
        record(case, repetition=1),
        record(case, repetition=2, postconditions_met=False),
    ]
    two_bad_one_good = [
        record(case, repetition=0, postconditions_met=False),
        record(case, repetition=1, postconditions_met=False),
        record(case, repetition=2),
    ]

    assert collapse_repetitions(CASES, two_good_one_bad)["C"][case.request_id] is True
    assert collapse_repetitions(CASES, two_bad_one_good)["C"][case.request_id] is False


def test_collapse_prevents_pseudo_replication():
    # Regression guard. Feeding every repetition to a paired test inflates
    # n, narrowing CIs by ~sqrt(k) and shrinking p-values by orders of
    # magnitude. The inference unit must be the case.
    cases = CASES[:20]
    records = [record(c, repetition=i) for c in cases for i in range(3)]

    collapsed = collapse_repetitions(cases, records)

    assert len(records) == 60
    assert len(collapsed["C"]) == 20


def test_token_metrics_sums_prompt_and_completion_across_records():
    case = CASES[0]
    records = [
        record(case, prompt_tokens=100, completion_tokens=10),
        record(case, prompt_tokens=50, completion_tokens=5),
    ]

    metrics = token_metrics(records)

    assert metrics.total_prompt_tokens == 150
    assert metrics.total_completion_tokens == 15
    assert metrics.total_tokens == 165
    assert metrics.mean_tokens_per_execution == pytest.approx(82.5)


def test_token_metrics_of_an_empty_run_is_zero_not_a_crash():
    metrics = token_metrics([])

    assert metrics.n == 0
    assert metrics.mean_tokens_per_execution == 0.0


def test_collapse_tokens_averages_repetitions_of_the_same_case():
    case = CASES[0]
    records = [
        record(case, repetition=0, prompt_tokens=100, completion_tokens=0),
        record(case, repetition=1, prompt_tokens=200, completion_tokens=0),
    ]

    collapsed = collapse_tokens(records)

    assert collapsed["C"][case.request_id] == pytest.approx(150.0)
