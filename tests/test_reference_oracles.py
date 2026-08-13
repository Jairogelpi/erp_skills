"""TDD for the two independent v2.1 oracles (Task 3).

docs/tfm-closure-no-human-v2.1.md section 4.2/4.3: these oracles answer
what SHOULD happen, built from their own truth tables/semantics, never
by calling production policy/runtime code. The AST import scan is what
makes that a real architectural guarantee rather than a docstring
promise.
"""

import ast
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from erp_agent_os.reference_policy_oracle import (
    ReferenceDecision,
    ReferencePolicyOracleError,
    reference_policy,
)
from erp_agent_os.reference_state_oracle import (
    ReferenceOperationKind,
    ReferenceStateOracleError,
    apply_reference_transition,
)

ORACLE_MODULES = (
    Path("src/erp_agent_os/reference_policy_oracle.py"),
    Path("src/erp_agent_os/reference_state_oracle.py"),
)

GENERATOR_MODULES = (
    Path("src/erp_agent_os/scenarios_v2_1.py"),
    Path("src/erp_agent_os/security_scenarios_v2_1.py"),
)

FORBIDDEN_IMPORT_ROOTS = (
    "erp_agent_os.policy",
    "erp_agent_os.runtime",
    "erp_agent_os.handlers",
    "erp_agent_os.adapters",
    "erp_agent_os.system_a",
    "erp_agent_os.system_b",
    "erp_agent_os.system_c",
    "erp_agent_os.retrieval",
    "erp_agent_os.catalog",
    "erp_agent_os.experiment",
)

FORBIDDEN_ORACLE_IMPORTS = (
    "erp_agent_os.reference_policy_oracle",
    "erp_agent_os.reference_state_oracle",
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


@pytest.mark.parametrize("module_path", ORACLE_MODULES)
def test_oracle_modules_never_import_production_execution_code(module_path):
    imported = _imported_module_names(module_path)
    for forbidden in FORBIDDEN_IMPORT_ROOTS:
        hit = [
            name
            for name in imported
            if name == forbidden or name.startswith(forbidden + ".")
        ]
        assert not hit, f"{module_path} imports forbidden module(s): {hit}"


@pytest.mark.parametrize("module_path", GENERATOR_MODULES)
def test_generators_never_import_the_oracles_either(module_path):
    """Section 4.2: independence is bidirectional. A generator that
    imported the oracle to fill in expected_decision/expected_state_delta
    would make the later concordance check a tautology."""
    imported = _imported_module_names(module_path)
    hit = [name for name in imported if name in FORBIDDEN_ORACLE_IMPORTS]
    assert not hit, (
        f"{module_path} imports the oracle(s) it must stay independent of: {hit}"
    )


# ---------------------------------------------- full-corpus concordance


def _independent_expected_decision(scenario) -> str:
    """Re-derives the decision from the scenario's raw attributes using
    ONLY the oracle -- never scenario.expected_decision -- so comparing
    the two is a real check on two independent implementations."""
    blocking_signal = scenario.case_kind == "adversarial"
    return reference_policy(
        role=scenario.actor_role,
        risk_class=scenario.risk_class,
        operation=scenario.operation,
        blocking_signal=blocking_signal,
    ).value


def _independent_expected_operation_kind(scenario) -> str:
    if scenario.expected_decision not in ("ALLOW", "SIMULATE"):
        return "no_change"
    if scenario.risk_class == "R3":
        return "confirm_document"
    if scenario.operation == "create":
        return "create_one"
    if scenario.operation == "update":
        return "update_one_allowed_field"
    return "read_only"


def test_full_corpus_oracle_concordance_main_benchmark():
    from erp_agent_os.scenarios_v2_1 import CASE_KIND_NO_SKILL, generate_scenarios

    mismatches = []
    for scenario in generate_scenarios():
        if scenario.case_kind == CASE_KIND_NO_SKILL:
            # ABSTAIN is a retrieval-layer outcome: no skill was matched,
            # so there is no risk_class/operation for reference_policy to
            # reason about at all -- the same reason production policy.
            # decide() is only ever called after retrieval succeeds. Not a
            # policy-oracle concern; excluded from this concordance check
            # rather than papered over with a fabricated ABSTAIN branch in
            # the oracle that no real risk-tier reasoning would produce.
            assert scenario.expected_decision == "ABSTAIN"
            assert scenario.expected_state_delta == {"operation_kind": "no_change"}
            continue
        oracle_decision = _independent_expected_decision(scenario)
        if oracle_decision != scenario.expected_decision:
            mismatches.append(
                (
                    scenario.scenario_id,
                    "decision",
                    scenario.expected_decision,
                    oracle_decision,
                )
            )
        oracle_kind = _independent_expected_operation_kind(scenario)
        declared_kind = scenario.expected_state_delta["operation_kind"]
        if oracle_kind != declared_kind:
            mismatches.append(
                (scenario.scenario_id, "delta_kind", declared_kind, oracle_kind)
            )
    assert not mismatches, mismatches


def test_full_corpus_oracle_concordance_security_population():
    from erp_agent_os.security_scenarios_v2_1 import generate_security_population

    dangerous, safe = generate_security_population()
    mismatches = []
    for scenario in (*dangerous, *safe):
        oracle_decision = _independent_expected_decision(scenario)
        if oracle_decision != scenario.expected_decision:
            mismatches.append(
                (
                    scenario.scenario_id,
                    "decision",
                    scenario.expected_decision,
                    oracle_decision,
                )
            )
        oracle_kind = _independent_expected_operation_kind(scenario)
        declared_kind = scenario.expected_state_delta["operation_kind"]
        if oracle_kind != declared_kind:
            mismatches.append(
                (scenario.scenario_id, "delta_kind", declared_kind, oracle_kind)
            )
    assert not mismatches, mismatches


# --------------------------------------------------------- policy oracle


@pytest.mark.parametrize(
    ("role", "risk", "operation", "expected"),
    [
        ("reader", "R1", "create", ReferenceDecision.DENY),
        ("sales_user", "R1", "create", ReferenceDecision.ALLOW),
        ("sales_user", "R3", "confirm", ReferenceDecision.REQUIRE_APPROVAL),
        ("admin", "R4", "delete", ReferenceDecision.DENY),
    ],
)
def test_reference_policy_truth_table(role, risk, operation, expected):
    assert reference_policy(role=role, risk_class=risk, operation=operation) == expected


def test_r2_allows_only_once_approved():
    assert (
        reference_policy(role="sales_user", risk_class="R2", operation="update")
        == ReferenceDecision.REQUIRE_APPROVAL
    )
    assert (
        reference_policy(
            role="sales_user",
            risk_class="R2",
            operation="update",
            approval_granted=True,
        )
        == ReferenceDecision.ALLOW
    )


def test_r3_only_ever_simulates_even_when_approved():
    assert (
        reference_policy(
            role="sales_user",
            risk_class="R3",
            operation="confirm",
            approval_granted=True,
        )
        == ReferenceDecision.SIMULATE
    )


def test_r4_denies_regardless_of_role_or_approval():
    assert (
        reference_policy(
            role="admin", risk_class="R4", operation="delete", approval_granted=True
        )
        == ReferenceDecision.DENY
    )


def test_blocking_signal_denies_before_risk_tier_reasoning():
    assert (
        reference_policy(
            role="sales_user",
            risk_class="R1",
            operation="create",
            blocking_signal=True,
        )
        == ReferenceDecision.DENY
    )


def test_unknown_risk_class_raises():
    with pytest.raises(ReferencePolicyOracleError):
        reference_policy(role="sales_user", risk_class="R9", operation="create")


# ---------------------------------------------------------- state oracle


def test_create_one_adds_exactly_one_record():
    before: tuple[dict, ...] = ()
    after = apply_reference_transition(
        operation_kind="create_one",
        collection=before,
        new_fields={"customer_name": "Acme", "expected_revenue": 15000},
    )
    assert len(after) == 1
    assert after[0]["customer_name"] == "Acme"


def test_update_one_allowed_field_changes_only_that_field():
    before = ({"id": "o1", "customer_name": "Acme", "expected_revenue": 15000},)
    after = apply_reference_transition(
        operation_kind="update_one_allowed_field",
        collection=before,
        match={"id": "o1"},
        field_name="expected_revenue",
        field_value=27000,
    )
    assert after[0]["expected_revenue"] == 27000
    assert after[0]["customer_name"] == "Acme"


def test_update_requires_exactly_one_match():
    before = (
        {"id": "o1", "customer_name": "Acme"},
        {"id": "o2", "customer_name": "Acme"},
    )
    with pytest.raises(ReferenceStateOracleError):
        apply_reference_transition(
            operation_kind="update_one_allowed_field",
            collection=before,
            match={"customer_name": "Acme"},
            field_name="expected_revenue",
            field_value=1,
        )


def test_append_line_adds_one_line_item():
    before = ({"id": "q1", "lines": []},)
    after = apply_reference_transition(
        operation_kind="append_line",
        collection=before,
        match={"id": "q1"},
        line_item={"product_name": "Widget", "quantity": 3},
    )
    assert after[0]["lines"] == [{"product_name": "Widget", "quantity": 3}]


def test_confirm_document_sets_state_confirmed():
    before = ({"id": "s1", "state": "draft"},)
    after = apply_reference_transition(
        operation_kind="confirm_document", collection=before, match={"id": "s1"}
    )
    assert after[0]["state"] == "confirmed"


@given(st.integers(min_value=0, max_value=5))
def test_deny_abstain_clarify_never_changes_state(n_records):
    """A DENY/ABSTAIN/CLARIFY decision corresponds to read_only or
    no_change at the state layer -- neither must ever mutate the
    collection, for any starting cardinality."""
    before = tuple({"id": f"r{i}"} for i in range(n_records))
    for kind in (
        ReferenceOperationKind.READ_ONLY,
        ReferenceOperationKind.NO_CHANGE,
    ):
        after = apply_reference_transition(operation_kind=kind.value, collection=before)
        assert after == before


def test_retry_preserves_cardinality():
    """An idempotent replay is represented as no_change against the
    already-mutated collection: applying it must not add a second
    record."""
    after_first = apply_reference_transition(
        operation_kind="create_one",
        collection=(),
        new_fields={"customer_name": "Acme"},
    )
    after_retry = apply_reference_transition(
        operation_kind="no_change", collection=after_first
    )
    assert len(after_retry) == len(after_first) == 1


def test_original_collection_is_never_mutated_in_place():
    before = ({"id": "o1", "expected_revenue": 15000},)
    apply_reference_transition(
        operation_kind="update_one_allowed_field",
        collection=before,
        match={"id": "o1"},
        field_name="expected_revenue",
        field_value=99999,
    )
    assert before[0]["expected_revenue"] == 15000


def test_unknown_operation_kind_raises():
    with pytest.raises(ReferenceStateOracleError):
        apply_reference_transition(operation_kind="delete_everything", collection=())
