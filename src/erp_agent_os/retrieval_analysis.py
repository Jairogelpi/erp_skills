"""Reproducible H5/H6 precision-coverage analysis for the frozen retriever."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Protocol

from erp_agent_os.dataset import (
    ABSTENTION_SENTINEL,
    BenchmarkCase,
    ExpectedDecision,
)
from erp_agent_os.retrieval import RetrievalCandidate, should_abstain

THRESHOLD_GRID = tuple(step / 100 for step in range(0, 61, 5))
DEFAULT_MARGIN = 0.05


class Retriever(Protocol):
    def rank(
        self, query: str, *, role: str | None = None
    ) -> list[RetrievalCandidate]: ...


@dataclass(frozen=True)
class RetrievalCurvePoint:
    threshold: float
    margin: float
    n_cases: int
    n_expected_skill: int
    n_abstention_expected: int
    accepted: int
    abstained: int
    correct_reuses: int
    wrong_reuses: int
    correct_abstentions: int
    margin_abstentions: int
    coverage: float
    expected_skill_coverage: float
    abstention_rate: float
    selective_accuracy: float
    false_reuse_risk: float
    correct_abstention_rate: float
    false_abstention_rate: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def curve_configuration_hash(
    *, thresholds: Sequence[float] = THRESHOLD_GRID, margin: float = DEFAULT_MARGIN
) -> str:
    encoded = json.dumps(
        {"thresholds": list(thresholds), "margin": margin},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def precision_coverage_curve(
    cases: Sequence[BenchmarkCase],
    retriever: Retriever,
    *,
    thresholds: Sequence[float] = THRESHOLD_GRID,
    margin: float = DEFAULT_MARGIN,
    role: str = "erp_user",
) -> list[RetrievalCurvePoint]:
    """Evaluate fixed thresholds without tuning them on the supplied cases."""
    ranked_cases = [
        (case, retriever.rank(case.request_text, role=role)) for case in cases
    ]
    n_cases = len(ranked_cases)
    n_expected_skill = sum(
        case.expected_skill != ABSTENTION_SENTINEL for case, _ in ranked_cases
    )

    def expects_abstention(case: BenchmarkCase) -> bool:
        return (
            case.expected_skill == ABSTENTION_SENTINEL
            or case.clarification_required
            or case.expected_decision
            in {ExpectedDecision.ABSTAIN, ExpectedDecision.CLARIFY}
        )

    n_abstention_expected = sum(expects_abstention(case) for case, _ in ranked_cases)
    n_automatic_expected = n_cases - n_abstention_expected
    points: list[RetrievalCurvePoint] = []

    for threshold in thresholds:
        accepted = correct_reuses = wrong_reuses = correct_abstentions = 0
        accepted_expected_skill = margin_abstentions = false_abstentions = 0
        for case, ranked in ranked_cases:
            missing = ["required_information"] if case.clarification_required else []
            score_margin = (
                ranked[0].score - ranked[1].score if len(ranked) > 1 else float("inf")
            )
            abstain = should_abstain(
                ranked, missing, threshold=threshold, margin=margin
            )
            if abstain:
                if score_margin < margin:
                    margin_abstentions += 1
                if expects_abstention(case):
                    correct_abstentions += 1
                else:
                    false_abstentions += 1
                continue

            accepted += 1
            if case.expected_skill != ABSTENTION_SENTINEL:
                accepted_expected_skill += 1
            if ranked and ranked[0].skill.skill_id == case.expected_skill:
                correct_reuses += 1
            else:
                wrong_reuses += 1

        abstained = n_cases - accepted
        points.append(
            RetrievalCurvePoint(
                threshold=float(threshold),
                margin=margin,
                n_cases=n_cases,
                n_expected_skill=n_expected_skill,
                n_abstention_expected=n_abstention_expected,
                accepted=accepted,
                abstained=abstained,
                correct_reuses=correct_reuses,
                wrong_reuses=wrong_reuses,
                correct_abstentions=correct_abstentions,
                margin_abstentions=margin_abstentions,
                coverage=accepted / n_cases if n_cases else 0.0,
                expected_skill_coverage=(
                    accepted_expected_skill / n_expected_skill
                    if n_expected_skill
                    else 0.0
                ),
                abstention_rate=abstained / n_cases if n_cases else 0.0,
                selective_accuracy=(correct_reuses / accepted if accepted else 0.0),
                false_reuse_risk=wrong_reuses / accepted if accepted else 0.0,
                correct_abstention_rate=(
                    correct_abstentions / n_abstention_expected
                    if n_abstention_expected
                    else 0.0
                ),
                false_abstention_rate=(
                    false_abstentions / n_automatic_expected
                    if n_automatic_expected
                    else 0.0
                ),
            )
        )
    return points
