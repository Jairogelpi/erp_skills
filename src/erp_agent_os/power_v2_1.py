"""Paired Monte Carlo power simulation for v2.1 sample-size selection.

docs/tfm-closure-no-human-v2.1.md section 10: the simulation must run
the SAME decision function and multiplicity correction as the final
confirmatory analysis, not per-contrast approximations, with >=100,000
Monte Carlo replicates per candidate size and a Wilson lower-95% bound
on simulated power >= 0.80.

**Design decision, made explicitly rather than silently defaulting**
(the user chose this over an McNemar+Holm p-value criterion): section
8's stated criteria are confidence-interval criteria ("los límites
inferiores de ambos IC95 superan 0"), not p-value thresholds. A full
nonparametric bootstrap CI (the method statistics.py already uses for
the final descriptive report) is far too slow to run >=100,000 times
per candidate n. This module instead uses the standard closed-form
Wald confidence interval for a paired-proportion difference (its
variance depends only on the discordant counts b, c -- the same b, c
McNemar's test already uses), with Bonferroni-adjusted per-contrast
confidence levels (alpha/m for a family of m simultaneous contrasts)
to control the familywise error rate for a joint multi-contrast event.
Bonferroni is more conservative than sequential Holm, so a sample size
this module selects as sufficient is sufficient (if anything,
slightly over-powered) under the final analysis's own Holm-corrected
criterion -- never the reverse.

This module is deliberately independent of erp_agent_os.statistics
(the v1 module): different formulas, verified against it only by
manual cross-checks in tests, not by importing its functions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy import stats

MIN_MC_REPLICATES = 100_000
POWER_TARGET = 0.80
ALPHA_FAMILY = 0.05

# Section 8, H1b: frozen joint (A, B, C) pattern probabilities. Order of
# each 3-tuple key is (A, B, C); values sum to 1.
H1B_PATTERNS: tuple[tuple[tuple[int, int, int], float], ...] = (
    ((0, 0, 0), 0.25),
    ((1, 1, 1), 0.32),
    ((0, 0, 1), 0.05),
    ((0, 1, 1), 0.10),
    ((1, 0, 1), 0.10),
    ((1, 1, 0), 0.02),
    ((1, 0, 0), 0.08),
    ((0, 1, 0), 0.08),
)

# Section 8, H4: two independently-sampled frozen joint distributions.
H4_FALSE_ALLOW_PATTERNS: tuple[tuple[tuple[int, int, int], float], ...] = (
    ((0, 0, 0), 0.36),
    ((1, 1, 1), 0.30),
    ((1, 1, 0), 0.05),
    ((1, 0, 0), 0.10),
    ((0, 1, 0), 0.10),
    ((0, 0, 1), 0.01),
    ((0, 1, 1), 0.04),
    ((1, 0, 1), 0.04),
)
H4_DETECTION_PATTERNS: tuple[tuple[tuple[int, int, int], float], ...] = (
    ((0, 0, 0), 0.26),
    ((1, 1, 1), 0.40),
    ((0, 0, 1), 0.05),
    ((0, 1, 1), 0.10),
    ((1, 0, 1), 0.10),
    ((1, 1, 0), 0.01),
    ((1, 0, 0), 0.04),
    ((0, 1, 0), 0.04),
)
# When false_allow_C == 1, unauthorized mutation is Bernoulli(0.01/0.39);
# it is impossible (probability 0) when false_allow_C == 0. This yields
# the registered 1% marginal rate (0.39 is false_allow_C's own marginal
# probability under H4_FALSE_ALLOW_PATTERNS, computed, not hardcoded, by
# _marginal_prob below and cross-checked in tests).
H4_UNAUTHORIZED_MUTATION_GIVEN_FALSE_ALLOW_C = 0.01 / 0.39


class PowerSimulationError(ValueError):
    pass


@dataclass(frozen=True)
class PowerResult:
    n: int
    replicates: int
    simulated_power: float
    power_ci95_low: float
    seed: int


def _pattern_arrays(
    patterns: tuple[tuple[tuple[int, int, int], float], ...],
) -> tuple[np.ndarray, np.ndarray]:
    outcomes = np.array([p for p, _ in patterns], dtype=np.int8)
    probs = np.array([w for _, w in patterns], dtype=np.float64)
    if not np.isclose(probs.sum(), 1.0):
        raise PowerSimulationError(f"pattern weights must sum to 1, got {probs.sum()}")
    return outcomes, probs


def _sample_patterns(
    patterns: tuple[tuple[tuple[int, int, int], float], ...],
    *,
    n_replicates: int,
    n_pairs: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Returns an (n_replicates, n_pairs, 3) int8 array of (A, B, C)
    draws, one row per simulated paired unit."""
    outcomes, probs = _pattern_arrays(patterns)
    choice = rng.choice(len(outcomes), size=(n_replicates, n_pairs), p=probs)
    return outcomes[choice]


def _discordant_counts(
    draws: np.ndarray, *, comparator_index: int, target_index: int = 2
) -> tuple[np.ndarray, np.ndarray]:
    """b = count of pairs where target=1, comparator=0 (favors target);
    c = the reverse. Vectorized over the replicate axis (axis 0)."""
    target = draws[:, :, target_index]
    comparator = draws[:, :, comparator_index]
    b = np.sum((target == 1) & (comparator == 0), axis=1)
    c = np.sum((target == 0) & (comparator == 1), axis=1)
    return b, c


def _wald_paired_ci_lower_bound(
    b: np.ndarray, c: np.ndarray, n: int, *, alpha: float
) -> np.ndarray:
    """Closed-form Wald CI lower bound for a paired-proportion
    difference (target - comparator), vectorized. Variance formula
    depends only on the discordant counts b, c -- the same statistic
    McNemar's test consumes."""
    point = (b - c) / n
    variance = ((b + c) - (b - c) ** 2 / n) / (n**2)
    variance = np.maximum(variance, 0.0)
    z = stats.norm.ppf(1 - alpha / 2)
    return point - z * np.sqrt(variance)


def _wilson_lower_bound(
    successes: int, trials: int, *, confidence: float = 0.95
) -> float:
    if trials == 0:
        raise PowerSimulationError("cannot compute a Wilson bound over zero trials")
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    phat = successes / trials
    denom = 1 + z**2 / trials
    center = phat + z**2 / (2 * trials)
    margin = z * np.sqrt(phat * (1 - phat) / trials + z**2 / (4 * trials**2))
    return float((center - margin) / denom)


def _search_min_n(
    evaluate_power: Callable[[int, np.random.Generator, int], float],
    *,
    start_n: int,
    step: int,
    seed: int,
    n_replicates: int,
    max_n: int = 2000,
) -> PowerResult:
    n = start_n
    rng = np.random.default_rng(seed)
    while n <= max_n:
        power = evaluate_power(n, rng, n_replicates)
        successes = round(power * n_replicates)
        lower = _wilson_lower_bound(successes, n_replicates)
        if lower >= POWER_TARGET:
            return PowerResult(
                n=n,
                replicates=n_replicates,
                simulated_power=power,
                power_ci95_low=lower,
                seed=seed,
            )
        n += step
    raise PowerSimulationError(f"power target not reached by n={max_n}")


def simulate_h1a_power(
    *,
    start_n: int = 120,
    step: int = 4,
    seed: int = 20260814,
    n_replicates: int = MIN_MC_REPLICATES,
) -> PowerResult:
    """Non-inferiority: symmetric discordance under true difference 0,
    P(C=1,A=0)=P(C=0,A=1)=0.125. Criterion: Wald CI lower bound of
    (C - A) at plain (unadjusted) 95% confidence exceeds -0.05 -- single
    contrast, no multiplicity family (section 10: "La potencia de H1a se
    calculará separadamente"). `n_replicates` defaults to the registered
    minimum; tests may pass a smaller value for speed -- callers that
    need a confirmatory-grade result must not lower it."""

    def evaluate(n: int, rng: np.random.Generator, replicates: int) -> float:
        # Multinomial over {C wins, A wins, concordant}: 0.125/0.125/0.75.
        draws = rng.choice(3, size=(replicates, n), p=[0.125, 0.125, 0.75])
        b = np.sum(draws == 0, axis=1)
        c = np.sum(draws == 1, axis=1)
        lower = _wald_paired_ci_lower_bound(b, c, n, alpha=ALPHA_FAMILY)
        return float(np.mean(lower > -0.05))

    return _search_min_n(
        evaluate, start_n=start_n, step=step, seed=seed, n_replicates=n_replicates
    )


def simulate_h1b_power(
    *,
    start_n: int = 120,
    step: int = 4,
    seed: int = 20260814,
    n_replicates: int = MIN_MC_REPLICATES,
) -> PowerResult:
    """Superiority: joint event requires BOTH C-A and C-B Bonferroni-
    adjusted (family of 2) Wald CI lower bounds to exceed 0, evaluated
    from a single draw per replicate from the frozen 8-pattern (A,B,C)
    joint distribution (not two independent draws), matching "no se
    multiplicarán potencias marginales"."""

    def evaluate(n: int, rng: np.random.Generator, replicates: int) -> float:
        draws = _sample_patterns(
            H1B_PATTERNS, n_replicates=replicates, n_pairs=n, rng=rng
        )
        b_ca, c_ca = _discordant_counts(draws, comparator_index=0)
        b_cb, c_cb = _discordant_counts(draws, comparator_index=1)
        alpha_adjusted = ALPHA_FAMILY / 2
        lower_ca = _wald_paired_ci_lower_bound(b_ca, c_ca, n, alpha=alpha_adjusted)
        lower_cb = _wald_paired_ci_lower_bound(b_cb, c_cb, n, alpha=alpha_adjusted)
        joint = (lower_ca > 0) & (lower_cb > 0)
        return float(np.mean(joint))

    return _search_min_n(
        evaluate, start_n=start_n, step=step, seed=seed, n_replicates=n_replicates
    )


def simulate_h4_power(
    *,
    start_n: int = 84,  # 7 categories * 12 (r4_operation retired, was 96/8)
    step: int = 7,
    seed: int = 20260814,
    n_replicates: int = MIN_MC_REPLICATES,
) -> PowerResult:
    """Joint H4 event: both false-allow contrasts AND both detection-
    recall contrasts (Bonferroni family of 4) favor C, AND the one-sided
    95% upper Clopper-Pearson bound on C's simulated unauthorized-
    mutation rate is below 5%. false_allow and detection are sampled
    with independent random streams within the same row (so a signal
    can be detected but still ignored), matching section 8."""

    def evaluate(n: int, rng: np.random.Generator, replicates: int) -> float:
        allow_draws = _sample_patterns(
            H4_FALSE_ALLOW_PATTERNS, n_replicates=replicates, n_pairs=n, rng=rng
        )
        detect_draws = _sample_patterns(
            H4_DETECTION_PATTERNS, n_replicates=replicates, n_pairs=n, rng=rng
        )
        # false_allow: LOWER is favorable to C, i.e. C=0,comparator=1 is
        # the "C wins" direction -- the reverse of detection, where
        # HIGHER (C=1,comparator=0) is favorable.
        c_wins_allow_a, comp_wins_allow_a = _discordant_counts(
            allow_draws, comparator_index=0
        )
        c_wins_allow_b, comp_wins_allow_b = _discordant_counts(
            allow_draws, comparator_index=1
        )
        alpha_adjusted = ALPHA_FAMILY / 4
        lower_allow_a = _wald_paired_ci_lower_bound(
            comp_wins_allow_a, c_wins_allow_a, n, alpha=alpha_adjusted
        )
        lower_allow_b = _wald_paired_ci_lower_bound(
            comp_wins_allow_b, c_wins_allow_b, n, alpha=alpha_adjusted
        )

        b_detect_a, c_detect_a = _discordant_counts(detect_draws, comparator_index=0)
        b_detect_b, c_detect_b = _discordant_counts(detect_draws, comparator_index=1)
        lower_detect_a = _wald_paired_ci_lower_bound(
            b_detect_a, c_detect_a, n, alpha=alpha_adjusted
        )
        lower_detect_b = _wald_paired_ci_lower_bound(
            b_detect_b, c_detect_b, n, alpha=alpha_adjusted
        )

        false_allow_c = allow_draws[:, :, 2]
        eligible = false_allow_c == 1
        mutation_draws = rng.random(size=false_allow_c.shape) < (
            H4_UNAUTHORIZED_MUTATION_GIVEN_FALSE_ALLOW_C
        )
        mutations = np.sum(eligible & mutation_draws, axis=1)
        # Vectorized Clopper-Pearson upper bound: beta.ppf accepts array
        # arguments directly. A per-replicate Python-level call here (a
        # list comprehension calling scipy once per one of the >=100,000
        # replicates) was measured to make this function the dominant
        # cost of the whole power search; vectorizing it is not a style
        # preference; the search was impractically slow without it.
        mutation_rate_upper = np.where(
            mutations < n,
            stats.beta.ppf(0.95, mutations + 1, n - mutations),
            1.0,
        )

        joint = (
            (lower_allow_a > 0)
            & (lower_allow_b > 0)
            & (lower_detect_a > 0)
            & (lower_detect_b > 0)
            & (mutation_rate_upper < 0.05)
        )
        return float(np.mean(joint))

    return _search_min_n(
        evaluate, start_n=start_n, step=step, seed=seed, n_replicates=n_replicates
    )


def marginal_prob(
    patterns: tuple[tuple[tuple[int, int, int], float], ...], index: int, value: int
) -> float:
    return sum(weight for outcome, weight in patterns if outcome[index] == value)
