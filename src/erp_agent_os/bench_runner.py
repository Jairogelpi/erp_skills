"""Wire ERP-Skills-Bench v1 cases to real System C execution.

Scope per roadmap P8.1 groundwork: for each case, build an isolated
`FakeERPAdapter` + `Runtime` + `TfidfRetriever` + `AuditStore` + `SystemC`,
seed whatever reference entity the case's skill needs (skipped for the
"identificador_inexistente" adversarial category, which is deliberately
about a missing reference), run `SystemC.handle`, and compare the actual
decision to the dataset's annotated `expected_decision`.

This is a **discovery/reporting** tool, not a policy/runtime fix: several
adversarial categories (prompt injection, out-of-range arguments,
disguised bulk change, conflicting fields, irreversible-operation framing,
insufficient permissions) have no corresponding check in the current
`policy.py`/`runtime.py`, so their actual decision will legitimately not
match the dataset's ideally-correct `expected_decision`. That gap is
reported, not hidden or silently "fixed" by relaxing the comparison.
"""

from dataclasses import dataclass
from typing import Any

from erp_agent_os.adapters import DuplicateRecordError, FakeERPAdapter
from erp_agent_os.audit import AuditStore
from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.bench_intents import INTENTS_BY_ID
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.dataset import BenchmarkCase, CaseLabel
from erp_agent_os.handlers import HANDLERS, REFERENCE_FIELDS, SKILL_MODELS
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.system_c import SystemC

ROLE = "erp_user"


def _seed_references(erp: FakeERPAdapter, skill_id: str, args: dict[str, Any]) -> None:
    model = SKILL_MODELS[skill_id]
    for field in REFERENCE_FIELDS.get(skill_id, []):
        ref_id = args.get(field)
        if not ref_id:
            continue
        fields = {"stock": 10} if model == "product.product" else {"seeded": True}
        try:
            erp.create(model, fields, record_id=ref_id)
        except DuplicateRecordError:
            pass


@dataclass(frozen=True)
class RunOutcome:
    request_id: str
    expected_decision: str
    actual_decision: str
    matched: bool
    handler_error: str | None
    initial_records: dict[str, Any]
    final_records: dict[str, Any]


def run_case(case: BenchmarkCase) -> RunOutcome:
    intent = INTENTS_BY_ID[case.canonical_intent]
    skill = CATALOG_BY_ID[intent.skill_id]

    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    if case.error_type != "unknown_record_id":
        _seed_references(erp, intent.skill_id, case.expected_arguments)
    initial_snapshot = erp.snapshot()

    runtime = Runtime(erp)
    for cataloged in CATALOG:
        runtime.register(
            cataloged.skill_id, cataloged.version, HANDLERS[cataloged.skill_id]
        )
    retriever = TfidfRetriever(CATALOG)
    audit = AuditStore()
    system = SystemC(erp, runtime, retriever, audit)

    required_fields = skill.input_schema["required"]
    proposal = structure_proposal(
        case.canonical_intent, case.expected_arguments, required_fields, confidence=0.9
    )

    result = system.handle(
        case.request_id, case.request_text, proposal, ROLE, case.request_id
    )
    final_snapshot = erp.snapshot()

    handler_error = result.execution.handler_error if result.execution else None
    return RunOutcome(
        request_id=case.request_id,
        expected_decision=case.expected_decision.value,
        actual_decision=result.decision,
        matched=result.decision == case.expected_decision.value,
        handler_error=handler_error,
        initial_records=initial_snapshot["records"],
        final_records=final_snapshot["records"],
    )


def run_all(cases: list[BenchmarkCase] | None = None) -> list[RunOutcome]:
    return [run_case(case) for case in (cases or generate_cases())]


def summarize(
    cases: list[BenchmarkCase], outcomes: list[RunOutcome]
) -> dict[str, dict[str, float | int]]:
    buckets: dict[str, list[int]] = {
        "NORMAL": [0, 0],
        "NOISE": [0, 0],
        "ADVERSARIAL": [0, 0],
    }
    for case, outcome in zip(cases, outcomes, strict=True):
        if CaseLabel.ADVERSARIAL in case.labels:
            label = "ADVERSARIAL"
        elif CaseLabel.NOISE in case.labels:
            label = "NOISE"
        else:
            label = "NORMAL"
        buckets[label][1] += 1
        if outcome.matched:
            buckets[label][0] += 1
    return {
        label: {"matched": matched, "total": total, "rate": matched / total}
        for label, (matched, total) in buckets.items()
    }
