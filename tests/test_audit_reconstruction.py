"""TDD for erp_agent_os.audit_reconstruction (v2.1 plan, Task 6)."""

from erp_agent_os.audit_reconstruction import FACT_NAMES, reconstruct


def _complete_correct_trace() -> dict:
    return {
        "correlation_id": "corr-1",
        "request_text": "Crea una oportunidad para Acme por 15000 euros.",
        "case_id": "corr-1",
        "case_id_matches_correlation": True,
        "intent": "crm.create_opportunity.new",
        "arguments": {"customer_name": "Acme", "expected_revenue": 15000},
        "selected_skill_id": "crm.create_opportunity",
        "abstained": False,
        "policy_decision": "ALLOW",
        "role": "sales_user",
        "skill_version": "1.0.0",
        "handler": "erp_agent_os.handlers.crm.create_opportunity",
        "execution_output": "o1",
        "observed_state_delta": {"operation_kind": "create_one"},
        "verification_status": "passed",
        "approval_evidence": None,
        "final_decision_allowed": True,
    }


def test_complete_correct_trace_recovers_all_seven_facts():
    result = reconstruct(_complete_correct_trace())
    assert result.all_facts_success is True
    assert result.contradiction_count == 0
    assert set(result.facts) == set(FACT_NAMES)


def test_empty_trace_recovers_nothing():
    result = reconstruct({})
    assert result.all_facts_success is False
    assert result.coverage() < 0.5


def test_partial_trace_only_some_facts_present():
    trace = {
        "correlation_id": "corr-2",
        "request_text": "algo",
        "intent": "crm.create_opportunity.new",
        "arguments": {"customer_name": "Acme"},
    }
    result = reconstruct(trace)
    assert result.facts["request_and_case_identity"].present is True
    assert result.facts["intent_and_arguments"].present is True
    assert result.facts["selected_action_or_skill"].present is False
    assert result.all_facts_success is False


def test_complete_but_contradictory_trace_a_deny_that_actually_mutated():
    trace = _complete_correct_trace()
    trace["policy_decision"] = "DENY"
    trace["observed_state_delta"] = {"operation_kind": "create_one"}
    result = reconstruct(trace)
    assert result.facts["result_and_observed_effects"].contradictory is True
    assert result.facts["result_and_observed_effects"].recovered is False
    assert result.contradiction_count >= 1
    assert result.all_facts_success is False


def test_complete_but_contradictory_trace_allowed_without_approval_evidence():
    trace = _complete_correct_trace()
    trace["policy_decision"] = "REQUIRE_APPROVAL"
    trace["final_decision_allowed"] = True
    trace["approval_evidence"] = None
    result = reconstruct(trace)
    assert result.facts["verification_approval_or_block_evidence"].contradictory is True
    assert result.all_facts_success is False


def test_approval_evidence_present_resolves_the_contradiction():
    trace = _complete_correct_trace()
    trace["policy_decision"] = "REQUIRE_APPROVAL"
    trace["final_decision_allowed"] = True
    trace["approval_evidence"] = {"actor": "Jairo", "scope": "crm.create_opportunity"}
    result = reconstruct(trace)
    assert result.facts["verification_approval_or_block_evidence"].recovered is True


def test_abstained_case_does_not_require_a_selected_skill():
    trace = _complete_correct_trace()
    trace["abstained"] = True
    trace["selected_skill_id"] = None
    trace["policy_decision"] = "ABSTAIN"
    trace["observed_state_delta"] = {"operation_kind": "no_change"}
    trace["final_decision_allowed"] = False
    result = reconstruct(trace)
    assert result.facts["selected_action_or_skill"].present is True
    assert result.facts["selected_action_or_skill"].contradictory is False


def test_abstained_but_a_skill_was_also_selected_is_contradictory():
    trace = _complete_correct_trace()
    trace["abstained"] = True
    # selected_skill_id still set from the base fixture -- contradictory:
    # a genuinely abstained case cannot also have committed to a skill.
    result = reconstruct(trace)
    assert result.facts["selected_action_or_skill"].contradictory is True


def test_missing_version_is_not_a_defect_for_a_non_executing_decision():
    trace = _complete_correct_trace()
    trace["policy_decision"] = "DENY"
    trace["skill_version"] = None
    trace["handler"] = None
    trace["observed_state_delta"] = {"operation_kind": "no_change"}
    result = reconstruct(trace)
    assert result.facts["exact_tool_skill_handler_version"].recovered is True


def test_missing_version_is_a_defect_for_an_executing_decision():
    trace = _complete_correct_trace()
    trace["skill_version"] = None
    result = reconstruct(trace)
    assert result.facts["exact_tool_skill_handler_version"].present is False


def test_result_is_independent_of_system_name_label_in_the_trace():
    """Renaming the system inside the trace must not change the score --
    the reconstructor never branches on a 'system' field's value."""
    base = _complete_correct_trace()
    labeled_a = {**base, "system": "A"}
    labeled_c = {**base, "system": "C"}
    assert reconstruct(labeled_a) == reconstruct(labeled_c)


def test_result_is_independent_of_trace_key_order():
    base = _complete_correct_trace()
    reordered = dict(reversed(list(base.items())))
    assert reconstruct(base) == reconstruct(reordered)


def test_reconstruction_never_reads_a_gold_or_scenario_parameter():
    """Structural guarantee: reconstruct() takes exactly one positional
    parameter, the trace -- there is no gold/scenario argument it could
    be tempted to fall back on."""
    import inspect

    signature = inspect.signature(reconstruct)
    assert list(signature.parameters) == ["trace"]
