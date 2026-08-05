import pytest

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.dataset import RiskClass
from erp_agent_os.policy import PolicyDecision
from erp_agent_os.runtime import Runtime, UnregisteredHandlerError
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


def test_allow_executes_handler_and_mutates_erp():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)

    result = runtime.execute(skill(), {"name": "Acme"}, "sales_user", "key-1")

    assert result.decision == PolicyDecision.ALLOW
    assert erp.get("crm.lead", result.output) == {"name": "Acme"}


def test_deny_never_calls_handler():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)

    result = runtime.execute(skill(), {}, "warehouse_user", "key-1")

    assert result.decision == PolicyDecision.DENY
    assert result.output is None


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

    first = runtime.execute(skill(), {"name": "Acme"}, "sales_user", "same-key")
    second = runtime.execute(skill(), {"name": "Acme"}, "sales_user", "same-key")

    assert len(calls) == 1
    assert first.output == second.output
    assert second.idempotent_replay is True
    assert len(erp._records["crm.lead"]) == 1


def test_postcondition_check_runs_and_can_fail():
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    runtime = Runtime(erp)
    runtime.register("crm.create_opportunity", "1.0.0", create_opportunity)

    result = runtime.execute(
        skill(),
        {"name": "Acme"},
        "sales_user",
        "key-1",
        postcondition_checks=(lambda adapter, output: False,),
    )

    assert result.postconditions_met is False


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
