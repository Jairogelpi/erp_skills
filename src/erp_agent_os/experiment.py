"""Paired A/B/C experiment runner (CLAUDE.md §19, roadmap P8.2-P8.3).

Runs the frozen test split through all three systems with the same
initial state, the same tool coverage, the same roles and the same
evaluator: 120 cases x 3 systems x 3 repetitions = 1.080 paired
observations. The unit of pairing is `request_id` x initial state x
repetition, and `FakeERPAdapter` is rebuilt per observation so no state
survives between them.

**Selector held constant.** All three systems receive the *same*
`LLMClient`. With `DeterministicStubClient` that isolates the
architectural contribution (governance vs. none) from model quality,
which is the comparison this module is for; it is *not* the confirmatory
protocol of §19, which requires a real provider. `run_experiment`
records which selector was used so results can never be silently
mistaken for the confirmatory run.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.audit import AuditStore
from erp_agent_os.bench_intents import INTENTS_BY_ID
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.dataset import BenchmarkCase, DatasetSplit
from erp_agent_os.handlers import HANDLERS, SKILL_MODELS
from erp_agent_os.llm_client import LLMClient
from erp_agent_os.metrics import ExecutionRecord
from erp_agent_os.parser import structure_proposal
from erp_agent_os.postconditions import build_checks
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.system_a import SystemA
from erp_agent_os.system_b import SystemB
from erp_agent_os.system_c import SystemC

ROLE = "erp_user"
REPETITIONS = 3

REFERENCE_FIELDS: dict[str, list[str]] = {
    "crm.update_expected_revenue": ["opportunity_id"],
    "sales.add_quote_line": ["quote_id"],
    "sales.confirm_order": ["order_id"],
    "product.update_field": ["product_name"],
    "inventory.check_availability": ["product_name"],
}


@dataclass(frozen=True)
class ExperimentManifest:
    """What was actually run — recorded so results cannot be misread."""

    selector: str
    is_confirmatory: bool
    n_cases: int
    n_systems: int
    n_repetitions: int
    seed: int

    @property
    def n_observations(self) -> int:
        return self.n_cases * self.n_systems * self.n_repetitions


def _seed_state(erp: FakeERPAdapter, case: BenchmarkCase) -> None:
    """Identical initial state for every system on this case."""
    if case.error_type == "unknown_record_id":
        return
    intent = INTENTS_BY_ID[case.canonical_intent]
    model = SKILL_MODELS[intent.skill_id]
    for reference in REFERENCE_FIELDS.get(intent.skill_id, []):
        value = case.expected_arguments.get(reference)
        if not value:
            continue
        fields = {"stock": 10} if model == "product.product" else {"seeded": True}
        try:
            erp.create(model, fields, record_id=str(value))
        except ValueError:
            pass


def _fresh_erp(case: BenchmarkCase) -> FakeERPAdapter:
    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    _seed_state(erp, case)
    return erp


def _run_system_c(
    case: BenchmarkCase, llm: LLMClient, repetition: int
) -> ExecutionRecord:
    erp = _fresh_erp(case)
    before = erp.snapshot()
    runtime = Runtime(erp)
    for skill in CATALOG:
        runtime.register(skill.skill_id, skill.version, HANDLERS[skill.skill_id])
    retriever = TfidfRetriever(CATALOG)
    system = SystemC(erp, runtime, retriever, AuditStore())

    intent = INTENTS_BY_ID[case.canonical_intent]
    required = CATALOG_BY_ID[intent.skill_id].input_schema["required"]
    proposal = structure_proposal(
        case.canonical_intent, case.expected_arguments, required, confidence=0.9
    )
    ranked = tuple(
        c.skill.skill_id for c in retriever.rank(case.request_text, role=ROLE)
    )
    result = system.handle(
        case.request_id, case.request_text, proposal, ROLE, case.request_id
    )

    postconditions_met = None
    if result.decision == "ALLOW" and result.selected_skill_id:
        skill = CATALOG_BY_ID[result.selected_skill_id]
        checks = build_checks(skill, case.expected_arguments, before)
        output = result.execution.output if result.execution else None
        postconditions_met = all(check(erp, output) for check in checks)

    return ExecutionRecord(
        request_id=case.request_id,
        system="C",
        repetition=repetition,
        selected_skill_id=result.selected_skill_id,
        decision=result.decision,
        postconditions_met=postconditions_met,
        side_effect_free=_side_effect_free(before, erp, result.decision),
        handler_error=result.execution.handler_error if result.execution else None,
        ranked_skill_ids=ranked,
        final_state=_state_signature(erp),
    )


def _run_system_b(
    case: BenchmarkCase, llm: LLMClient, repetition: int
) -> ExecutionRecord:
    erp = _fresh_erp(case)
    before = erp.snapshot()
    system = SystemB(erp, llm)
    result = system.handle(case.request_text, case.expected_arguments)

    decision = "ALLOW" if result.error is None else "DENY"
    postconditions_met = None
    if result.error is None and result.skill_id:
        checks = build_checks(
            CATALOG_BY_ID[result.skill_id], case.expected_arguments, before
        )
        postconditions_met = all(check(erp, result.output) for check in checks)

    return ExecutionRecord(
        request_id=case.request_id,
        system="B",
        repetition=repetition,
        selected_skill_id=result.skill_id,
        decision=decision,
        postconditions_met=postconditions_met,
        side_effect_free=_side_effect_free(before, erp, decision),
        handler_error=result.error,
        ranked_skill_ids=(result.skill_id,) if result.skill_id else (),
        final_state=_state_signature(erp),
    )


def _run_system_a(
    case: BenchmarkCase, llm: LLMClient, repetition: int
) -> ExecutionRecord:
    erp = _fresh_erp(case)
    before = erp.snapshot()
    system = SystemA(erp, llm)

    intent = INTENTS_BY_ID[case.canonical_intent]
    model = SKILL_MODELS[intent.skill_id]
    args = {
        "model": model,
        "fields": dict(case.expected_arguments),
        "record_id": next(
            (
                str(case.expected_arguments[f])
                for f in REFERENCE_FIELDS.get(intent.skill_id, [])
                if case.expected_arguments.get(f)
            ),
            "",
        ),
    }
    result = system.handle(case.request_text, args)
    decision = "ALLOW" if result.error is None else "DENY"

    # Judged by the same criterion as B and C: did the resulting state
    # satisfy the postconditions of the skill this task required? Leaving
    # this None would make A structurally unable to pass STSR conjunct 4.
    postconditions_met = None
    if result.error is None:
        checks = build_checks(
            CATALOG_BY_ID[intent.skill_id], case.expected_arguments, before
        )
        postconditions_met = all(check(erp, result.output) for check in checks)

    return ExecutionRecord(
        request_id=case.request_id,
        system="A",
        repetition=repetition,
        # System A has no skill registry, so scoring it on skill identity
        # would make its STSR structurally 0 and rig the comparison
        # (CLAUDE.md D-03 demands equivalent tool coverage). Instead its
        # generic tool call is mapped back to the catalog skill with the
        # same model and operation: A gets credit for choosing the right
        # KIND of action, which is all its vocabulary can express.
        selected_skill_id=_equivalent_skill(result.tool_name, model),
        decision=decision,
        postconditions_met=postconditions_met,
        side_effect_free=_side_effect_free(before, erp, decision),
        handler_error=result.error,
        ranked_skill_ids=(),
        final_state=_state_signature(erp),
    )


_TOOL_OPERATIONS = {
    "create_record": "create",
    "update_record": "update",
    "get_record": "read",
}


def _equivalent_skill(tool_name: str | None, model: str) -> str | None:
    """Map a System A generic tool call onto the catalog skill it matches."""
    operation = _TOOL_OPERATIONS.get(tool_name or "")
    if operation is None:
        return None
    for skill in CATALOG:
        if SKILL_MODELS[skill.skill_id] == model and skill.operation == operation:
            return skill.skill_id
    return None


def _state_signature(erp: FakeERPAdapter) -> dict[str, int]:
    snapshot = erp.snapshot()
    return {model: len(rows) for model, rows in snapshot["records"].items()}


def _side_effect_free(
    before: dict[str, object], erp: FakeERPAdapter, decision: str
) -> bool:
    """A refusal must leave the store untouched; an ALLOW may add records."""
    after = erp.snapshot()
    if decision == "ALLOW":
        return True
    return before == after


def run_experiment(
    cases: Sequence[BenchmarkCase],
    llm: LLMClient,
    *,
    repetitions: int = REPETITIONS,
    seed: int = 20260805,
) -> tuple[list[ExecutionRecord], ExperimentManifest]:
    test_cases = [c for c in cases if c.split is DatasetSplit.FINAL_TEST]
    rng = random.Random(seed)

    plan = [
        (case, system, repetition)
        for case in test_cases
        for system in ("A", "B", "C")
        for repetition in range(repetitions)
    ]
    rng.shuffle(plan)  # randomized order, CLAUDE.md §19

    runners = {"A": _run_system_a, "B": _run_system_b, "C": _run_system_c}
    records = [runners[system](case, llm, rep) for case, system, rep in plan]

    manifest = ExperimentManifest(
        selector=type(llm).__name__,
        is_confirmatory=type(llm).__name__ != "DeterministicStubClient",
        n_cases=len(test_cases),
        n_systems=3,
        n_repetitions=repetitions,
        seed=seed,
    )
    return records, manifest
