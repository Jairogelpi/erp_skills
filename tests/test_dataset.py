import pytest
from pydantic import ValidationError

from erp_agent_os.dataset import (
    BenchmarkCase,
    CaseLabel,
    DatasetSplit,
    ExpectedDecision,
    RiskClass,
    SplitPlan,
    validate_case_groups,
)


def case(**changes):
    data = {
        "schema_version": "1.0",
        "request_id": "r1",
        "request_text": "help",
        "canonical_intent": "x",
        "paraphrase_group_id": "g1",
        "split": DatasetSplit.DEVELOPMENT,
        "expected_skill": "sin_skill/abstención",
        "expected_arguments": {},
        "expected_decision": ExpectedDecision.ABSTAIN,
        "initial_state": {},
        "expected_final_state": {},
        "clarification_required": False,
        "approval_required": False,
        "error_type": "none",
        "risk_class": RiskClass.R0,
        "module": "sales",
        "labels": {CaseLabel.NORMAL},
    }
    data.update(changes)
    return data


def test_complete_case_and_fixed_split_plan():
    assert BenchmarkCase(**case()).expected_skill == "sin_skill/abstención"
    assert SplitPlan(schema_version="1.0").total == 480


@pytest.mark.parametrize(
    "changes", [{"request_text": None}, {"labels": {CaseLabel.NORMAL, CaseLabel.NOISE}}]
)
def test_case_rejects_missing_or_inconsistent_annotations(changes):
    with pytest.raises(ValidationError):
        BenchmarkCase(**case(**changes))


def test_rejects_changed_allocation_and_group_leakage():
    invalid_plan = {"schema_version": "1.0", "development_count": 239}
    with pytest.raises(ValidationError):
        SplitPlan(**invalid_plan)
    cases = [
        BenchmarkCase(**case()),
        BenchmarkCase(**case(split=DatasetSplit.VALIDATION)),
    ]
    with pytest.raises(ValueError):
        validate_case_groups(cases)


def test_allows_abnormal_overlap_but_rejects_normal_overlap():
    assert BenchmarkCase(
        **case(labels={CaseLabel.NOISE, CaseLabel.ADVERSARIAL})
    ).labels == {CaseLabel.NOISE, CaseLabel.ADVERSARIAL}
    with pytest.raises(ValidationError):
        BenchmarkCase(**case(labels={CaseLabel.NORMAL, CaseLabel.NOISE}))
