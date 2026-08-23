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

import json
import logging
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.audit import AuditStore
from erp_agent_os.bench_intents import INTENTS_BY_ID
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.dataset import BenchmarkCase, DatasetSplit
from erp_agent_os.evidence import (
    execution_record_from_dict,
    execution_record_to_dict,
)
from erp_agent_os.handlers import HANDLERS, REFERENCE_FIELDS, SKILL_MODELS
from erp_agent_os.llm_client import CachingLLMClient, LLMClient
from erp_agent_os.metrics import ExecutionRecord
from erp_agent_os.parser import structure_proposal
from erp_agent_os.postconditions import build_checks
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.system_a import SystemA
from erp_agent_os.system_b import SystemB
from erp_agent_os.system_c import SystemC
from erp_agent_os.traceability import (
    score_governed_execution,
    score_ungoverned_execution,
)

logger = logging.getLogger(__name__)

ROLE = "erp_user"
REPETITIONS = 3


@dataclass(frozen=True)
class ExperimentManifest:
    """What was actually run — recorded so results cannot be misread."""

    selector: str
    is_confirmatory: bool
    n_cases: int
    n_systems: int
    n_repetitions: int
    seed: int
    # True when every system extracted its arguments from the raw
    # request text with the same LLM, instead of being handed
    # `case.expected_arguments`. See `_resolve_arguments`.
    real_parser: bool = False

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


def _resolve_arguments(
    case: BenchmarkCase, llm: LLMClient, required: list[str], real_parser: bool
) -> tuple[dict[str, Any], int, int]:
    """Arguments a system works from, plus the tokens they cost.

    Default (`real_parser=False`): every system is handed
    `case.expected_arguments` -- a perfect parse nobody paid for. That
    keeps the frozen confirmatory run comparable to its published
    numbers, but it flatters System C on H2: A and B spend tokens
    selecting a tool while C spends none at all, so C looks free when a
    real deployment would still need an LLM to read arguments out of
    the request text.

    With `real_parser=True`, all three systems pay the *same*
    extraction cost, over the *same* field list, with the *same* prompt
    (CLAUDE.md D-03: identical in everything comparable). The token
    comparison then isolates exactly what the thesis claims -- that
    retrieval replaces the tool-selection call -- instead of crediting
    C with an argument parse it never performed.
    """
    if not real_parser:
        return dict(case.expected_arguments), 0, 0
    extraction = llm.extract_arguments(case.request_text, required)
    return (
        dict(extraction.arguments),
        extraction.prompt_tokens,
        extraction.completion_tokens,
    )


def _run_system_c(
    case: BenchmarkCase, llm: LLMClient, repetition: int, real_parser: bool = False
) -> ExecutionRecord:
    erp = _fresh_erp(case)
    before = erp.snapshot()
    runtime = Runtime(erp)
    for skill in CATALOG:
        runtime.register(skill.skill_id, skill.version, HANDLERS[skill.skill_id])
    retriever = TfidfRetriever(CATALOG)
    audit = AuditStore()
    system = SystemC(erp, runtime, retriever, audit)

    intent = INTENTS_BY_ID[case.canonical_intent]
    required = CATALOG_BY_ID[intent.skill_id].input_schema["required"]
    arguments, parse_in, parse_out = _resolve_arguments(
        case, llm, required, real_parser
    )
    proposal = structure_proposal(
        case.canonical_intent, arguments, required, confidence=0.9
    )
    candidates = retriever.rank(case.request_text, role=ROLE)
    ranked = tuple(candidate.skill.skill_id for candidate in candidates)
    result = system.handle(
        case.request_id, case.request_text, proposal, ROLE, case.request_id
    )

    postconditions_met = None
    if result.decision == "ALLOW" and result.selected_skill_id:
        skill = CATALOG_BY_ID[result.selected_skill_id]
        checks = build_checks(skill, case.expected_arguments, before)
        output = result.execution.output if result.execution else None
        postconditions_met = all(check(erp, output) for check in checks)

    audit_events = audit.events(case.request_id)
    abstentions = audit.abstentions(case.request_id)
    trace_details = score_governed_execution(
        correlation_id=case.request_id,
        has_interpretation=bool(proposal.intent),
        ranked_skill_ids=ranked,
        abstention_reasons=abstentions[-1].reasons if abstentions else result.reasons,
        audit_event=audit_events[-1] if audit_events else None,
    )
    selected_skill = (
        CATALOG_BY_ID[result.selected_skill_id] if result.selected_skill_id else None
    )
    output = result.execution.output if result.execution else None
    if selected_skill is not None and result.decision == "ALLOW":
        named_checks = build_checks(selected_skill, case.expected_arguments, before)
        postcondition_evidence: dict[str, bool] | str = {
            name: check(erp, output)
            for name, check in zip(
                selected_skill.postconditions, named_checks, strict=True
            )
        }
    else:
        postcondition_evidence = {
            "state_unchanged_on_non_allow": _state_unchanged(before, erp)
        }

    return ExecutionRecord(
        request_id=case.request_id,
        system="C",
        repetition=repetition,
        selected_skill_id=result.selected_skill_id,
        decision=result.decision,
        postconditions_met=postconditions_met,
        side_effect_free=_side_effect_free(
            before, erp, result.decision, SKILL_MODELS[intent.skill_id]
        ),
        handler_error=result.execution.handler_error if result.execution else None,
        ranked_skill_ids=ranked,
        final_state=erp.snapshot(),
        state_unchanged=_state_unchanged(before, erp),
        traceability_score=trace_details.total,
        # C's retrieval is TF-IDF, so its only LLM cost is the shared
        # argument parse -- zero unless `--real-parser` is on.
        prompt_tokens=parse_in,
        completion_tokens=parse_out,
        initial_state=before,
        normalized_arguments=dict(arguments),
        candidate_scores={
            candidate.skill.skill_id: candidate.score for candidate in candidates
        },
        role=ROLE,
        policy_reasons=tuple(result.reasons),
        permission_evidence=(
            f"policy_evaluated_for_role:{ROLE}"
            if audit_events
            else "policy_not_reached_due_to_abstention_or_clarification"
        ),
        selected_skill_version=selected_skill.version if selected_skill else None,
        handler_name=(
            f"{HANDLERS[selected_skill.skill_id].__module__}."
            f"{HANDLERS[selected_skill.skill_id].__name__}"
            if selected_skill
            else "not_applicable"
        ),
        postcondition_evidence=postcondition_evidence,
        traceability_components={
            name: float(present) for name, present in trace_details.components.items()
        },
    )


def _run_system_b(
    case: BenchmarkCase, llm: LLMClient, repetition: int, real_parser: bool = False
) -> ExecutionRecord:
    erp = _fresh_erp(case)
    before = erp.snapshot()
    intent = INTENTS_BY_ID[case.canonical_intent]
    model = SKILL_MODELS[intent.skill_id]
    required = CATALOG_BY_ID[intent.skill_id].input_schema["required"]
    arguments, parse_in, parse_out = _resolve_arguments(
        case, llm, required, real_parser
    )
    system = SystemB(erp, llm)
    result = system.handle(case.request_text, arguments)

    decision = "ALLOW" if result.error is None else "DENY"
    postconditions_met = None
    if result.error is None and result.skill_id:
        checks = build_checks(
            CATALOG_BY_ID[result.skill_id], case.expected_arguments, before
        )
        postconditions_met = all(check(erp, result.output) for check in checks)

    trace_details = score_ungoverned_execution(
        correlation_id=case.request_id,
        tool_or_skill_id=result.skill_id,
        output_present=result.output is not None,
    )
    return ExecutionRecord(
        request_id=case.request_id,
        system="B",
        repetition=repetition,
        selected_skill_id=result.skill_id,
        decision=decision,
        postconditions_met=postconditions_met,
        side_effect_free=_side_effect_free(before, erp, decision, model),
        handler_error=result.error,
        ranked_skill_ids=(result.skill_id,) if result.skill_id else (),
        final_state=erp.snapshot(),
        state_unchanged=_state_unchanged(before, erp),
        # Tool selection + (when enabled) the shared argument parse.
        prompt_tokens=result.prompt_tokens + parse_in,
        completion_tokens=result.completion_tokens + parse_out,
        traceability_score=trace_details.total,
        initial_state=before,
        normalized_arguments=dict(arguments),
        role=ROLE,
        policy_reasons=("not_available",),
        traceability_components={
            name: float(present) for name, present in trace_details.components.items()
        },
    )


def _run_system_a(
    case: BenchmarkCase, llm: LLMClient, repetition: int, real_parser: bool = False
) -> ExecutionRecord:
    erp = _fresh_erp(case)
    before = erp.snapshot()
    system = SystemA(erp, llm)

    intent = INTENTS_BY_ID[case.canonical_intent]
    model = SKILL_MODELS[intent.skill_id]
    required = CATALOG_BY_ID[intent.skill_id].input_schema["required"]
    arguments, parse_in, parse_out = _resolve_arguments(
        case, llm, required, real_parser
    )
    args = {
        "model": model,
        "fields": dict(arguments),
        "record_id": next(
            (
                str(arguments[f])
                for f in REFERENCE_FIELDS.get(intent.skill_id, [])
                if arguments.get(f)
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

    trace_details = score_ungoverned_execution(
        correlation_id=case.request_id,
        tool_or_skill_id=result.tool_name,
        output_present=result.output is not None,
    )
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
        side_effect_free=_side_effect_free(before, erp, decision, model),
        handler_error=result.error,
        ranked_skill_ids=(),
        final_state=erp.snapshot(),
        state_unchanged=_state_unchanged(before, erp),
        # Tool selection + (when enabled) the shared argument parse.
        prompt_tokens=result.prompt_tokens + parse_in,
        completion_tokens=result.completion_tokens + parse_out,
        traceability_score=trace_details.total,
        initial_state=before,
        normalized_arguments=dict(arguments),
        role=ROLE,
        policy_reasons=("not_available",),
        traceability_components={
            name: float(present) for name, present in trace_details.components.items()
        },
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


def _state_unchanged(before: dict[str, Any], erp: FakeERPAdapter) -> bool:
    return bool(before["records"] == erp.snapshot()["records"])


def _state_signature(erp: FakeERPAdapter) -> dict[str, int]:
    snapshot = erp.snapshot()
    return {model: len(rows) for model, rows in snapshot["records"].items()}


def _side_effect_free(
    before: dict[str, Any], erp: FakeERPAdapter, decision: str, target_model: str
) -> bool:
    """No collateral change outside the model the task targets.

    A refusal must leave the store untouched. An ALLOW may modify its own
    target model, but touching any *other* model is a side effect -- which
    is what §20's fifth conjunct means. Returning True unconditionally for
    ALLOW (the earlier implementation) made the conjunct vacuous: it never
    once failed across 1.080 observations.
    """
    after = erp.snapshot()
    before_records: dict[str, Any] = before["records"]
    after_records: dict[str, Any] = after["records"]

    if decision != "ALLOW":
        return before_records == after_records

    return all(
        rows == after_records.get(model)
        for model, rows in before_records.items()
        if model != target_model
    )


def _record_key(request_id: str, system: str, repetition: int) -> str:
    return f"{request_id}|{system}|{repetition}"


def _dump_record(record: ExecutionRecord) -> dict[str, Any]:
    return execution_record_to_dict(record)


def _load_record(payload: dict[str, Any]) -> ExecutionRecord:
    return execution_record_from_dict(payload)


def _load_checkpoint(checkpoint_path: Path) -> dict[str, ExecutionRecord]:
    """Already-completed observations from a prior, interrupted run.

    A real-LLM run can take an hour+ and cross a daily token quota or an
    unrelated interruption; without this, restarting re-spends tokens
    already paid for on the same 1.080 observations.
    """
    if not checkpoint_path.exists():
        return {}
    done: dict[str, ExecutionRecord] = {}
    for line in checkpoint_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        done[row["key"]] = _load_record(row["record"])
    return done


def run_experiment(
    cases: Sequence[BenchmarkCase],
    llm: LLMClient,
    *,
    repetitions: int = REPETITIONS,
    seed: int = 20260805,
    checkpoint_path: Path | None = None,
    real_parser: bool = False,
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

    selector = type(llm).__name__
    is_confirmatory = selector != "DeterministicStubClient"

    # Repetitions of the same case ask the same query; with temperature=0
    # (CLAUDE.md §23) two independent real runs already showed the result
    # is reproducible (H3 = 1.0 both times). Only the first call per
    # unique query is real; cached hits report 0 tokens (see
    # CachingLLMClient) so H2/H8 never overcount actual spend.
    #
    # One cache PER SYSTEM, not one shared cache. Sharing it was a real
    # measurement bug: argument extraction is keyed on
    # (query_text, fields), which is identical for A, B and C on the same
    # case, so whichever system the randomized order happened to run
    # first paid for the extraction and the other two were credited zero
    # tokens. Per-system token totals then measured execution order
    # rather than architecture. In a real deployment a request reaches
    # one system, and that system pays its own extraction; deduplicating
    # across systems has no real-world counterpart, while deduplicating
    # across a case's 3 repetitions removes a purely experimental
    # artifact -- which is what this cache is for.
    cached_llms: dict[str, LLMClient] = {
        system: CachingLLMClient(llm) for system in ("A", "B", "C")
    }

    done = _load_checkpoint(checkpoint_path) if checkpoint_path else {}
    if done:
        logger.info(
            "resuming from checkpoint: %d/%d already done", len(done), len(plan)
        )

    checkpoint_file = None
    if checkpoint_path is not None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_file = checkpoint_path.open("a", encoding="utf-8")

    runners = {"A": _run_system_a, "B": _run_system_b, "C": _run_system_c}
    total = len(plan)
    records = []
    try:
        for i, (case, system, rep) in enumerate(plan, start=1):
            key = _record_key(case.request_id, system, rep)
            cached = done.get(key)
            if cached is not None:
                records.append(cached)
                continue
            logger.info(
                "observation %d/%d: system=%s case=%s rep=%d",
                i,
                total,
                system,
                case.request_id,
                rep,
            )
            # RF-16: measured once here rather than in each runner, so
            # every system is timed at exactly the same boundary.
            started = time.monotonic()
            record = runners[system](case, cached_llms[system], rep, real_parser)
            record = replace(record, latency_seconds=time.monotonic() - started)
            records.append(record)
            if checkpoint_file is not None:
                checkpoint_file.write(
                    json.dumps({"key": key, "record": _dump_record(record)}) + "\n"
                )
                checkpoint_file.flush()
    finally:
        if checkpoint_file is not None:
            checkpoint_file.close()

    manifest = ExperimentManifest(
        selector=selector,
        is_confirmatory=is_confirmatory,
        n_cases=len(test_cases),
        n_systems=3,
        n_repetitions=repetitions,
        seed=seed,
        real_parser=real_parser,
    )
    return records, manifest
