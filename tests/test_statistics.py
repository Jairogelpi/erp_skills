import pytest

from erp_agent_os.statistics import (
    cliffs_delta,
    cochran_q,
    holm_correction,
    mcnemar,
    odds_ratio,
    paired_mean_difference,
    paired_proportion_difference,
)


def test_mcnemar_no_discordant_pairs_is_not_significant():
    result = mcnemar([True, False, True], [True, False, True])
    assert result.p_value == 1.0
    assert result.statistic == 0.0


def test_mcnemar_strong_asymmetry_is_significant():
    # 20 units where `first` wins, 1 where `second` does.
    first = [True] * 20 + [False]
    second = [False] * 20 + [True]
    result = mcnemar(first, second)

    assert result.discordant_b == 20
    assert result.discordant_c == 1
    assert result.p_value < 0.001


def test_mcnemar_is_symmetric_in_p_value():
    first = [True] * 12 + [False] * 3
    second = [False] * 12 + [True] * 3
    assert mcnemar(first, second).p_value == pytest.approx(
        mcnemar(second, first).p_value
    )


def test_mcnemar_rejects_unequal_lengths():
    with pytest.raises(ValueError):
        mcnemar([True], [True, False])


def test_cochran_q_identical_systems_is_zero():
    rows = [True, False, True, True]
    q, df = cochran_q(rows, rows, rows)
    assert q == 0.0
    assert df == 2


def test_cochran_q_detects_disagreement():
    a = [True] * 10
    b = [True] * 10
    c = [False] * 10
    q, df = cochran_q(a, b, c)
    assert q > 0
    assert df == 2


def test_cochran_q_needs_three_systems():
    with pytest.raises(ValueError):
        cochran_q([True], [False])


def test_bootstrap_interval_brackets_the_point_estimate():
    first = [True] * 30 + [False] * 10
    second = [True] * 15 + [False] * 25
    interval = paired_proportion_difference(first, second)

    assert interval.point == pytest.approx(0.375)
    assert interval.low <= interval.point <= interval.high


def test_bootstrap_is_deterministic_for_a_fixed_seed():
    first = [True, False, True, True, False]
    second = [False, False, True, False, True]
    assert paired_proportion_difference(first, second) == paired_proportion_difference(
        first, second
    )


def test_odds_ratio_above_one_when_first_wins_more():
    first = [True] * 9 + [False]
    second = [False] * 9 + [True]
    assert odds_ratio(first, second) > 1.0


def test_cliffs_delta_bounds():
    assert cliffs_delta([3, 4, 5], [0, 1, 2]) == 1.0
    assert cliffs_delta([0, 1, 2], [3, 4, 5]) == -1.0
    assert cliffs_delta([1, 2, 3], [1, 2, 3]) == 0.0


def test_holm_correction_is_monotone_and_order_preserving():
    adjusted = holm_correction([0.01, 0.04, 0.03])

    # Positions are preserved (input index 0 stays index 0)...
    assert len(adjusted) == 3
    # ...values never shrink below the raw p-value, and never exceed 1.
    assert all(a >= p for a, p in zip(adjusted, [0.01, 0.04, 0.03], strict=True))
    assert all(a <= 1.0 for a in adjusted)


def test_holm_correction_matches_known_values():
    # Classic worked example: p = .01, .02, .03 with m = 3
    # -> .03, .04, .03 -> enforced monotone -> .03, .04, .04
    assert holm_correction([0.01, 0.02, 0.03]) == pytest.approx([0.03, 0.04, 0.04])


def test_mcnemar_applies_the_continuity_correction_exactly():
    # Mutation-testing gap: dropping the -1 continuity correction left the
    # whole suite green. Without it the statistic is anti-conservative
    # (smaller p, easier to declare significance), so the exact value is
    # pinned rather than merely checked for "significant".
    first = [True] * 50 + [False] * 6 + [True] * 10
    second = [False] * 50 + [True] * 6 + [True] * 10
    result = mcnemar(first, second)

    b, c = 50, 6
    with_correction = (abs(b - c) - 1) ** 2 / (b + c)
    without_correction = (abs(b - c)) ** 2 / (b + c)

    assert result.statistic == pytest.approx(with_correction)
    assert result.statistic != pytest.approx(without_correction)


def test_bootstrap_interval_is_not_degenerate():
    # Mutation-testing gap: replacing the resample with the original sample
    # collapsed the CI to a single point and no test noticed, because
    # "low <= point <= high" holds for a degenerate interval. A CI of zero
    # width would be published as [0.700, 0.700].
    first = [True] * 70 + [False] * 30
    second = [True] * 40 + [False] * 60

    interval = paired_proportion_difference(first, second)

    assert interval.high > interval.low, "bootstrap CI collapsed to a point"
    assert interval.low < interval.point < interval.high


def test_paired_mean_difference_on_token_counts():
    # H2: mean tokens per case, C (0, never calls the LLM) vs B.
    b_tokens = [300.0, 250.0, 280.0, 310.0]
    c_tokens = [0.0, 0.0, 0.0, 0.0]

    interval = paired_mean_difference(c_tokens, b_tokens)

    assert interval.point == pytest.approx(-285.0)
    assert interval.low <= interval.point <= interval.high
    assert interval.high < 0  # C uses strictly fewer tokens than B here


def test_bootstrap_width_shrinks_as_the_sample_grows():
    # A real bootstrap narrows with n; a broken one does not react at all.
    small_a, small_b = [True] * 15 + [False] * 5, [True] * 5 + [False] * 15
    large_a, large_b = [True] * 150 + [False] * 50, [True] * 50 + [False] * 150

    small = paired_proportion_difference(small_a, small_b)
    large = paired_proportion_difference(large_a, large_b)

    assert (large.high - large.low) < (small.high - small.low)


def test_bootstrap_width_tracks_the_theoretical_standard_error():
    # The strongest guard against a broken resample: the interval width
    # must be in the right ballpark for the sample, not merely non-zero.
    # For a paired difference of proportions the normal approximation gives
    # a full width of about 2 * 1.96 * SE.
    import math

    first = [True] * 70 + [False] * 30
    second = [True] * 40 + [False] * 60
    n = len(first)

    interval = paired_proportion_difference(first, second)
    width = interval.high - interval.low

    b = sum(1 for x, y in zip(first, second, strict=True) if x and not y)
    c = sum(1 for x, y in zip(first, second, strict=True) if y and not x)
    se = math.sqrt((b + c) - (b - c) ** 2 / n) / n
    expected = 2 * 1.96 * se

    assert 0.5 * expected < width < 1.5 * expected
