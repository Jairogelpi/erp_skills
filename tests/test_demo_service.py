"""What the comparison screen claims must be what the systems actually do.

Every assertion here is about behaviour the demo displays. If a scene
stops behaving as the UI says it does, this file fails rather than the
demo quietly showing something else on stage.
"""

from __future__ import annotations

from erp_agent_os.demo_service import SCENARIOS, DemoService, _fresh_erp, _records


def test_all_three_systems_start_from_an_identical_seeded_state():
    """Otherwise the before/after panels are not comparable at all."""
    scenario = SCENARIOS["approval"]
    states = [_records(_fresh_erp(scenario)) for _ in range(3)]
    assert states[0] == states[1] == states[2]
    assert states[0]["crm.opportunity"]["OPP-47"]["expected_revenue"] == 27000


def test_r2_change_requires_approval_and_leaves_the_erp_untouched():
    """The headline scene: C decides before writing, not after."""
    run = DemoService().run("approval")
    c = run.results["C"]
    assert c.risk_class == "R2"
    assert c.policy_decision == "REQUIRE_APPROVAL"
    assert c.execution_status == "not executed"
    # Proven by re-reading the store, not by trusting the decision.
    assert c.erp.changed is False
    assert c.erp.after["crm.opportunity"]["OPP-47"]["expected_revenue"] == 27000


def test_ungoverned_systems_mutate_the_same_request_immediately():
    """The contrast only exists if A and B really do write."""
    run = DemoService().run("approval")
    for name in ("A", "B"):
        result = run.results[name]
        assert result.erp.changed is True, name
        assert (
            result.erp.after["crm.opportunity"]["OPP-47"]["expected_revenue"] == 49500
        )


def test_approval_then_rerun_executes_and_verifies_the_postcondition():
    service = DemoService()
    run = service.run("approval")
    service.approve(run.request_id, "Demo Administrator")
    rerun = service.rerun(run.request_id)

    c = rerun.results["C"]
    assert c.policy_decision == "ALLOW"
    assert c.erp.changed is True
    assert c.erp.after["crm.opportunity"]["OPP-47"]["expected_revenue"] == 49500
    # SystemC.handle never passes postcondition checks to the runtime, so
    # this has to be resolved and run by the demo; asserting it here is
    # what stops the panel from showing an empty field as "verified".
    assert c.postcondition_verified is True
    assert c.postcondition_detail


def test_rerun_does_not_double_apply_the_ungoverned_systems():
    """A and B are left alone on re-run: re-running them would mutate
    twice and make their before/after panel misreport what happened."""
    service = DemoService()
    run = service.run("approval")
    before = run.results["A"].erp.after
    service.approve(run.request_id, "admin")
    rerun = service.rerun(run.request_id)
    assert rerun.results["A"].erp.after == before


def test_governed_system_also_executes_a_routine_request():
    """C must not read as 'the system that only says no'."""
    c = DemoService().run("normal").results["C"]
    assert c.policy_decision == "ALLOW"
    assert c.erp.changed is True
    assert c.postcondition_verified is True


def test_injection_scenario_is_denied_with_no_mutation():
    c = DemoService().run("security").results["C"]
    assert c.policy_decision == "DENY"
    assert c.erp.changed is False
    assert c.findings, "the injected instruction should surface a finding"


def test_ungoverned_systems_report_no_governance_fields():
    """A and B must not appear to have policy/risk/approval.

    Filling these with plausible defaults would erase exactly the
    difference §18 defines between the three architectures.
    """
    run = DemoService().run("approval")
    for name in ("A", "B"):
        result = run.results[name]
        assert result.risk_class is None, name
        assert result.policy_decision is None, name
        assert result.approval_status is None, name
        assert result.unavailable, name
    assert run.results["C"].risk_class is not None
    assert run.results["C"].policy_decision is not None


def test_system_c_spends_no_model_tokens():
    """C's retrieval is TF-IDF; it never calls the LLM. The token panel
    must not invent a cost for it."""
    assert DemoService().run("approval").results["C"].tokens == 0


def test_paraphrases_run_every_variant_through_every_system():
    service = DemoService()
    run = service.run("approval")
    _, variants, per_system = service.paraphrases(run.request_id)
    assert len(variants) == 3
    for name in ("A", "B", "C"):
        assert len(per_system[name]) == len(variants)
