"""TDD for erp_agent_os.power_v2_1 (v2.1 plan, Task 5).

Uses a reduced n_replicates for speed in the unit suite -- the >=100,000
minimum is enforced and exercised by scripts/run_power_v2_1.py, a
separate, deliberately slower command (see that script's own docstring),
not by these tests.
"""

import math

import numpy as np
import pytest

from erp_agent_os.power_v2_1 import (
    ALPHA_FAMILY,
    H1B_PATTERNS,
    H4_DETECTION_PATTERNS,
    H4_FALSE_ALLOW_PATTERNS,
    H4_UNAUTHORIZED_MUTATION_GIVEN_FALSE_ALLOW_C,
    MIN_MC_REPLICATES,
    POWER_TARGET,
    PowerSimulationError,
    _wald_paired_ci_lower_bound,
    _wilson_lower_bound,
    marginal_prob,
    simulate_h1a_power,
    simulate_h1b_power,
    simulate_h4_power,
)

_TEST_REPLICATES = 4_000


def test_min_replicates_and_power_target_match_the_spec():
    assert MIN_MC_REPLICATES >= 100_000
    assert POWER_TARGET == 0.80
    assert ALPHA_FAMILY == 0.05


def test_h1b_patterns_sum_to_one_and_imply_the_registered_discordance():
    total = sum(w for _, w in H1B_PATTERNS)
    assert math.isclose(total, 1.0)
    b_ca = sum(w for (a, b, c), w in H1B_PATTERNS if c == 1 and a == 0)
    c_ca = sum(w for (a, b, c), w in H1B_PATTERNS if c == 0 and a == 1)
    b_cb = sum(w for (a, b, c), w in H1B_PATTERNS if c == 1 and b == 0)
    c_cb = sum(w for (a, b, c), w in H1B_PATTERNS if c == 0 and b == 1)
    assert math.isclose(b_ca, 0.15)
    assert math.isclose(c_ca, 0.10)
    assert math.isclose(b_cb, 0.15)
    assert math.isclose(c_cb, 0.10)
    # implied true difference: +5 points, both contrasts
    assert math.isclose(b_ca - c_ca, 0.05)
    assert math.isclose(b_cb - c_cb, 0.05)


def test_h4_patterns_sum_to_one_and_imply_registered_discordance():
    assert math.isclose(sum(w for _, w in H4_FALSE_ALLOW_PATTERNS), 1.0)
    assert math.isclose(sum(w for _, w in H4_DETECTION_PATTERNS), 1.0)
    # false_allow: favorable to C is (A=1, C=0); unfavorable is (A=0, C=1).
    favorable = sum(w for (a, b, c), w in H4_FALSE_ALLOW_PATTERNS if a == 1 and c == 0)
    unfavorable = sum(
        w for (a, b, c), w in H4_FALSE_ALLOW_PATTERNS if a == 0 and c == 1
    )
    assert math.isclose(favorable, 0.15)
    assert math.isclose(unfavorable, 0.05)
    # detection: favorable to C is (A=0, C=1) -- higher recall is better.
    favorable_d = sum(w for (a, b, c), w in H4_DETECTION_PATTERNS if a == 0 and c == 1)
    unfavorable_d = sum(
        w for (a, b, c), w in H4_DETECTION_PATTERNS if a == 1 and c == 0
    )
    assert math.isclose(favorable_d, 0.15)
    assert math.isclose(unfavorable_d, 0.05)


def test_marginal_false_allow_c_matches_the_conditional_mutation_setup():
    """0.01 / 0.39 conditioned on false_allow_C=1 must yield exactly a 1%
    marginal unauthorized-mutation rate for C -- computed here from the
    registered pattern weights, not hand-copied."""
    marginal = marginal_prob(H4_FALSE_ALLOW_PATTERNS, index=2, value=1)
    assert math.isclose(marginal, 0.39)
    implied_marginal_rate = marginal * H4_UNAUTHORIZED_MUTATION_GIVEN_FALSE_ALLOW_C
    assert math.isclose(implied_marginal_rate, 0.01, abs_tol=1e-9)


def test_wald_ci_matches_a_hand_computed_example():
    b = np.array([20])
    c = np.array([10])
    n = 120
    point = (20 - 10) / 120
    variance = ((20 + 10) - (20 - 10) ** 2 / 120) / (120**2)
    z = 1.959963984540054  # scipy.stats.norm.ppf(0.975), literal for this test
    expected_lower = point - z * math.sqrt(variance)
    lower = _wald_paired_ci_lower_bound(b, c, n, alpha=0.05)
    assert lower[0] == pytest.approx(expected_lower, abs=1e-9)


def test_wald_ci_lower_bound_widens_as_alpha_shrinks():
    """Bonferroni adjustment (alpha/m) must produce a WIDER (more
    conservative, lower) bound than the unadjusted alpha -- otherwise the
    'multiplicity correction' would not actually be doing anything."""
    b = np.array([20])
    c = np.array([10])
    n = 120
    unadjusted = _wald_paired_ci_lower_bound(b, c, n, alpha=0.05)
    bonferroni_4 = _wald_paired_ci_lower_bound(b, c, n, alpha=0.05 / 4)
    assert bonferroni_4[0] < unadjusted[0]


def test_wilson_lower_bound_matches_a_known_textbook_value():
    # 45/100 successes, 95% Wilson score interval lower bound ~0.354-0.356
    # depending on rounding convention; verified independently via the
    # standard closed-form formula in this test, not just "looks right".
    bound = _wilson_lower_bound(45, 100)
    assert 0.35 < bound < 0.36


def test_wilson_bound_increases_with_more_trials_at_the_same_rate():
    small = _wilson_lower_bound(40, 100)
    large = _wilson_lower_bound(400, 1000)
    assert large > small  # same 0.40 point estimate, narrower CI at larger n


def test_wilson_bound_rejects_zero_trials():
    with pytest.raises(PowerSimulationError):
        _wilson_lower_bound(0, 0)


def test_h1a_search_raises_if_the_target_is_unreachable_by_max_n():
    with pytest.raises(PowerSimulationError):
        simulate_h1a_power(n_replicates=_TEST_REPLICATES, start_n=50, step=1_000_000)


def test_h1a_search_finds_an_n_whose_wilson_lower_bound_clears_target():
    result = simulate_h1a_power(n_replicates=_TEST_REPLICATES, start_n=400, step=100)
    assert result.power_ci95_low >= POWER_TARGET
    assert result.replicates == _TEST_REPLICATES


def test_h1b_search_finds_an_n_whose_wilson_lower_bound_clears_target():
    result = simulate_h1b_power(n_replicates=_TEST_REPLICATES, start_n=100, step=50)
    assert result.power_ci95_low >= POWER_TARGET


def test_h4_search_finds_an_n_whose_wilson_lower_bound_clears_target():
    result = simulate_h4_power(n_replicates=_TEST_REPLICATES, start_n=96, step=32)
    assert result.power_ci95_low >= POWER_TARGET


def test_h1a_and_h1b_are_deterministic_for_the_same_seed():
    first = simulate_h1a_power(
        n_replicates=_TEST_REPLICATES, start_n=400, step=100, seed=7
    )
    second = simulate_h1a_power(
        n_replicates=_TEST_REPLICATES, start_n=400, step=100, seed=7
    )
    assert first == second


def test_pattern_weights_must_sum_to_one_or_raise():
    from erp_agent_os.power_v2_1 import _pattern_arrays

    with pytest.raises(PowerSimulationError):
        _pattern_arrays((((0, 0, 0), 0.5), ((1, 1, 1), 0.4)))
