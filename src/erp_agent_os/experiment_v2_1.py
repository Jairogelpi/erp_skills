"""Arm-aware, uncached v2.1 experiment execution (Task 8).

docs/tfm-closure-no-human-v2.1.md section 6/7/9: runs generated
`ScenarioSpec`s through A/B/C, producing one `ObservationV21` row per
unit. Deliberately separate from erp_agent_os.experiment (v1): that
module stays reproducible on its own frozen protocol; nothing here is
retrofitted into it, and this module never imports `run_experiment`,
`_run_system_a/b/c`, or any v1 selector-caching machinery.

**Uncached, unconditionally.** v1's `CachingLLMClient` served repeated
identical queries from a per-process cache. This module never wraps a
client in it: section 7 forbids sharing a cache between systems, and H2
additionally forbids caching across cases and repetitions -- since no
arm here repeats an identical (system, query) pair for a reason that
should be free (H3b's repeated calls are the one exception the spec
itself carves out, and they still bypass any cache by construction: this
module has none), the simplest and most defensible design is to have no
caching layer anywhere in it.

**Call-level retry telemetry, with a declared limit.** `RecordingLLMClient`
performs the runner's OWN bounded retry loop around each `propose_action`/
`extract_arguments` call, recording one `ModelCallEvent` per attempt
(success or failure). This captures every retry THIS module decides to
perform. It cannot see retries a real provider client already performs
internally before returning (docs/*_client.py's own backoff loops) --
that is a real granularity limit of the shared `LLMClient` Protocol,
not something this module can observe through it, and is declared here
rather than silently overstated.

**Delta observation, not trust.** `_observe_delta` derives what actually
changed from a live `FakeERPAdapter` before/after snapshot diff -- never
from what a system claims it did -- mirroring this project's own
postcondition-verification principle (CLAUDE.md section 25).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.audit import AbstentionEvent, AuditEvent, AuditStore
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.evaluator_v2_1 import (
    ExecutionOutcome,
    StrictSuccessResult,
    evaluate_stsr,
)
from erp_agent_os.evidence_v2_1 import (
    Arm,
    CallPurpose,
    ModelCallEvent,
    ObservationV21,
    Population,
    System,
    surface_id_for,
)
from erp_agent_os.handlers import HANDLERS, REFERENCE_FIELDS, SKILL_MODELS
from erp_agent_os.llm_client import (
    EXTRACTION_SYSTEM_PROMPT,
    SELECTION_SYSTEM_PROMPT,
    ArgumentExtraction,
    LLMClient,
    ToolCall,
)
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.scenarios_v2_1 import ScenarioSpec, build_gold
from erp_agent_os.surfaces_v2_1 import (
    Surface,
    SurfaceKind,
    primary_surface_kind,
    render_surface,
)
from erp_agent_os.system_a import SystemA
from erp_agent_os.system_b import SystemB
from erp_agent_os.system_c import SystemC

DEFAULT_MAX_CALL_ATTEMPTS = 3


class ExperimentV21Error(RuntimeError):
    pass


class AllAttemptsFailedError(ExperimentV21Error):
    def __init__(self, purpose: str, events: tuple[ModelCallEvent, ...]) -> None:
        super().__init__(f"all {len(events)} attempts failed for {purpose}")
        self.purpose = purpose
        self.events = events


def _hash_json(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# --------------------------------------------------------------- context


@dataclass(frozen=True)
class ArmRunContext:
    """Everything Task 8 step 2 requires to be IDENTICAL across A/B/C for
    one unit. Every runner in this module takes exactly one of these and
    reads provider/model/hashes from it -- there is nowhere else a system
    could pick up a different provider config, timeout or retry budget."""

    protocol_version: str
    frozen_commit: str
    dataset_hash: str
    provider: str
    model: str
    provider_config: dict[str, Any]
    code_version_hash: str
    dependency_lock_hash: str
    timeout_seconds: float
    max_call_attempts: int = DEFAULT_MAX_CALL_ATTEMPTS

    @property
    def provider_config_hash(self) -> str:
        payload = dict(self.provider_config)
        payload["timeout_seconds"] = self.timeout_seconds
        payload["max_call_attempts"] = self.max_call_attempts
        return _hash_json(payload)

    @property
    def extraction_prompt_hash(self) -> str:
        return _hash_json({"prompt": EXTRACTION_SYSTEM_PROMPT})

    @property
    def selection_prompt_hash(self) -> str:
        return _hash_json({"prompt": SELECTION_SYSTEM_PROMPT})


# ------------------------------------------------------- call telemetry


def _call_with_retries(
    purpose: CallPurpose,
    attempt_fn: Callable[[], tuple[Any, int, int]],
    *,
    max_attempts: int,
) -> tuple[Any, list[ModelCallEvent]]:
    events: list[ModelCallEvent] = []
    for attempt in range(1, max_attempts + 1):
        started = time.monotonic()
        try:
            result, prompt_tokens, completion_tokens = attempt_fn()
        except Exception as exc:  # noqa: E722 - any provider failure becomes telemetry
            events.append(
                ModelCallEvent(
                    purpose=purpose,
                    attempt=attempt,
                    success=False,
                    error_class=type(exc).__name__,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_seconds=time.monotonic() - started,
                )
            )
            continue
        events.append(
            ModelCallEvent(
                purpose=purpose,
                attempt=attempt,
                success=True,
                error_class=None,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_seconds=time.monotonic() - started,
            )
        )
        return result, events
    raise AllAttemptsFailedError(purpose, tuple(events))


class RecordingLLMClient:
    """Wraps any LLMClient, performing this module's OWN bounded retry
    loop and recording one ModelCallEvent per attempt -- never a cache.
    A fresh instance per unit means `.events` is exactly that unit's
    call history, nothing shared or carried over from a prior case."""

    def __init__(self, inner: LLMClient, *, max_attempts: int = 1) -> None:
        self._inner = inner
        self._max_attempts = max_attempts
        self.events: list[ModelCallEvent] = []

    def propose_action(self, query_text: str, tools: list) -> ToolCall:
        def attempt() -> tuple[ToolCall, int, int]:
            call = self._inner.propose_action(query_text, tools)
            return call, call.prompt_tokens, call.completion_tokens

        result, events = _call_with_retries(
            "tool_selection", attempt, max_attempts=self._max_attempts
        )
        self.events.extend(events)
        return result

    def extract_arguments(
        self, query_text: str, fields: list[str]
    ) -> ArgumentExtraction:
        def attempt() -> tuple[ArgumentExtraction, int, int]:
            extraction = self._inner.extract_arguments(query_text, fields)
            return extraction, extraction.prompt_tokens, extraction.completion_tokens

        result, events = _call_with_retries(
            "argument_extraction", attempt, max_attempts=self._max_attempts
        )
        self.events.extend(events)
        return result


# ------------------------------------------------------------- ERP state


def _fresh_erp() -> FakeERPAdapter:
    return FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))


def _seed_state(erp: FakeERPAdapter, scenario: ScenarioSpec) -> None:
    """Identical initial state for every system on this scenario -- the
    same REFERENCE_FIELDS-driven seeding v1 uses, reused here as pure
    data (which skill needs which id pre-created), not as behavior."""
    if scenario.expected_skill is None:
        return
    model = SKILL_MODELS.get(scenario.expected_skill)
    if model is None:
        return
    for reference in REFERENCE_FIELDS.get(scenario.expected_skill, []):
        value = scenario.arguments.get(reference)
        if not value:
            continue
        fields = {"stock": 10} if model == "product.product" else {"seeded": True}
        try:
            erp.create(model, fields, record_id=str(value))
        except ValueError:
            pass


def _observe_delta(
    before: dict[str, Any],
    after: dict[str, Any],
    model: str,
    *,
    decision: str,
    operation: str,
    risk_class: str,
) -> dict[str, Any]:
    """What actually changed, read from real before/after snapshots --
    never from what a system claims it did. Falls back to the declared
    operation/risk_class only for the two cases where nothing in the
    store could possibly distinguish them (a genuine no-op read, and R3's
    "confirm but never mutate" contract) -- both already public
    information the scenario used to construct the request, not gold."""
    if decision not in ("ALLOW", "SIMULATE"):
        return {"operation_kind": "no_change"}

    before_rows = dict(before.get("records", {}).get(model, []))
    after_rows = dict(after.get("records", {}).get(model, []))

    added = {rid: f for rid, f in after_rows.items() if rid not in before_rows}
    if added:
        _, fields = next(iter(added.items()))
        return {"operation_kind": "create_one", "new_fields": fields}

    changed = {
        rid: f
        for rid, f in after_rows.items()
        if rid in before_rows and f != before_rows[rid]
    }
    if changed:
        rid, fields = next(iter(changed.items()))
        before_fields = before_rows[rid]
        diffs = {k: v for k, v in fields.items() if before_fields.get(k) != v}
        if diffs:
            return {
                "operation_kind": "update_one_allowed_field",
                "match": before_fields,
                "new_fields": diffs,
            }

    if risk_class == "R3":
        return {"operation_kind": "confirm_document", "match": {}}
    if operation == "read":
        return {"operation_kind": "read_only"}
    return {"operation_kind": "no_change"}


def _side_effects(
    before: dict[str, Any], after: dict[str, Any], target_model: str | None
) -> tuple[str, ...]:
    before_records = before.get("records", {})
    after_records = after.get("records", {})
    return tuple(
        model
        for model, rows in before_records.items()
        if model != target_model and rows != after_records.get(model)
    )


# ------------------------------------------------------------------ trace


def _dump_audit_event(event: AuditEvent) -> dict[str, Any]:
    return {
        "correlation_id": event.correlation_id,
        "skill_id": event.skill_id,
        "skill_version": event.skill_version,
        "role": event.role,
        "decision": event.decision,
        "risk_score": event.risk_score,
        "reasons": list(event.reasons),
        "idempotency_key": event.idempotency_key,
        "idempotent_replay": event.idempotent_replay,
        "postconditions_met": event.postconditions_met,
        "output": event.output,
        "recorded_at": event.recorded_at.isoformat(),
    }


def _dump_abstention_event(event: AbstentionEvent) -> dict[str, Any]:
    return {"correlation_id": event.correlation_id, "reasons": list(event.reasons)}


def _normalized_trace(
    *,
    correlation_id: str,
    request_text: str,
    case_id: str,
    intent: str | None,
    arguments: dict[str, Any],
    selected_skill_id: str | None,
    abstained: bool,
    policy_decision: str,
    role: str,
    skill_version: str | None,
    handler: str | None,
    execution_output: Any,
    observed_state_delta: dict[str, Any],
    verification_status: str | None,
    approval_evidence: dict[str, Any] | None,
    final_decision_allowed: bool,
) -> dict[str, Any]:
    """The flat shape erp_agent_os.audit_reconstruction.reconstruct()
    expects (H7's common evaluator). Populated with what THIS system
    actually knows -- a field it has no evidence for stays None/missing
    rather than being fabricated (same discipline as
    erp_agent_os.evidence.trace_from_execution_record)."""
    return {
        "correlation_id": correlation_id,
        "request_text": request_text,
        "case_id": case_id,
        "case_id_matches_correlation": case_id == correlation_id,
        "intent": intent,
        "arguments": arguments or None,
        "selected_skill_id": selected_skill_id,
        "abstained": abstained,
        "policy_decision": policy_decision,
        "role": role,
        "skill_version": skill_version,
        "handler": handler,
        "execution_output": execution_output,
        "observed_state_delta": observed_state_delta,
        "verification_status": verification_status,
        "approval_evidence": approval_evidence,
        "final_decision_allowed": final_decision_allowed,
    }


def _evaluator_components(result: StrictSuccessResult) -> dict[str, bool]:
    return {
        "action_correct": result.action_correct,
        "arguments_correct": result.arguments_correct,
        "policy_correct": result.policy_correct,
        "final_state_correct": result.final_state_correct,
        "no_duplicate_mutation": result.no_duplicate_mutation,
        "no_unrelated_side_effect": result.no_unrelated_side_effect,
        "success": result.success,
    }


def _required_fields(scenario: ScenarioSpec) -> list[str]:
    if scenario.expected_skill is None:
        return []
    skill = CATALOG_BY_ID.get(scenario.expected_skill)
    if skill is None:
        return []
    return list(skill.input_schema.get("required", []))


# -------------------------------------------------------- per-system run


def _observation(
    *,
    scenario: ScenarioSpec,
    surface: Surface,
    context: ArmRunContext,
    system: System,
    arm: Arm,
    repetition_index: int,
    population: Population,
    security_pair_id: str | None,
    control_stratum: str | None,
    started_at: str,
    request_text: str,
    extracted_arguments: dict[str, Any],
    selected_skill_id: str | None,
    ranked_skill_ids: tuple[str, ...],
    candidate_scores: dict[str, float],
    policy_decision: str,
    policy_reasons: tuple[str, ...],
    call_events: tuple[ModelCallEvent, ...],
    selection_prompt_hash: str | None,
    initial_state: dict[str, Any],
    final_state: dict[str, Any],
    observed_state_delta: dict[str, Any],
    postcondition_evidence: dict[str, bool],
    side_effects: tuple[str, ...],
    raw_trace: dict[str, Any],
    normalized_trace: dict[str, Any],
    evaluator_components: dict[str, bool],
    latency_seconds: float,
) -> ObservationV21:
    return ObservationV21(
        protocol_version=context.protocol_version,
        frozen_commit=context.frozen_commit,
        dataset_hash=context.dataset_hash,
        scenario_id=scenario.scenario_id,
        surface_id=surface_id_for(scenario.scenario_id, surface.kind),
        surface_kind=surface.kind,  # type: ignore[arg-type]
        security_pair_id=security_pair_id,
        population=population,
        control_stratum=control_stratum,
        system=system,
        arm=arm,
        repetition_index=repetition_index,
        provider=context.provider,
        model=context.model,
        provider_config_hash=context.provider_config_hash,
        selection_prompt_hash=selection_prompt_hash,
        extraction_prompt_hash=context.extraction_prompt_hash,
        started_at=started_at,
        completed_at=_now_iso(),
        correlation_id=scenario.scenario_id,
        request_text=request_text,
        extracted_arguments=extracted_arguments,
        selected_skill_id=selected_skill_id,
        ranked_skill_ids=ranked_skill_ids,
        candidate_scores=candidate_scores,
        policy_decision=policy_decision,
        policy_reasons=policy_reasons,
        call_events=call_events,
        latency_seconds=latency_seconds,
        initial_state=initial_state,
        final_state=final_state,
        observed_state_delta=observed_state_delta,
        postcondition_evidence=postcondition_evidence,
        side_effects=side_effects,
        raw_trace=raw_trace,
        normalized_trace=normalized_trace,
        evaluator_components=evaluator_components,
        code_version_hash=context.code_version_hash,
        dependency_lock_hash=context.dependency_lock_hash,
    )


def run_c(
    scenario: ScenarioSpec,
    surface: Surface,
    context: ArmRunContext,
    llm: LLMClient,
    *,
    arm: Arm = "main",
    repetition_index: int = 0,
    population: Population = "main",
    security_pair_id: str | None = None,
    control_stratum: str | None = None,
    abstain: Callable | None = None,
) -> ObservationV21:
    started_at = _now_iso()
    t0 = time.monotonic()

    erp = _fresh_erp()
    _seed_state(erp, scenario)
    before = erp.snapshot()
    runtime: Runtime = Runtime(erp)
    for skill in CATALOG:
        runtime.register(skill.skill_id, skill.version, HANDLERS[skill.skill_id])
    retriever = TfidfRetriever(CATALOG)
    audit = AuditStore()
    kwargs: dict[str, Any] = {}
    if abstain is not None:
        kwargs["abstain"] = abstain
    system = SystemC(erp, runtime, retriever, audit, **kwargs)

    recorder = RecordingLLMClient(llm, max_attempts=context.max_call_attempts)
    required = _required_fields(scenario)
    if required:
        extraction = recorder.extract_arguments(surface.text, required)
        arguments = dict(extraction.arguments)
    else:
        arguments = {}

    proposal = structure_proposal(
        scenario.canonical_intent, arguments, required, confidence=0.9
    )
    candidates = retriever.rank(surface.text, role=scenario.actor_role)
    ranked_ids = tuple(candidate.skill.skill_id for candidate in candidates)
    candidate_scores = {c.skill.skill_id: c.score for c in candidates}

    result = system.handle(
        scenario.scenario_id,
        surface.text,
        proposal,
        scenario.actor_role,
        scenario.scenario_id,
    )

    after = erp.snapshot()
    fallback_model = (
        SKILL_MODELS.get(scenario.expected_skill) if scenario.expected_skill else None
    )
    target_model = (
        SKILL_MODELS.get(result.selected_skill_id)
        if result.selected_skill_id
        else fallback_model
    )
    delta = (
        _observe_delta(
            before,
            after,
            target_model,
            decision=result.decision,
            operation=scenario.operation,
            risk_class=scenario.risk_class,
        )
        if target_model
        else {"operation_kind": "no_change"}
    )
    side_effects = _side_effects(before, after, target_model) if target_model else ()

    outcome = ExecutionOutcome(
        selected_skill_id=result.selected_skill_id,
        arguments=arguments,
        decision=result.decision,
        final_state_delta=delta,
        duplicate_mutation=False,
        side_effects=side_effects,
    )
    gold = build_gold(scenario)
    stsr = evaluate_stsr(gold, outcome)

    selected_skill = (
        CATALOG_BY_ID.get(result.selected_skill_id)
        if result.selected_skill_id
        else None
    )
    handler_name = None
    if selected_skill is not None:
        handler_fn = HANDLERS.get(selected_skill.skill_id)
        if handler_fn is not None:
            handler_name = f"{handler_fn.__module__}.{handler_fn.__name__}"

    audit_events = audit.events(scenario.scenario_id)
    abstentions = audit.abstentions(scenario.scenario_id)
    execution_output = result.execution.output if result.execution else None
    postconditions_met = (
        result.execution.postconditions_met if result.execution else None
    )

    normalized_trace = _normalized_trace(
        correlation_id=scenario.scenario_id,
        request_text=surface.text,
        case_id=scenario.scenario_id,
        intent=scenario.canonical_intent,
        arguments=arguments,
        selected_skill_id=result.selected_skill_id,
        abstained=result.decision == "ABSTAIN",
        policy_decision=result.decision,
        role=scenario.actor_role,
        skill_version=selected_skill.version if selected_skill else None,
        handler=handler_name,
        execution_output=execution_output,
        observed_state_delta=delta,
        verification_status=(
            "passed"
            if postconditions_met is True
            else "failed"
            if postconditions_met is False
            else None
        ),
        approval_evidence=None,
        final_decision_allowed=result.decision == "ALLOW",
    )
    raw_trace = {
        "audit_events": [_dump_audit_event(e) for e in audit_events],
        "abstention_events": [_dump_abstention_event(e) for e in abstentions],
        "reasons": list(result.reasons),
    }

    return _observation(
        scenario=scenario,
        surface=surface,
        context=context,
        system="C",
        arm=arm,
        repetition_index=repetition_index,
        population=population,
        security_pair_id=security_pair_id,
        control_stratum=control_stratum,
        started_at=started_at,
        request_text=surface.text,
        extracted_arguments=arguments,
        selected_skill_id=result.selected_skill_id,
        ranked_skill_ids=ranked_ids,
        candidate_scores=candidate_scores,
        policy_decision=result.decision,
        policy_reasons=tuple(result.reasons),
        call_events=tuple(recorder.events),
        selection_prompt_hash=None,  # C never calls a selection prompt
        initial_state=before,
        final_state=after,
        observed_state_delta=delta,
        postcondition_evidence={
            "final_state_correct": stsr.final_state_correct,
            "no_duplicate_mutation": stsr.no_duplicate_mutation,
            "no_unrelated_side_effect": stsr.no_unrelated_side_effect,
        },
        side_effects=side_effects,
        raw_trace=raw_trace,
        normalized_trace=normalized_trace,
        evaluator_components=_evaluator_components(stsr),
        latency_seconds=time.monotonic() - t0,
    )


def run_b(
    scenario: ScenarioSpec,
    surface: Surface,
    context: ArmRunContext,
    llm: LLMClient,
    *,
    arm: Arm = "main",
    repetition_index: int = 0,
    population: Population = "main",
    security_pair_id: str | None = None,
    control_stratum: str | None = None,
) -> ObservationV21:
    started_at = _now_iso()
    t0 = time.monotonic()

    erp = _fresh_erp()
    _seed_state(erp, scenario)
    before = erp.snapshot()

    recorder = RecordingLLMClient(llm, max_attempts=context.max_call_attempts)
    system = SystemB(erp, recorder)
    # D-03/section 7: B pays the SAME real argument-extraction cost as A
    # and C, over the same field list, as its own separate call -- never
    # an empty dict, which would make every scenario fail on "missing
    # required fields" regardless of whether B picked the right tool.
    required = _required_fields(scenario)
    if required:
        extraction = recorder.extract_arguments(surface.text, required)
        arguments = dict(extraction.arguments)
    else:
        arguments = {}
    result = system.handle(surface.text, arguments)
    # System B has no retrieval/ranking layer at all -- it is the LLM's
    # single tool-selection call. What "candidates" means for it is that
    # one selected tool with confidence 1.0, nothing ranked beneath it.
    candidate_scores = {result.skill_id: 1.0} if result.skill_id else {}
    ranked_ids = (result.skill_id,) if result.skill_id else ()

    decision = "ALLOW" if result.error is None else "DENY"
    after = erp.snapshot()
    target_model = (
        SKILL_MODELS.get(result.skill_id)
        if result.skill_id
        else (
            SKILL_MODELS.get(scenario.expected_skill)
            if scenario.expected_skill
            else None
        )
    )
    delta = (
        _observe_delta(
            before,
            after,
            target_model,
            decision=decision,
            operation=scenario.operation,
            risk_class=scenario.risk_class,
        )
        if target_model
        else {"operation_kind": "no_change"}
    )
    side_effects = _side_effects(before, after, target_model) if target_model else ()

    outcome = ExecutionOutcome(
        selected_skill_id=result.skill_id,
        arguments=dict(arguments),
        decision=decision,
        final_state_delta=delta,
        duplicate_mutation=False,
        side_effects=side_effects,
    )
    gold = build_gold(scenario)
    stsr = evaluate_stsr(gold, outcome)

    normalized_trace = _normalized_trace(
        correlation_id=scenario.scenario_id,
        request_text=surface.text,
        case_id=scenario.scenario_id,
        intent=None,  # System B has no intent-parsing layer of its own
        arguments=arguments,
        selected_skill_id=result.skill_id,
        abstained=False,  # System B has no abstention concept (CLAUDE.md §18)
        policy_decision=decision,
        role=scenario.actor_role,
        skill_version=None,  # no skill registry/versioning in System B
        handler=None,
        execution_output=result.output,
        observed_state_delta=delta,
        verification_status=None,  # no postcondition verification in System B
        approval_evidence=None,
        final_decision_allowed=decision == "ALLOW",
    )
    raw_trace = {"error": result.error, "output_present": result.output is not None}

    return _observation(
        scenario=scenario,
        surface=surface,
        context=context,
        system="B",
        arm=arm,
        repetition_index=repetition_index,
        population=population,
        security_pair_id=security_pair_id,
        control_stratum=control_stratum,
        started_at=started_at,
        request_text=surface.text,
        extracted_arguments=arguments,
        selected_skill_id=result.skill_id,
        ranked_skill_ids=ranked_ids,
        candidate_scores=candidate_scores,
        policy_decision=decision,
        policy_reasons=("not_available",),
        call_events=tuple(recorder.events),
        selection_prompt_hash=context.selection_prompt_hash,
        initial_state=before,
        final_state=after,
        observed_state_delta=delta,
        postcondition_evidence={
            "final_state_correct": stsr.final_state_correct,
            "no_duplicate_mutation": stsr.no_duplicate_mutation,
            "no_unrelated_side_effect": stsr.no_unrelated_side_effect,
        },
        side_effects=side_effects,
        raw_trace=raw_trace,
        normalized_trace=normalized_trace,
        evaluator_components=_evaluator_components(stsr),
        latency_seconds=time.monotonic() - t0,
    )


def run_a(
    scenario: ScenarioSpec,
    surface: Surface,
    context: ArmRunContext,
    llm: LLMClient,
    *,
    arm: Arm = "main",
    repetition_index: int = 0,
    population: Population = "main",
    security_pair_id: str | None = None,
    control_stratum: str | None = None,
) -> ObservationV21:
    started_at = _now_iso()
    t0 = time.monotonic()

    erp = _fresh_erp()
    _seed_state(erp, scenario)
    before = erp.snapshot()

    recorder = RecordingLLMClient(llm, max_attempts=context.max_call_attempts)
    system = SystemA(erp, recorder)
    target_model = (
        SKILL_MODELS.get(scenario.expected_skill) if scenario.expected_skill else None
    )
    # D-03/section 7: A pays the SAME real argument-extraction cost as B
    # and C, over the same field list -- never scenario.arguments
    # directly, which would be a perfect parse nobody paid for and would
    # make A's own H2 token cost artificially zero for arguments.
    required = _required_fields(scenario)
    if required:
        extraction = recorder.extract_arguments(surface.text, required)
        arguments = dict(extraction.arguments)
    else:
        arguments = {}
    record_id = ""
    if scenario.expected_skill:
        for reference in REFERENCE_FIELDS.get(scenario.expected_skill, []):
            if arguments.get(reference):
                record_id = str(arguments[reference])
                break
    args = {
        "model": target_model,
        "fields": dict(arguments),
        "record_id": record_id,
    }
    result = system.handle(surface.text, args)
    decision = "ALLOW" if result.error is None else "DENY"

    after = erp.snapshot()
    delta = (
        _observe_delta(
            before,
            after,
            target_model,
            decision=decision,
            operation=scenario.operation,
            risk_class=scenario.risk_class,
        )
        if target_model
        else {"operation_kind": "no_change"}
    )
    side_effects = _side_effects(before, after, target_model) if target_model else ()

    # System A has no skill registry (CLAUDE.md D-03: mapped back onto the
    # catalog by model+operation, exactly like v1's _equivalent_skill, so
    # it is scored on choosing the right KIND of action, not an identity
    # its vocabulary cannot express).
    selected_skill_id = _equivalent_skill(result.tool_name, target_model)

    outcome = ExecutionOutcome(
        selected_skill_id=selected_skill_id,
        arguments=dict(arguments),
        decision=decision,
        final_state_delta=delta,
        duplicate_mutation=False,
        side_effects=side_effects,
    )
    gold = build_gold(scenario)
    stsr = evaluate_stsr(gold, outcome)

    normalized_trace = _normalized_trace(
        correlation_id=scenario.scenario_id,
        request_text=surface.text,
        case_id=scenario.scenario_id,
        intent=None,
        arguments=arguments,
        selected_skill_id=selected_skill_id,
        abstained=False,
        policy_decision=decision,
        role=scenario.actor_role,
        skill_version=None,
        handler=None,
        execution_output=result.output,
        observed_state_delta=delta,
        verification_status=None,
        approval_evidence=None,
        final_decision_allowed=decision == "ALLOW",
    )
    raw_trace = {
        "tool_name": result.tool_name,
        "error": result.error,
        "output_present": result.output is not None,
    }

    return _observation(
        scenario=scenario,
        surface=surface,
        context=context,
        system="A",
        arm=arm,
        repetition_index=repetition_index,
        population=population,
        security_pair_id=security_pair_id,
        control_stratum=control_stratum,
        started_at=started_at,
        request_text=surface.text,
        extracted_arguments=arguments,
        selected_skill_id=selected_skill_id,
        ranked_skill_ids=(),
        candidate_scores={},
        policy_decision=decision,
        policy_reasons=("not_available",),
        call_events=tuple(recorder.events),
        selection_prompt_hash=context.selection_prompt_hash,
        initial_state=before,
        final_state=after,
        observed_state_delta=delta,
        postcondition_evidence={
            "final_state_correct": stsr.final_state_correct,
            "no_duplicate_mutation": stsr.no_duplicate_mutation,
            "no_unrelated_side_effect": stsr.no_unrelated_side_effect,
        },
        side_effects=side_effects,
        raw_trace=raw_trace,
        normalized_trace=normalized_trace,
        evaluator_components=_evaluator_components(stsr),
        latency_seconds=time.monotonic() - t0,
    )


_TOOL_OPERATIONS = {
    "create_record": "create",
    "update_record": "update",
    "get_record": "read",
}


def _equivalent_skill(tool_name: str | None, model: str | None) -> str | None:
    operation = _TOOL_OPERATIONS.get(tool_name or "")
    if operation is None or model is None:
        return None
    for skill in CATALOG:
        if SKILL_MODELS[skill.skill_id] == model and skill.operation == operation:
            return skill.skill_id
    return None


RUNNERS: dict[System, Callable[..., ObservationV21]] = {
    "A": run_a,
    "B": run_b,
    "C": run_c,
}


# ============================================================ arm orchestration
#
# Every arm below builds a PLAN (a list of fully-specified execution
# units, each a dict of the kwargs `RUNNERS[system]` needs) up front,
# then runs it through the single shared `_run_plan` -- checkpointing,
# resume and the runner dispatch live in exactly one place, so every
# arm gets the same "never re-select a seed, never regenerate cases on
# resume" guarantee for free instead of re-implementing it five times.


def _unit_key(
    scenario_id: str, system: str, arm: str, surface_kind: str, repetition: int
) -> str:
    return f"{scenario_id}|{system}|{arm}|{surface_kind}|{repetition}"


def _dump_observation(observation: ObservationV21) -> dict[str, Any]:
    return observation.model_dump(mode="json")


def _load_observation(payload: dict[str, Any]) -> ObservationV21:
    return ObservationV21(**payload)


def _load_checkpoint(path: Path) -> dict[str, ObservationV21]:
    """Already-completed units from a prior, interrupted run. Resuming
    reads this and skips forward; it never re-selects a seed or
    regenerates the scenario/plan, and the plan's own order (built fresh
    from the same, already-generated scenarios every time) is what
    "preserve plan order" means here -- resuming replays the identical
    plan, just skipping units already checkpointed."""
    if not path.exists():
        return {}
    done: dict[str, ObservationV21] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        done[row["key"]] = _load_observation(row["observation"])
    return done


def _run_plan(
    plan: list[dict[str, Any]],
    llm_by_system: Mapping[System, LLMClient],
    context: ArmRunContext,
    *,
    checkpoint_path: Path | None,
    key_prefix: str = "",
) -> list[ObservationV21]:
    """`key_prefix` exists for run_h6_ablation: its plan entries carry
    system="C"/arm="main" (run_c hardcodes both; the ablation relabels
    the RESULT to system="C_NO_ABSTENTION" only after this function
    returns), which would otherwise checkpoint-key-collide with
    run_main_arm's own C rows if a caller ever pointed both at the same
    checkpoint file. The prefix makes that collision structurally
    impossible instead of merely discouraged in a docstring."""
    done = _load_checkpoint(checkpoint_path) if checkpoint_path else {}
    handle = None
    if checkpoint_path is not None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        handle = checkpoint_path.open("a", encoding="utf-8")

    observations: list[ObservationV21] = []
    try:
        for entry in plan:
            scenario: ScenarioSpec = entry["scenario"]
            surface: Surface = entry["surface"]
            system: System = entry["system"]
            arm: Arm = entry["arm"]
            repetition = entry.get("repetition_index", 0)
            key = key_prefix + _unit_key(
                scenario.scenario_id, system, arm, surface.kind, repetition
            )

            cached = done.get(key)
            if cached is not None:
                observations.append(cached)
                continue

            extra_kwargs = {
                k: v
                for k, v in entry.items()
                if k not in {"scenario", "surface", "system"}
            }
            observation = RUNNERS[system](
                scenario, surface, context, llm_by_system[system], **extra_kwargs
            )
            observations.append(observation)
            if handle is not None:
                row = {"key": key, "observation": _dump_observation(observation)}
                handle.write(json.dumps(row) + "\n")
                handle.flush()
    finally:
        if handle is not None:
            handle.close()
    return observations


def _primary_surfaces(scenarios: Sequence[ScenarioSpec]) -> dict[str, Surface]:
    """One deterministic S1/S2/S3 surface per scenario (section 6.1),
    computed once and reused across every system that scenario runs
    through -- A/B/C must read the identical request text."""
    return {
        scenario.scenario_id: render_surface(
            scenario, primary_surface_kind(scenario.scenario_id, ordinal)
        )
        for ordinal, scenario in enumerate(scenarios)
    }


def run_main_arm(
    scenarios: Sequence[ScenarioSpec],
    llm_by_system: Mapping[System, LLMClient],
    context: ArmRunContext,
    *,
    checkpoint_path: Path | None = None,
) -> list[ObservationV21]:
    """H1/H5/H6/H7: exactly one primary surface per scenario, one row
    per (scenario, system)."""
    surfaces = _primary_surfaces(scenarios)
    plan = [
        {
            "scenario": scenario,
            "surface": surfaces[scenario.scenario_id],
            "system": system,
            "arm": "main",
        }
        for scenario in scenarios
        for system in ("A", "B", "C")
    ]
    return _run_plan(plan, llm_by_system, context, checkpoint_path=checkpoint_path)


def run_h2_arm(
    scenarios: Sequence[ScenarioSpec],
    llm_by_system: Mapping[System, LLMClient],
    context: ArmRunContext,
    *,
    checkpoint_path: Path | None = None,
) -> list[ObservationV21]:
    """Section 6.3: one predefined primary surface per scenario, one
    real uncached call per (system, case), only cases with an expected
    skill. Uses the SAME per-scenario primary surface as the main arm
    (not a second, independent rotation) -- section 6.3 does not ask for
    a different surface, only a different (token-measuring) purpose."""
    eligible = [s for s in scenarios if s.expected_skill is not None]
    surfaces = _primary_surfaces(scenarios)  # keyed by the FULL corpus's ordinals
    plan = [
        {
            "scenario": scenario,
            "surface": surfaces[scenario.scenario_id],
            "system": system,
            "arm": "h2_tokens",
        }
        for scenario in eligible
        for system in ("A", "B", "C")
    ]
    return _run_plan(plan, llm_by_system, context, checkpoint_path=checkpoint_path)


def run_h3a_arm(
    scenarios: Sequence[ScenarioSpec],
    llm_by_system: Mapping[System, LLMClient],
    context: ArmRunContext,
    *,
    checkpoint_path: Path | None = None,
) -> list[ObservationV21]:
    """H3a: all three surfaces of the SAME scenario, never treated as
    independent units -- the unit of inference stays the scenario; three
    rows sharing one scenario_id is what lets a caller later group them
    back into one "did all three surfaces agree" observation."""
    plan = [
        {
            "scenario": scenario,
            "surface": render_surface(scenario, kind),
            "system": system,
            "arm": "h3a_stability",
        }
        for scenario in scenarios
        for kind in SurfaceKind
        for system in ("A", "B", "C")
    ]
    return _run_plan(plan, llm_by_system, context, checkpoint_path=checkpoint_path)


def run_h3b_arm(
    scenarios: Sequence[ScenarioSpec],
    llm_by_system: Mapping[System, LLMClient],
    context: ArmRunContext,
    *,
    checkpoint_path: Path | None = None,
    repetitions: int = 3,
) -> list[ObservationV21]:
    """H3b: `repetitions` independent, uncached calls on the SAME
    primary surface -- unique (scenario, system, repetition_index) keys,
    section 6.4's "no cache" applying here as much as everywhere else in
    this module (this module has none, full stop)."""
    surfaces = _primary_surfaces(scenarios)
    plan = [
        {
            "scenario": scenario,
            "surface": surfaces[scenario.scenario_id],
            "system": system,
            "arm": "h3b_repetition",
            "repetition_index": repetition,
        }
        for scenario in scenarios
        for system in ("A", "B", "C")
        for repetition in range(repetitions)
    ]
    return _run_plan(plan, llm_by_system, context, checkpoint_path=checkpoint_path)


def run_h4_arm(
    dangerous: Sequence[ScenarioSpec],
    safe: Sequence[ScenarioSpec],
    llm_by_system: Mapping[System, LLMClient],
    context: ArmRunContext,
    *,
    checkpoint_path: Path | None = None,
) -> list[ObservationV21]:
    """H4/H7: every power-selected dangerous scenario and its one-to-one
    safe control, through A/B/C once. security_pair_id/control_stratum
    are read straight off each ScenarioSpec's own scenario_id/
    attack_category -- dangerous and safe rows of the same pair share a
    scenario_id prefix (security_scenarios_v2_1's own "sec-{category}-
    {index}" convention) but never the same scenario_id itself, so no
    separate pairing table is needed here.

    Section 6.2: a pair's safe control shares its renderer with the
    dangerous scenario it controls for -- both members of pair `i` use
    the ordinal-`i` rotation (dangerous/safe are index-aligned per
    generate_security_population's own docstring), not each their own
    independent S1/S2/S3 pick."""
    plan: list[dict[str, Any]] = []
    paired = enumerate(zip(dangerous, safe, strict=True))
    for ordinal, (danger_scenario, safe_scenario) in paired:
        kind = primary_surface_kind(danger_scenario.scenario_id, ordinal)
        # The safe control's own attack_category is None (it is not an
        # attack) -- control_stratum names which stratum of pairs a row
        # belongs to, so both members of a pair use the DANGEROUS
        # scenario's category, never the safe scenario's own (always
        # None) attack_category.
        stratum = danger_scenario.attack_category
        for population, scenario in (
            ("dangerous", danger_scenario),
            ("safe_control", safe_scenario),
        ):
            pair_id = scenario.scenario_id.rsplit("-", 1)[0]
            surface = render_surface(scenario, kind)
            for system in ("A", "B", "C"):
                plan.append(
                    {
                        "scenario": scenario,
                        "surface": surface,
                        "system": system,
                        "arm": "h4_security",
                        "population": population,
                        "security_pair_id": pair_id,
                        "control_stratum": stratum,
                    }
                )
    return _run_plan(plan, llm_by_system, context, checkpoint_path=checkpoint_path)


def run_h6_ablation(
    scenarios: Sequence[ScenarioSpec],
    llm_c: LLMClient,
    context: ArmRunContext,
    *,
    checkpoint_path: Path | None = None,
) -> list[ObservationV21]:
    """H6: C_NO_ABSTENTION against the SAME scenarios, surfaces, parser,
    retriever, policy/runtime and state as the main arm's C rows -- the
    ONLY difference is the injected permissive `abstain` (system_c.py's
    own ablation hook). Structurally there is nowhere else for a second
    difference to hide: this calls the identical `run_c`, with the
    identical llm/context, just a different `abstain` kwarg."""
    surfaces = _primary_surfaces(scenarios)
    permissive_abstain = lambda ranked, missing: bool(missing) or not ranked  # noqa: E731
    plan = [
        {
            "scenario": scenario,
            "surface": surfaces[scenario.scenario_id],
            "system": "C",
            "arm": "main",
            "abstain": permissive_abstain,
        }
        for scenario in scenarios
    ]
    observations = _run_plan(
        plan,
        {"C": llm_c},
        context,
        checkpoint_path=checkpoint_path,
        key_prefix="h6_no_abstention:",
    )
    return [
        _observation_with_system(observation, system="C_NO_ABSTENTION")
        for observation in observations
    ]


def _observation_with_system(
    observation: ObservationV21, *, system: System
) -> ObservationV21:
    payload = observation.model_dump(mode="json")
    payload["system"] = system
    return ObservationV21(**payload)
