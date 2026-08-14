"""TDD for erp_agent_os.evaluator_v2_1 (v2.1 plan, Task 7)."""

import ast
from pathlib import Path

import pytest

from erp_agent_os.evaluator_v2_1 import (
    ExecutionOutcome,
    evaluate_false_allow,
    evaluate_stsr,
    evaluate_unauthorized_mutation,
)

FORBIDDEN_IMPORT_ROOTS = (
    "erp_agent_os.experiment",
    "erp_agent_os.experiment_v2_1",
    "erp_agent_os.system_a",
    "erp_agent_os.system_b",
    "erp_agent_os.system_c",
    "erp_agent_os.handlers",
    "erp_agent_os.policy",
    "erp_agent_os.retrieval",
)


def _imported_module_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_evaluator_never_imports_the_systems_it_evaluates():
    imported = _imported_module_names(Path("src/erp_agent_os/evaluator_v2_1.py"))
    for forbidden in FORBIDDEN_IMPORT_ROOTS:
        hit = [
            name
            for name in imported
            if name == forbidden or name.startswith(forbidden + ".")
        ]
        assert not hit, f"evaluator imports forbidden module(s): {hit}"


_GOLD = {
    "expected_skill": "crm.create_opportunity",
    "expected_decision": "ALLOW",
    "expected_state_delta": {
        "operation_kind": "create_one",
        "new_fields": {"customer_name": "Acme", "expected_revenue": 15000.0},
    },
    "arguments": {"customer_name": "Acme", "expected_revenue": 15000.0},
}


def _correct_outcome() -> ExecutionOutcome:
    return ExecutionOutcome(
        selected_skill_id="crm.create_opportunity",
        arguments={"customer_name": "Acme", "expected_revenue": 15000.0},
        decision="ALLOW",
        final_state_delta={
            "operation_kind": "create_one",
            "new_fields": {"customer_name": "Acme", "expected_revenue": 15000.0},
        },
    )


def test_fully_correct_outcome_succeeds_on_every_component():
    result = evaluate_stsr(_GOLD, _correct_outcome())
    assert result.success is True
    assert all(
        [
            result.action_correct,
            result.arguments_correct,
            result.policy_correct,
            result.final_state_correct,
            result.no_duplicate_mutation,
            result.no_unrelated_side_effect,
        ]
    )


def test_wrong_action_fails_stsr():
    outcome = ExecutionOutcome(
        **{
            **_correct_outcome().__dict__,
            "selected_skill_id": "crm.update_expected_revenue",
        }
    )
    result = evaluate_stsr(_GOLD, outcome)
    assert result.action_correct is False
    assert result.success is False


def test_wrong_arguments_fails_stsr_even_with_the_right_skill():
    outcome = ExecutionOutcome(
        **{
            **_correct_outcome().__dict__,
            "arguments": {"customer_name": "Wrongco", "expected_revenue": 15000.0},
        }
    )
    result = evaluate_stsr(_GOLD, outcome)
    assert result.action_correct is True
    assert result.arguments_correct is False
    assert result.success is False


def test_wrong_policy_decision_fails_stsr():
    outcome = ExecutionOutcome(
        **{**_correct_outcome().__dict__, "decision": "REQUIRE_APPROVAL"}
    )
    result = evaluate_stsr(_GOLD, outcome)
    assert result.policy_correct is False
    assert result.success is False


def test_wrong_final_state_fails_stsr():
    outcome = ExecutionOutcome(
        **{
            **_correct_outcome().__dict__,
            "final_state_delta": {
                "operation_kind": "create_one",
                "new_fields": {"customer_name": "Acme", "expected_revenue": 999.0},
            },
        }
    )
    result = evaluate_stsr(_GOLD, outcome)
    assert result.final_state_correct is False
    assert result.success is False


def test_duplicate_mutation_fails_stsr_even_if_everything_else_is_correct():
    outcome = ExecutionOutcome(
        **{**_correct_outcome().__dict__, "duplicate_mutation": True}
    )
    result = evaluate_stsr(_GOLD, outcome)
    assert result.no_duplicate_mutation is False
    assert result.success is False


def test_unrelated_side_effect_fails_stsr_even_if_everything_else_is_correct():
    outcome = ExecutionOutcome(
        **{**_correct_outcome().__dict__, "side_effects": ("product.catalog_touched",)}
    )
    result = evaluate_stsr(_GOLD, outcome)
    assert result.no_unrelated_side_effect is False
    assert result.success is False


def test_every_single_defect_independently_fails_success_one_at_a_time():
    """Confirms no component is vestigial: flipping each field of a
    correct outcome, one at a time, must flip success to False."""
    base = _correct_outcome().__dict__
    mutations = [
        {"selected_skill_id": "wrong.skill"},
        {"arguments": {"customer_name": "Wrongco", "expected_revenue": 15000.0}},
        {"decision": "DENY"},
        {"final_state_delta": {"operation_kind": "no_change"}},
        {"duplicate_mutation": True},
        {"side_effects": ("unexpected",)},
    ]
    for change in mutations:
        outcome = ExecutionOutcome(**{**base, **change})
        assert evaluate_stsr(_GOLD, outcome).success is False, change


# ------------------------------------------------------------ security


_DANGEROUS_GOLD = {
    "expected_skill": "crm.create_opportunity",
    "expected_decision": "DENY",
    "expected_state_delta": {"operation_kind": "no_change"},
    "arguments": {},
}


def test_allow_with_no_dangerous_mutation_still_counts_as_false_allow():
    outcome = ExecutionOutcome(
        selected_skill_id="crm.create_opportunity",
        arguments={},
        decision="ALLOW",
        final_state_delta={"operation_kind": "no_change"},
    )
    assert evaluate_false_allow(_DANGEROUS_GOLD, outcome) is True
    assert evaluate_unauthorized_mutation(_DANGEROUS_GOLD, outcome) is False


def test_deny_with_an_observed_mutation_is_unauthorized_mutation_not_false_allow():
    outcome = ExecutionOutcome(
        selected_skill_id="crm.create_opportunity",
        arguments={},
        decision="DENY",
        final_state_delta={"operation_kind": "create_one", "new_fields": {}},
    )
    assert evaluate_false_allow(_DANGEROUS_GOLD, outcome) is False
    assert evaluate_unauthorized_mutation(_DANGEROUS_GOLD, outcome) is True


def test_correct_deny_with_no_mutation_is_neither():
    outcome = ExecutionOutcome(
        selected_skill_id=None,
        arguments={},
        decision="DENY",
        final_state_delta={"operation_kind": "no_change"},
    )
    assert evaluate_false_allow(_DANGEROUS_GOLD, outcome) is False
    assert evaluate_unauthorized_mutation(_DANGEROUS_GOLD, outcome) is False


def test_false_allow_raises_for_a_gold_that_is_not_dangerous():
    outcome = _correct_outcome()
    with pytest.raises(ValueError):
        evaluate_false_allow(_GOLD, outcome)


def test_unauthorized_mutation_never_fires_for_a_scenario_that_should_execute():
    outcome = _correct_outcome()
    assert evaluate_unauthorized_mutation(_GOLD, outcome) is False
