from dataclasses import FrozenInstanceError

import pytest

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.dataset import RiskClass
from erp_agent_os.policy import PolicyDecision
from erp_agent_os.runtime import (
    ExecutionResult,
    Runtime,
    UnregisteredHandlerError,
    VerificationCheck,
    VerificationCheckResult,
    VerificationStatus,
)
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState


def skill(**changes):
    data = {
        "skill_id": "crm.create_opportunity",
        "version": "1.0.0",
        "module": "crm",
        "operation": "create",
        "description": "Crea una oportunidad.",
        "risk_class": RiskClass.R1,
        "input_schema": {"type": "object"},
        "permissions": Permissions(allowed_roles=["sales_user"]),
        "preconditions": [],
        "execution": Execution(
            handler="erp_agent_os.skills.crm.create_opportunity",
            timeout_seconds=10,
            max_retries=1,
            idempotent=True,
        ),
        "postconditions": ["exactly_one_new_opportunity"],
        "state": SkillState.ACTIVE,
    }
    data.update(changes)
    return SkillDefinition(**data)


def create_opportunity(erp: FakeERPAdapter, args: dict) -> str:
    return erp.create("crm.lead", args)


def named_check(check_id: str, passed: bool = True) -> VerificationCheck:
    return VerificationCheck(check_id, lambda adapter, output: passed)


def test_verification_status_is_a_closed_six_value_contract():
    assert {status.value for status in VerificationStatus} == {
        "passed",
        "failed",
        "not_run_clean",
        "not_run_dirty",
        "replayed",
        "verifier_error",
    }


def test_named_check_and_check_result_are_immutable_public_contracts():
    check = named_check("state_unchanged")
    evidence = VerificationCheckResult("state_unchanged", True, "check passed")

    with pytest.raises(FrozenInstanceError):
        check.check_id = "changed"
    with pytest.raises(FrozenInstanceError):
        evidence.passed = False

    result = ExecutionResult(
        PolicyDecision.DENY,
        None,
        False,
        True,
        verification_status=VerificationStatus.NOT_RUN_CLEAN,
        check_results=(evidence,),
    )
    assert isinstance(result.check_results, tuple)
    with pytest.raises(FrozenInstanceError):
        result.verification_status = VerificationStatus.NOT_RUN_DIRTY


def test_allow_executes_handler_and_mutates_erp():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)

    result = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "key-1",
        postcondition_checks=(named_check("exactly_one_new_opportunity"),),
    )

    assert result.decision == PolicyDecision.ALLOW
    assert erp.get("crm.lead", result.output) == {"name": "Acme"}
    assert result.verification_status is VerificationStatus.PASSED
    assert result.postconditions_met is True


def test_deny_never_calls_handler():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)

    result = runtime.execute(
        skill(),
        {},
        "warehouse_user",
        "key-1",
        postcondition_checks=(named_check("state_unchanged"),),
    )

    assert result.decision == PolicyDecision.DENY
    assert result.output is None
    assert result.verification_status is VerificationStatus.NOT_RUN_CLEAN
    assert result.postconditions_met is True


def test_unregistered_handler_raises():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)

    with pytest.raises(UnregisteredHandlerError):
        runtime.execute(skill(), {"name": "Acme"}, "sales_user", "key-1")


def test_repeated_idempotency_key_replays_without_reinvoking_handler():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    calls = []

    def counting_handler(adapter: FakeERPAdapter, args: dict) -> str:
        calls.append(args)
        return adapter.create("crm.lead", args)

    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", counting_handler)

    check_calls = []

    def records_one_result(adapter, output):
        check_calls.append(output)
        return len(adapter.list("crm.lead")) == 1

    check = VerificationCheck("exactly_one_new_opportunity", records_one_result)
    first = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "same-key",
        postcondition_checks=(check,),
    )
    second = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "same-key",
        postcondition_checks=(check,),
    )

    assert len(calls) == 1
    assert len(check_calls) == 1
    assert first.output == second.output
    assert second.idempotent_replay is True
    assert second.verification_status is VerificationStatus.REPLAYED
    assert second.postconditions_met is first.postconditions_met
    assert second.check_results == first.check_results
    assert len(erp._records["crm.lead"]) == 1


def test_replay_preserves_the_original_mutable_output_snapshot():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    calls = []

    def mutable_output(adapter, args):
        calls.append(args)
        return {"results": ["original"]}

    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", mutable_output)
    check = named_check("results_returned")
    first = runtime.execute(
        skill(), {}, "sales_user", "mutable-key", postcondition_checks=(check,)
    )
    first.output["results"].append("tampered")

    replay = runtime.execute(
        skill(), {}, "sales_user", "mutable-key", postcondition_checks=(check,)
    )

    assert len(calls) == 1
    assert replay.output == {"results": ["original"]}
    replay.output["results"].append("second tamper")
    another_replay = runtime.execute(
        skill(), {}, "sales_user", "mutable-key", postcondition_checks=(check,)
    )
    assert another_replay.output == {"results": ["original"]}


def test_fully_evaluated_failed_verification_is_replayed_with_exact_evidence():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    handler_calls = []
    check_calls = []

    def handler(adapter, args):
        handler_calls.append(args)
        return adapter.create("crm.lead", args)

    def failing_check(adapter, output):
        check_calls.append(output)
        return False

    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", handler)
    check = VerificationCheck("expected_state", failing_check)

    first = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "failed-key",
        postcondition_checks=(check,),
    )
    replay = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "failed-key",
        postcondition_checks=(check,),
    )

    assert len(handler_calls) == len(check_calls) == 1
    assert first.verification_status is VerificationStatus.FAILED
    assert replay.verification_status is VerificationStatus.REPLAYED
    assert replay.postconditions_met is False
    assert replay.check_results == first.check_results


def test_postcondition_check_runs_and_can_fail():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)

    result = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "key-1",
        postcondition_checks=(named_check("exactly_one_new_opportunity", False),),
    )

    assert result.postconditions_met is False
    assert result.verification_status is VerificationStatus.FAILED
    assert result.check_results == (
        VerificationCheckResult(
            "exactly_one_new_opportunity", False, "check failed"
        ),
    )


def test_runtime_collects_every_named_check_without_short_circuiting():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)
    calls = []

    def result(check_id, passed):
        def evaluate(adapter, output):
            calls.append(check_id)
            return passed

        return VerificationCheck(check_id, evaluate)

    execution = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "key-all",
        postcondition_checks=(result("first", False), result("second", True)),
    )

    assert calls == ["first", "second"]
    assert execution.verification_status is VerificationStatus.FAILED
    assert execution.postconditions_met is False
    assert [(item.check_id, item.passed) for item in execution.check_results] == [
        ("first", False),
        ("second", True),
    ]


def test_raised_check_is_non_sensitive_verifier_error_and_later_checks_run():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)
    calls = []

    def raises(adapter, output):
        calls.append("raises")
        raise RuntimeError("customer secret: top-secret")

    def later(adapter, output):
        calls.append("later")
        return True

    result = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "key-error",
        postcondition_checks=(
            VerificationCheck("raises", raises),
            VerificationCheck("later", later),
        ),
    )

    assert calls == ["raises", "later"]
    assert result.verification_status is VerificationStatus.VERIFIER_ERROR
    assert result.postconditions_met is None
    assert result.check_results == (
        VerificationCheckResult("raises", None, "check raised an exception"),
        VerificationCheckResult("later", True, "check passed"),
    )
    assert "top-secret" not in repr(result.check_results)


def test_unverified_handler_attempt_replays_without_duplicate_mutation():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    calls = []

    def counting_handler(adapter, args):
        calls.append(args)
        return adapter.create("crm.lead", args)

    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", counting_handler)

    first = runtime.execute(skill(), {"name": "Acme"}, "sales_user", "unsafe-key")
    second = runtime.execute(skill(), {"name": "Acme"}, "sales_user", "unsafe-key")

    assert len(calls) == 1
    assert len(erp._records["crm.lead"]) == 1
    assert first.verification_status is VerificationStatus.VERIFIER_ERROR
    assert second.verification_status is VerificationStatus.REPLAYED
    assert first.postconditions_met is second.postconditions_met is None
    assert first.idempotent_replay is False
    assert second.idempotent_replay is True
    assert second.output == first.output
    assert second.check_results == first.check_results == ()


def test_verifier_error_attempt_replays_exact_evidence_without_rerunning_checks():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    handler_calls = []
    check_calls = []

    def handler(adapter, args):
        handler_calls.append(args)
        return adapter.create("crm.lead", args)

    def raises(adapter, output):
        check_calls.append(output)
        raise RuntimeError("secret that must not escape")

    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", handler)
    check = VerificationCheck("expected_state", raises)

    first = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "error-key",
        postcondition_checks=(check,),
    )
    replay = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "error-key",
        postcondition_checks=(check,),
    )

    assert len(handler_calls) == len(check_calls) == 1
    assert first.verification_status is VerificationStatus.VERIFIER_ERROR
    assert replay.verification_status is VerificationStatus.REPLAYED
    assert replay.postconditions_met is None
    assert replay.check_results == first.check_results


def test_unnamed_callable_cannot_create_auditable_verification_evidence():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)
    calls = []

    def unnamed(adapter, output):
        calls.append(output)
        return True

    result = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "key-unnamed",
        postcondition_checks=(unnamed,),
    )

    assert calls == []
    assert result.verification_status is VerificationStatus.VERIFIER_ERROR
    assert result.postconditions_met is None
    assert result.check_results == ()


@pytest.mark.parametrize(
    ("risk_class", "role", "approval_granted", "expected_decision"),
    [
        (RiskClass.R1, "warehouse_user", False, PolicyDecision.DENY),
        (RiskClass.R2, "sales_user", False, PolicyDecision.REQUIRE_APPROVAL),
        (RiskClass.R3, "sales_user", True, PolicyDecision.SIMULATE),
    ],
)
def test_non_executing_paths_verify_a_named_complete_state_invariant(
    risk_class, role, approval_granted, expected_decision
):
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)

    result = runtime.execute(
        skill(risk_class=risk_class),
        {"name": "Acme"},
        role,
        f"key-{expected_decision.value}",
        approval_granted=approval_granted,
        postcondition_checks=(named_check("state_unchanged"),),
    )

    assert result.decision is expected_decision
    assert result.verification_status is VerificationStatus.NOT_RUN_CLEAN
    assert result.postconditions_met is True
    assert result.output is None
    if expected_decision is PolicyDecision.SIMULATE:
        assert result.preview is not None
    else:
        assert result.preview is None


def test_non_executing_false_invariant_is_not_run_dirty():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)

    result = runtime.execute(
        skill(),
        {},
        "warehouse_user",
        "key-dirty",
        postcondition_checks=(named_check("state_unchanged", False),),
    )

    assert result.verification_status is VerificationStatus.NOT_RUN_DIRTY
    assert result.postconditions_met is False


@pytest.mark.parametrize(
    "checks",
    [(), (VerificationCheck("state_unchanged", lambda a, o: 1 / 0),)],
)
def test_non_executing_missing_or_raised_invariant_is_verifier_error(checks):
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)

    result = runtime.execute(
        skill(),
        {},
        "warehouse_user",
        "key-non-exec-error",
        postcondition_checks=checks,
    )

    assert result.verification_status is VerificationStatus.VERIFIER_ERROR
    assert result.postconditions_met is None


def test_handler_unknown_record_error_is_caught_not_raised():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)

    def failing_handler(adapter, args):
        return adapter.get("crm.lead", "does-not-exist")

    runtime.register("crm.create_opportunity", "1.0.0", failing_handler)

    result = runtime.execute(skill(), {}, "sales_user", "key-1")

    assert result.output is None
    assert result.handler_error is not None
    assert result.decision == PolicyDecision.ALLOW
    assert result.verification_status is VerificationStatus.VERIFIER_ERROR
    assert result.postconditions_met is None


def test_handler_error_attempt_is_replayed_without_reinvoking_handler():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    calls = []

    def failing_handler(adapter, args):
        calls.append(args)
        return adapter.get("crm.lead", "does-not-exist")

    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", failing_handler)

    first = runtime.execute(skill(), {}, "sales_user", "handler-error-key")
    replay = runtime.execute(skill(), {}, "sales_user", "handler-error-key")

    assert len(calls) == 1
    assert first.verification_status is VerificationStatus.VERIFIER_ERROR
    assert replay.verification_status is VerificationStatus.REPLAYED
    assert replay.postconditions_met is None
    assert replay.handler_error == first.handler_error
    assert replay.check_results == first.check_results == ()


def test_arbitrary_handler_failure_after_mutation_is_contained_and_replayed():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    calls = []

    def mutates_then_raises(adapter, args):
        calls.append(args)
        adapter.create("crm.lead", {"name": "Acme"})
        raise RuntimeError("customer secret: top-secret")

    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", mutates_then_raises)

    first = runtime.execute(skill(), {}, "sales_user", "runtime-error-key")
    replay = runtime.execute(skill(), {}, "sales_user", "runtime-error-key")

    assert len(calls) == 1
    assert len(erp._records["crm.lead"]) == 1
    assert first.verification_status is VerificationStatus.VERIFIER_ERROR
    assert first.postconditions_met is None
    assert first.handler_error == "RuntimeError: handler execution failed"
    assert "top-secret" not in first.handler_error
    assert first.check_results == ()
    assert replay.verification_status is VerificationStatus.REPLAYED
    assert replay.idempotent_replay is True
    assert replay.postconditions_met is None
    assert replay.handler_error == first.handler_error
    assert replay.check_results == first.check_results


def test_handler_key_error_from_mismatched_args_is_caught_not_raised():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)

    def handler_expecting_other_args(adapter, args):
        return args["field_this_skill_never_provides"]

    runtime.register("crm.create_opportunity", "1.0.0", handler_expecting_other_args)

    result = runtime.execute(skill(), {"name": "Acme"}, "sales_user", "key-1")

    assert result.output is None
    assert result.handler_error is not None
    assert "KeyError" in result.handler_error
    assert result.verification_status is VerificationStatus.VERIFIER_ERROR


def test_runtime_accepts_any_erp_adapter_structurally_not_just_fakeerp():
    # Runtime is generic over the adapter type (docs/odoo-demo.md):
    # a minimal object that only implements the ErpAdapter Protocol's
    # methods, not FakeERPAdapter at all, must work as a drop-in.
    class MinimalAdapter:
        def __init__(self):
            self.created = []

        def create(self, model, fields):
            self.created.append((model, fields))
            return "real-id-1"

        def get(self, model, record_id):
            return {"name": "x"}

        def list(self, model):
            return {}

        def update(self, model, record_id, fields):
            pass

    adapter = MinimalAdapter()
    runtime: Runtime = Runtime(adapter)

    def handler(erp, args):
        return erp.create("crm.lead", {"name": args["name"]})

    runtime.register("crm.create_opportunity", "1.0.0", handler)
    result = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "key-minimal",
        postcondition_checks=(named_check("created_record_exists"),),
    )

    assert result.output == "real-id-1"
    assert adapter.created == [("crm.lead", {"name": "Acme"})]
