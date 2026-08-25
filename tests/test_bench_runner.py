from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.bench_runner import run_all, run_case, summarize
from erp_agent_os.dataset import CaseLabel

_CASES = generate_cases()


def test_run_all_produces_one_outcome_per_case():
    outcomes = run_all(_CASES)
    assert len(outcomes) == len(_CASES) == 480


def test_a_normal_case_actually_mutates_and_matches():
    normal_cases = [c for c in _CASES if c.labels == {CaseLabel.NORMAL}]
    case = normal_cases[0]
    outcome = run_case(case)
    assert outcome.matched is True
    assert outcome.handler_error is None


def test_seeded_reference_lets_r2_update_skill_reach_the_handler_when_approved():
    from erp_agent_os.adapters import FakeERPAdapter
    from erp_agent_os.approval import ApprovalService
    from erp_agent_os.audit import AuditStore
    from erp_agent_os.bench_intents import INTENTS_BY_ID
    from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
    from erp_agent_os.handlers import HANDLERS, SKILL_MODELS
    from erp_agent_os.parser import structure_proposal
    from erp_agent_os.retrieval import TfidfRetriever
    from erp_agent_os.runtime import Runtime
    from erp_agent_os.system_c import SystemC

    update_cases = [
        c
        for c in _CASES
        if c.canonical_intent.startswith("crm.update_expected_revenue")
        and c.labels == {CaseLabel.NORMAL}
    ]
    case = update_cases[0]
    intent = INTENTS_BY_ID[case.canonical_intent]
    skill = CATALOG_BY_ID[intent.skill_id]

    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    erp.create(
        "crm.opportunity",
        {"seeded": True},
        record_id=case.expected_arguments["opportunity_id"],
    )
    runtime = Runtime(erp)
    for cataloged in CATALOG:
        runtime.register(
            cataloged.skill_id, cataloged.version, HANDLERS[cataloged.skill_id]
        )
    from datetime import UTC, datetime

    approval = ApprovalService(clock=lambda: datetime.now(UTC))
    approval.grant("manager1", skill.skill_id, ttl_seconds=60)
    system = SystemC(erp, runtime, TfidfRetriever(CATALOG), AuditStore(), approval)

    proposal = structure_proposal(
        case.canonical_intent,
        case.expected_arguments,
        skill.input_schema["required"],
        0.9,
    )
    before = erp.snapshot()
    system.handle(
        case.request_id, case.request_text, proposal, "erp_user", case.request_id
    )
    after = erp.snapshot()

    assert before != after


def test_unreferenced_record_surfaces_handler_error_on_r0_skill():
    # inventory.check_availability (R0) auto-executes and looks its
    # product up by name; if that product was never seeded, the handler
    # must fail visibly (Runtime catches it), not silently succeed.
    from erp_agent_os.dataset import CaseLabel, ExpectedDecision

    case = next(
        c
        for c in _CASES
        if c.canonical_intent.startswith("inventory.check_availability")
        and c.labels == {CaseLabel.NORMAL}
    ).model_copy(
        update={
            "expected_arguments": {"product_name": "Producto-Nunca-Sembrado"},
            "expected_decision": ExpectedDecision.DENY,
            "error_type": "unknown_record_id",
        }
    )
    outcome = run_case(case)
    assert outcome.handler_error is not None


def test_summarize_reports_all_three_buckets():
    outcomes = run_all(_CASES)
    summary = summarize(_CASES, outcomes)
    assert set(summary) == {"NORMAL", "NOISE", "ADVERSARIAL"}
    assert summary["NORMAL"]["total"] == 240
    assert summary["NOISE"]["total"] == 144
    assert summary["ADVERSARIAL"]["total"] == 96


def test_adversarial_gap_is_visible_not_hidden():
    outcomes = run_all(_CASES)
    summary = summarize(_CASES, outcomes)
    # Documented finding: current policy/runtime has no prompt-injection,
    # range, bulk-scope, or permission-text detection, so most ADVERSARIAL
    # cases legitimately do not match their ideally-correct label yet.
    assert summary["ADVERSARIAL"]["rate"] < summary["NORMAL"]["rate"]
