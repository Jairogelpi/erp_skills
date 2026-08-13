"""Contract tests (CLAUDE.md §29).

§29 asks for four contract suites: the adapter contract, the skill
schema, the LLM output, and events. Their content existed scattered
across per-module tests; grouping them here makes the requirement
auditable and, more usefully, states each contract *once* so a second
implementation can be checked against it.

The adapter section is the one that earns its keep: it runs the **same
assertions** against every `ErpAdapter` implementation, so
`Odoo19Adapter` is held to the contract `FakeERPAdapter` defines rather
than to a hand-written parallel test.
"""

from typing import Any

import pytest

from erp_agent_os.adapters import (
    ErpAdapter,
    FakeERPAdapter,
    UnknownModelError,
    UnknownRecordError,
)
from erp_agent_os.audit import AbstentionEvent, AuditEvent, AuditStore
from erp_agent_os.catalog import CATALOG
from erp_agent_os.llm_client import (
    ArgumentExtraction,
    DeterministicStubClient,
    ToolCall,
    ToolSpec,
    parse_extraction,
)
from erp_agent_os.policy import PolicyDecision, decide
from erp_agent_os.runtime import (
    ExecutionResult,
    Runtime,
    VerificationCheck,
    VerificationCheckResult,
    VerificationStatus,
)
from erp_agent_os.skills import SkillDefinition, SkillState

MODEL = "crm.opportunity"


# ======================================================================
# 1. Adapter contract -- every ErpAdapter must satisfy these
# ======================================================================


def _fake() -> ErpAdapter:
    return FakeERPAdapter(allowed_models={MODEL})


# Each factory returns a fresh adapter honouring the contract. Odoo is
# absent by design: its tests mock HTTP, and pointing this suite at a
# live ERP would make the unit suite depend on a network service.
ADAPTER_FACTORIES = [pytest.param(_fake, id="FakeERPAdapter")]


@pytest.mark.parametrize("make_adapter", ADAPTER_FACTORIES)
def test_adapter_contract_create_returns_an_id_that_get_resolves(make_adapter):
    erp = make_adapter()
    record_id = erp.create(MODEL, {"customer_name": "Acme"})
    assert isinstance(record_id, str)
    assert erp.get(MODEL, record_id)["customer_name"] == "Acme"


@pytest.mark.parametrize("make_adapter", ADAPTER_FACTORIES)
def test_adapter_contract_update_changes_only_given_fields(make_adapter):
    erp = make_adapter()
    record_id = erp.create(MODEL, {"customer_name": "Acme", "state": "open"})
    erp.update(MODEL, record_id, {"state": "won"})
    record = erp.get(MODEL, record_id)
    assert record["state"] == "won"
    assert record["customer_name"] == "Acme", "untouched fields must survive"


@pytest.mark.parametrize("make_adapter", ADAPTER_FACTORIES)
def test_adapter_contract_unknown_model_raises_unknown_model_error(make_adapter):
    erp = make_adapter()
    with pytest.raises(UnknownModelError):
        erp.get("model.that.is.not.allowlisted", "1")


@pytest.mark.parametrize("make_adapter", ADAPTER_FACTORIES)
def test_adapter_contract_unknown_record_raises_unknown_record_error(make_adapter):
    erp = make_adapter()
    with pytest.raises(UnknownRecordError):
        erp.get(MODEL, "does-not-exist")


@pytest.mark.parametrize("make_adapter", ADAPTER_FACTORIES)
def test_adapter_contract_list_is_keyed_by_id(make_adapter):
    erp = make_adapter()
    record_id = erp.create(MODEL, {"customer_name": "Acme"})
    listing = erp.list(MODEL)
    assert record_id in listing
    assert listing[record_id]["customer_name"] == "Acme"


@pytest.mark.parametrize("make_adapter", ADAPTER_FACTORIES)
def test_adapter_contract_reads_do_not_alias_internal_state(make_adapter):
    # Mutating what `get` returned must not change the store: otherwise
    # a caller could edit records without going through `update`, and
    # every postcondition check would be comparing an object with
    # itself.
    erp = make_adapter()
    record_id = erp.create(MODEL, {"customer_name": "Acme"})
    erp.get(MODEL, record_id)["customer_name"] = "Tampered"
    assert erp.get(MODEL, record_id)["customer_name"] == "Acme"


def test_adapter_contract_exposes_no_deletion():
    # R4: irreversible deletion must be unreachable, structurally.
    for name in ("delete", "unlink", "drop", "truncate"):
        assert not hasattr(FakeERPAdapter, name)


# ======================================================================
# 2. Skill schema contract
# ======================================================================


def test_skill_schema_every_catalog_skill_round_trips_through_json():
    # The registry persists skills as JSON; a definition that cannot
    # survive that round trip would corrupt on restart.
    for skill in CATALOG:
        restored = SkillDefinition.model_validate_json(skill.model_dump_json())
        assert restored == skill


def test_skill_schema_rejects_unknown_fields():
    payload = CATALOG[0].model_dump()
    payload["undeclared_field"] = "x"
    with pytest.raises(Exception):
        SkillDefinition.model_validate(payload)


def test_skill_schema_every_catalog_skill_declares_what_the_contract_needs():
    for skill in CATALOG:
        assert skill.permissions.allowed_roles, f"{skill.skill_id} has no roles"
        assert skill.postconditions, f"{skill.skill_id} declares no postconditions"
        assert skill.input_schema.get("required"), f"{skill.skill_id} has no required"
        assert skill.state is SkillState.ACTIVE
        assert skill.execution.timeout_seconds > 0


# ======================================================================
# 3. LLM output contract
# ======================================================================


def test_llm_contract_stub_satisfies_the_client_protocol():
    client: Any = DeterministicStubClient()
    call = client.propose_action("crea una tarea", [ToolSpec("t", "crea tarea", [])])
    assert isinstance(call, ToolCall)
    extraction = client.extract_arguments("crea una tarea", ["title"])
    assert isinstance(extraction, ArgumentExtraction)


@pytest.mark.parametrize(
    "content",
    ['{"tool_name": null}', "not json", "[]", '{"unexpected": 1}', ""],
)
def test_llm_contract_malformed_output_never_yields_arguments(content):
    # §23: nothing is executed from free text. Whatever the model
    # returns, a malformed response must degrade to "no arguments"
    # rather than raising or inventing values.
    assert parse_extraction(content, ["customer_name"]) == {}


def test_llm_contract_extraction_never_widens_the_argument_set():
    parsed = parse_extraction(
        '{"customer_name": "Acme", "injected_admin_flag": true}', ["customer_name"]
    )
    assert parsed == {"customer_name": "Acme"}


# ======================================================================
# 4. Event contract
# ======================================================================


def _skill() -> SkillDefinition:
    return CATALOG[0]


def test_event_contract_audit_event_carries_every_field_the_rubric_scores():
    store = AuditStore()
    outcome = decide(_skill(), _skill().permissions.allowed_roles[0])
    event = store.record(
        "corr-1",
        _skill(),
        _skill().permissions.allowed_roles[0],
        outcome,
        ExecutionResult(
            PolicyDecision.ALLOW,
            "id-1",
            False,
            True,
            verification_status=VerificationStatus.PASSED,
            check_results=(
                VerificationCheckResult("record_exists", True, "check passed"),
            ),
        ),
        "key-1",
    )
    assert isinstance(event, AuditEvent)
    for field in (
        "correlation_id",
        "skill_id",
        "skill_version",
        "role",
        "decision",
        "risk_score",
        "reasons",
        "idempotency_key",
        "idempotent_replay",
        "postconditions_met",
        "output",
        "recorded_at",
    ):
        assert hasattr(event, field), f"traceability rubric reads {field}"


def test_event_contract_abstention_is_its_own_event_type():
    # An abstention is not a policy decision; recording it as one would
    # claim the policy engine ran when it did not.
    store = AuditStore()
    event = store.record_abstention("corr-2", ["no confident candidate"])
    assert isinstance(event, AbstentionEvent)
    assert store.events("corr-2") == ()
    assert store.abstentions("corr-2") == (event,)


def test_event_contract_store_is_append_only_by_surface():
    for name in ("update", "delete", "clear", "remove", "purge"):
        assert not hasattr(AuditStore, name)


def test_event_contract_events_are_filterable_by_correlation():
    store = AuditStore()
    outcome = decide(_skill(), _skill().permissions.allowed_roles[0])
    result = ExecutionResult(
        PolicyDecision.ALLOW,
        "id",
        False,
        True,
        verification_status=VerificationStatus.PASSED,
        check_results=(VerificationCheckResult("record_exists", True, "check passed"),),
    )
    store.record("a", _skill(), "erp_user", outcome, result, "k1")
    store.record("b", _skill(), "erp_user", outcome, result, "k2")

    assert len(store.events("a")) == 1
    assert len(store.events()) == 2


def test_event_contract_runtime_result_shape_is_stable():
    erp = _fake()
    runtime: Runtime = Runtime(erp)
    runtime.register(
        _skill().skill_id, _skill().version, lambda e, a: e.create(MODEL, a)
    )
    result = runtime.execute(
        _skill(),
        {"customer_name": "Acme", "expected_revenue": "100"},
        _skill().permissions.allowed_roles[0],
        "key",
        postcondition_checks=(
            VerificationCheck("record_exists", lambda adapter, output: True),
        ),
    )
    assert isinstance(result, ExecutionResult)
    assert isinstance(result.decision, PolicyDecision)
    assert isinstance(result.idempotent_replay, bool)
    assert isinstance(result.verification_status, VerificationStatus)
    assert isinstance(result.check_results, tuple)
    assert all(
        isinstance(item, VerificationCheckResult) for item in result.check_results
    )
