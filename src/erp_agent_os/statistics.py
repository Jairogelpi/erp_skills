"""Executable statistical plan (CLAUDE.md §21, roadmap P1.3).

Implements the paired tests the confirmatory protocol commits to, so the
analysis is code that runs rather than prose that promises: McNemar for
paired binary outcomes, Cochran's Q for three systems, bootstrap
confidence intervals for a paired proportion difference, and the effect
sizes §21 names (proportion difference, odds ratio, Cliff's delta).

SciPy is deliberately not a dependency: each test here is a short exact
formula over paired counts, and adding SciPy/statsmodels for four
functions would add a large transitive tree for arithmetic that is
auditable inline. Holm correction is included for the post-hoc family.
"""

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

_BOOTSTRAP_RESAMPLES = 10_000


@dataclass(frozen=True)
class McNemarResult:
    discordant_b: int
    discordant_c: int
    statistic: float
    p_value: float


@dataclass(frozen=True)
class Interval:
    point: float
    low: float
    high: float


def _chi2_sf_1df(x: float) -> float:
    """Survival function of chi-square with 1 df = erfc(sqrt(x/2))."""
    if x <= 0:
        return 1.0
    return math.erfc(math.sqrt(x / 2.0))


def mcnemar(first: Sequence[bool], second: Sequence[bool]) -> McNemarResult:
    """Paired binary comparison of two systems on the same units.

    Uses the continuity-corrected chi-square statistic. `b` counts units
    where `first` succeeded and `second` failed; `c` the reverse. Only
    discordant pairs carry information.
    """
    if len(first) != len(second):
        raise ValueError("paired sequences must have equal length")
    b = sum(1 for x, y in zip(first, second, strict=True) if x and not y)
    c = sum(1 for x, y in zip(first, second, strict=True) if y and not x)
    if b + c == 0:
        return McNemarResult(b, c, 0.0, 1.0)
    statistic = (abs(b - c) - 1) ** 2 / (b + c)
    return McNemarResult(b, c, statistic, _chi2_sf_1df(statistic))


def cochran_q(*systems: Sequence[bool]) -> tuple[float, int]:
    """Cochran's Q for k>=3 paired binary systems. Returns (Q, df)."""
    if len(systems) < 3:
        raise ValueError("Cochran's Q needs at least three systems")
    lengths = {len(s) for s in systems}
    if len(lengths) != 1:
        raise ValueError("paired sequences must have equal length")

    k = len(systems)
    column_totals = [sum(1 for v in s if v) for s in systems]
    row_totals = [sum(1 for s in systems if s[i]) for i in range(len(systems[0]))]
    grand = sum(column_totals)

    numerator = (k - 1) * (k * sum(t * t for t in column_totals) - grand**2)
    denominator = k * grand - sum(r * r for r in row_totals)
    if denominator == 0:
        return 0.0, k - 1
    return numerator / denominator, k - 1


def paired_proportion_difference(
    first: Sequence[bool],
    second: Sequence[bool],
    *,
    confidence: float = 0.95,
    seed: int = 20260805,
) -> Interval:
    """Bootstrap CI for the paired difference in success proportion."""
    if len(first) != len(second):
        raise ValueError("paired sequences must have equal length")
    n = len(first)
    if n == 0:
        raise ValueError("cannot bootstrap an empty sample")

    point = (sum(first) - sum(second)) / n
    rng = random.Random(seed)
    diffs = []
    indices = range(n)
    for _ in range(_BOOTSTRAP_RESAMPLES):
        sample = [rng.choice(indices) for _ in indices]
        diffs.append(sum(first[i] - second[i] for i in sample) / n)
    diffs.sort()
    alpha = (1 - confidence) / 2
    low = diffs[int(alpha * _BOOTSTRAP_RESAMPLES)]
    high = diffs[min(int((1 - alpha) * _BOOTSTRAP_RESAMPLES), _BOOTSTRAP_RESAMPLES - 1)]
    return Interval(point, low, high)


def odds_ratio(first: Sequence[bool], second: Sequence[bool]) -> float:
    """Paired odds ratio (b/c) with the Haldane-Anscombe 0.5 correction."""
    b = sum(1 for x, y in zip(first, second, strict=True) if x and not y)
    c = sum(1 for x, y in zip(first, second, strict=True) if y and not x)
    return (b + 0.5) / (c + 0.5)


def cliffs_delta(first: Sequence[float], second: Sequence[float]) -> float:
    """Non-parametric effect size for two independent samples, in [-1, 1]."""
    if not first or not second:
        raise ValueError("both samples must be non-empty")
    greater = sum(1 for x in first for y in second if x > y)
    lesser = sum(1 for x in first for y in second if x < y)
    return (greater - lesser) / (len(first) * len(second))


def holm_correction(p_values: Sequence[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, order-preserving."""
    indexed = sorted(enumerate(p_values), key=lambda pair: pair[1])
    m = len(p_values)
    adjusted = [0.0] * m
    running = 0.0
    for rank, (original_index, p) in enumerate(indexed):
        value = min(1.0, (m - rank) * p)
        running = max(running, value)
        adjusted[original_index] = running
    return adjusted
