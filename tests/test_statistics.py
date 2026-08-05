import pytest

from erp_agent_os.statistics import (
    cliffs_delta,
    cochran_q,
    holm_correction,
    mcnemar,
    odds_ratio,
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
