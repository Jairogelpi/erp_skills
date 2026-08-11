"""Frozen synthetic benchmark annotations and split invariants."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

DATASET_SCHEMA_VERSION = "1.0"


class DatasetSplit(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    FINAL_TEST = "FINAL_TEST"


class RiskClass(str, Enum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"


class CaseLabel(str, Enum):
    NORMAL = "NORMAL"
    NOISE = "NOISE"
    ADVERSARIAL = "ADVERSARIAL"


class ExpectedDecision(str, Enum):
    ALLOW = "ALLOW"
    SIMULATE = "SIMULATE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"
    CLARIFY = "CLARIFY"
    ABSTAIN = "ABSTAIN"


class _Model(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class BenchmarkCase(_Model):
    schema_version: Literal["1.0"]
    request_id: str
    request_text: str
    canonical_intent: str
    paraphrase_group_id: str
    split: DatasetSplit
    expected_skill: str
    expected_arguments: dict[str, Any]
    expected_decision: ExpectedDecision
    initial_state: dict[str, Any]
    expected_final_state: dict[str, Any]
    clarification_required: bool
    approval_required: bool
    error_type: str
    risk_class: RiskClass
    module: str
    labels: set[CaseLabel]

    @field_validator(
        "request_id",
        "request_text",
        "canonical_intent",
        "paraphrase_group_id",
        "expected_skill",
        "error_type",
        "module",
    )
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonblank")
        return value

    @model_validator(mode="after")
    def valid_labels(self):
        abnormal = {CaseLabel.NOISE, CaseLabel.ADVERSARIAL}
        if (CaseLabel.NORMAL in self.labels) != (not bool(self.labels & abnormal)):
            raise ValueError("NORMAL is exclusive with abnormal labels")
        return self


class SplitPlan(_Model):
    schema_version: Literal["1.0"]
    development_count: Literal[240] = 240
    validation_count: Literal[120] = 120
    final_test_count: Literal[120] = 120

    @property
    def total(self) -> int:
        return self.development_count + self.validation_count + self.final_test_count


def validate_case_groups(cases: list[BenchmarkCase]) -> None:
    """Check the declared paraphrase-group id does not cross splits.

    **This is NOT sufficient on its own.** When every case is its own
    group, this check is vacuous -- a group of size 1 cannot cross
    anything -- and it passed while 10 identical request texts sat in both
    DEVELOPMENT and FINAL_TEST. Always pair it with
    `validate_no_split_leakage`, which checks the text and the
    (intent, arguments) pair and is proven non-vacuous by a planted leak.
    """
    groups: dict[str, DatasetSplit] = {}
    for case in cases:
        previous = groups.setdefault(case.paraphrase_group_id, case.split)
        if previous != case.split:
            raise ValueError("paraphrase group crosses splits")


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def validate_no_split_leakage(cases: list[BenchmarkCase]) -> None:
    """Reject any formulation that appears in more than one split.

    CLAUDE.md §17 forbids a paraphrase group *or a semantically equivalent
    formulation* from crossing partitions. `validate_case_groups` only
    checks the declared group id, which is vacuous when every case is its
    own group -- this checks the two things that actually matter:
    identical request text, and identical (intent, arguments).
    """
    by_text: dict[str, set[DatasetSplit]] = {}
    by_semantics: dict[tuple[str, str], set[DatasetSplit]] = {}

    for case in cases:
        by_text.setdefault(_normalize(case.request_text), set()).add(case.split)
        key = (
            case.canonical_intent,
            repr(sorted(case.expected_arguments.items())),
        )
        by_semantics.setdefault(key, set()).add(case.split)

    leaked_text = [t for t, splits in by_text.items() if len(splits) > 1]
    if leaked_text:
        raise ValueError(
            f"{len(leaked_text)} request text(s) appear in multiple splits; "
            f"first: {leaked_text[0]!r}"
        )

    leaked_semantics = [k for k, splits in by_semantics.items() if len(splits) > 1]
    if leaked_semantics:
        raise ValueError(
            f"{len(leaked_semantics)} (intent, arguments) pair(s) appear in "
            f"multiple splits; first: {leaked_semantics[0]}"
        )
