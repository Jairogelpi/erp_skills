"""Inter-annotator agreement (CLAUDE.md §21, roadmap P3.4).

Provides the *instrument*: a stratified review sample and Cohen's kappa
over two annotators' labels. It does **not** and cannot produce the
second annotator's labels — that is a human step. Running
`scripts/build_annotation_sample.py` emits a blank review sheet; kappa
is computed only once a human has filled it in.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass

from erp_agent_os.dataset import BenchmarkCase, CaseLabel


@dataclass(frozen=True)
class AgreementResult:
    n: int
    observed_agreement: float
    expected_agreement: float
    kappa: float

    def interpretation(self) -> str:
        """Landis & Koch (1977) bands. Reported as a convention, not a verdict."""
        k = self.kappa
        if k < 0.0:
            return "worse than chance"
        if k < 0.21:
            return "slight"
        if k < 0.41:
            return "fair"
        if k < 0.61:
            return "moderate"
        if k < 0.81:
            return "substantial"
        return "almost perfect"


def cohens_kappa(first: Sequence[str], second: Sequence[str]) -> AgreementResult:
    """Cohen's kappa for two annotators over the same items."""
    if len(first) != len(second):
        raise ValueError("annotator sequences must have equal length")
    n = len(first)
    if n == 0:
        raise ValueError("cannot compute kappa over an empty sample")

    observed = sum(1 for a, b in zip(first, second, strict=True) if a == b) / n

    categories = set(first) | set(second)
    expected = sum(
        (sum(1 for a in first if a == c) / n) * (sum(1 for b in second if b == c) / n)
        for c in categories
    )

    if expected == 1.0:
        # Every item in one category: kappa is undefined; agreement is
        # trivially perfect. Report kappa = 1.0 and let the caller see n.
        return AgreementResult(n, observed, expected, 1.0)

    kappa = (observed - expected) / (1 - expected)
    return AgreementResult(n, observed, expected, kappa)


def stratified_review_sample(
    cases: Sequence[BenchmarkCase],
    *,
    per_stratum: int = 8,
    seed: int = 20260805,
) -> list[BenchmarkCase]:
    """Deterministic sample covering every (label, risk class) stratum.

    Stratifying by label and risk means the reviewer sees adversarial and
    high-risk cases at a rate far above their share of the corpus — the
    places where a mis-annotation would most distort the results.
    """
    rng = random.Random(seed)
    strata: dict[tuple[str, str], list[BenchmarkCase]] = {}
    for case in cases:
        if CaseLabel.ADVERSARIAL in case.labels:
            label = "ADVERSARIAL"
        elif CaseLabel.NOISE in case.labels:
            label = "NOISE"
        else:
            label = "NORMAL"
        strata.setdefault((label, case.risk_class.value), []).append(case)

    sample: list[BenchmarkCase] = []
    for key in sorted(strata):
        bucket = sorted(strata[key], key=lambda c: c.request_id)
        rng.shuffle(bucket)
        sample.extend(bucket[:per_stratum])
    return sorted(sample, key=lambda c: c.request_id)
