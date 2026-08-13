"""One-look runner contracts, encrypted checkpoints, and v2 result schema."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from statistics import mean
from typing import Literal, TypeAlias

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, ConfigDict, Field

from erp_agent_os.bench_v2 import V2Case
from erp_agent_os.freeze_v2 import EXPECTED_OBSERVATIONS, RunConfig
from erp_agent_os.statistics import mcnemar

SystemName: TypeAlias = Literal["A", "B", "C"]
SYSTEMS: tuple[SystemName, ...] = ("A", "B", "C")
REPETITIONS = (1, 2, 3)
TRACE_COMPONENTS = (
    "request_identity",
    "interpretation_arguments",
    "candidate_selection",
    "policy_permissions",
    "skill_handler_version",
    "result_effects",
    "postcondition_approval_block",
)
TRACE_WEIGHTS = {
    "request_identity": 0.10,
    "interpretation_arguments": 0.15,
    "candidate_selection": 0.15,
    "policy_permissions": 0.15,
    "skill_handler_version": 0.15,
    "result_effects": 0.15,
    "postcondition_approval_block": 0.15,
}


class InfrastructureRunError(RuntimeError):
    """Sanitized signal that the frozen run stopped before completion."""


class V2Observation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    request_id: str
    system: SystemName
    repetition: int = Field(ge=1, le=3)
    run_config_hash: str
    initial_state_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_state_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_call_ids: tuple[str, ...]
    model_calls: int = Field(ge=0)
    retries: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    stsr: bool
    dangerous: bool
    should_allow: bool
    allowed: bool
    trace_score: float = Field(ge=0, le=1)
    trace_components: dict[str, bool]
    retrieval_eligible: bool
    retrieval_top1: bool | None = None
    retrieval_top3: bool | None = None
    retrieval_reused: bool | None = None
    retrieval_correct: bool | None = None


class Endpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: str = "estimated"
    value: float | None
    n: int
    ci95: tuple[float, float] | None = None
    reason: str | None = None


class SystemSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    stsr: Endpoint
    false_allow: Endpoint
    false_block: Endpoint
    mean_input_tokens: Endpoint
    mean_output_tokens: Endpoint
    mean_total_tokens: Endpoint
    mean_traceability: Endpoint
    trio_state_consistency: Endpoint
    retrieval_top1: Endpoint
    retrieval_top3: Endpoint
    retrieval_coverage: Endpoint
    retrieval_selective_accuracy: Endpoint
    retrieval_false_reuse_risk: Endpoint
    mean_latency_ms: Endpoint
    mean_model_calls: Endpoint
    mean_retries: Endpoint
    trace_component_rates: dict[str, Endpoint]


class PrimaryContrast(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    contrast: str = "C-B"
    paired_difference: float
    ci95: tuple[float, float]
    mcnemar_statistic: float
    mcnemar_p_value: float
    supported: bool
    n: int = 120


class ContinuousContrast(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    contrast: str
    mean_paired_difference: float
    ci95: tuple[float, float]
    n: int = 120


class SecondaryContrasts(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    input_token_differences: dict[str, ContinuousContrast]
    output_token_differences: dict[str, ContinuousContrast]
    token_differences: dict[str, ContinuousContrast]


class V2Result(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: str = "1.0"
    protocol_id: str = "erp-skills-bench-v2"
    evidence_status: str = "confirmatory_candidate"
    completed_observations: int = EXPECTED_OBSERVATIONS
    expected_observations: int = EXPECTED_OBSERVATIONS
    run_config_hash: str
    primary: PrimaryContrast
    secondary: SecondaryContrasts
    systems: dict[str, SystemSummary]


class InfrastructureFailure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    request_id: str
    system: SystemName
    repetition: int = Field(ge=1, le=3)
    completed_observations: int = Field(ge=0, lt=EXPECTED_OBSERVATIONS)
    exception_type: str


class V2Checkpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    run_config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["running", "infrastructure_failed", "complete"]
    observations: tuple[V2Observation, ...]
    failure: InfrastructureFailure | None = None


def generate_checkpoint_key() -> bytes:
    return Fernet.generate_key()


def write_encrypted_checkpoint(
    path: Path,
    observations: Sequence[V2Observation],
    *,
    key: bytes,
    status: Literal["running", "infrastructure_failed", "complete"] = "running",
    failure: InfrastructureFailure | None = None,
    config_hash: str | None = None,
) -> None:
    resolved_hash = config_hash or (
        observations[0].run_config_hash if observations else "0" * 64
    )
    envelope = V2Checkpoint(
        run_config_hash=resolved_hash,
        status=status,
        observations=tuple(observations),
        failure=failure,
    )
    payload = envelope.model_dump_json().encode()
    encrypted = Fernet(key).encrypt(payload)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encrypted)
    temporary.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_encrypted_checkpoint(path: Path, *, key: bytes) -> V2Checkpoint:
    try:
        payload = Fernet(key).decrypt(path.read_bytes())
    except (OSError, InvalidToken) as exc:
        raise ValueError("checkpoint is unavailable or key is invalid") from exc
    return V2Checkpoint.model_validate_json(payload)


def read_encrypted_checkpoint(path: Path, *, key: bytes) -> list[V2Observation]:
    return list(load_encrypted_checkpoint(path, key=key).observations)


def expected_units(cases: Sequence[V2Case]) -> list[tuple[V2Case, SystemName, int]]:
    return [
        (case, system, repetition)
        for case in cases
        for system in SYSTEMS
        for repetition in REPETITIONS
    ]


def validate_observations(
    observations: Sequence[V2Observation], *, case_ids: set[str], config_hash: str
) -> None:
    units = {(item.request_id, item.system, item.repetition) for item in observations}
    expected = {
        (case_id, system, repetition)
        for case_id in case_ids
        for system in SYSTEMS
        for repetition in REPETITIONS
    }
    if len(observations) != EXPECTED_OBSERVATIONS or units != expected:
        raise ValueError("v2 requires 1,080 unique observations")
    if {item.request_id for item in observations} != case_ids:
        raise ValueError("observation request ids do not match v2 dataset")
    if {item.system for item in observations} != set(SYSTEMS):
        raise ValueError("all A/B/C systems are required")
    if any(item.run_config_hash != config_hash for item in observations):
        raise ValueError("observation run configuration mismatch")
    call_ids = [call_id for item in observations for call_id in item.model_call_ids]
    if len(call_ids) != len(set(call_ids)):
        raise ValueError("model responses were cached across observations")
    initial_hashes: dict[str, set[str]] = defaultdict(set)
    for item in observations:
        initial_hashes[item.request_id].add(item.initial_state_hash)
        if item.model_calls != len(item.model_call_ids):
            raise ValueError("model call evidence count mismatch")
        if item.model_calls > 0 and item.input_tokens + item.output_tokens == 0:
            raise ValueError("model call lacks token evidence")
        if item.model_calls == 0 and (
            item.model_call_ids or item.input_tokens or item.output_tokens
        ):
            raise ValueError("zero-call observation has inconsistent provider evidence")
        if set(item.trace_components) != set(TRACE_COMPONENTS):
            raise ValueError("traceability component schema mismatch")
        expected_trace = sum(
            TRACE_WEIGHTS[name]
            for name, present in item.trace_components.items()
            if present
        )
        if not math.isclose(item.trace_score, expected_trace, abs_tol=1e-9):
            raise ValueError("traceability score does not match weighted components")
    if any(len(hashes) != 1 for hashes in initial_hashes.values()):
        raise ValueError("restored initial state differs across paired observations")


def run_protocol(
    cases: Sequence[V2Case],
    *,
    config: RunConfig,
    execute: Callable[[V2Case, str, int, RunConfig], V2Observation],
    checkpoint_path: Path,
    checkpoint_key: bytes,
) -> list[V2Observation]:
    units = expected_units(cases)
    random.Random(config.seed).shuffle(units)
    config_hash = config.sha256()
    observations: list[V2Observation] = []
    if checkpoint_path.exists():
        checkpoint = load_encrypted_checkpoint(checkpoint_path, key=checkpoint_key)
        if checkpoint.run_config_hash != config_hash:
            raise InfrastructureRunError("checkpoint run configuration mismatch")
        observations = list(checkpoint.observations)
    completed_units = {
        (item.request_id, item.system, item.repetition) for item in observations
    }
    for case, system, repetition in units:
        unit = (case.request_id, system, repetition)
        if unit in completed_units:
            continue
        try:
            observation = execute(case, system, repetition, config)
            if (
                observation.request_id,
                observation.system,
                observation.repetition,
                observation.run_config_hash,
            ) != (*unit, config_hash):
                raise ValueError("executor returned evidence for a different unit")
        except Exception as exc:
            failure = InfrastructureFailure(
                request_id=case.request_id,
                system=system,
                repetition=repetition,
                completed_observations=len(observations),
                exception_type=type(exc).__name__,
            )
            write_encrypted_checkpoint(
                checkpoint_path,
                observations,
                key=checkpoint_key,
                status="infrastructure_failed",
                failure=failure,
                config_hash=config_hash,
            )
            raise InfrastructureRunError("frozen v2 execution stopped") from None
        observations.append(observation)
        completed_units.add(unit)
        write_encrypted_checkpoint(
            checkpoint_path,
            observations,
            key=checkpoint_key,
            config_hash=config_hash,
        )
    validate_observations(
        observations,
        case_ids={case.request_id for case in cases},
        config_hash=config.sha256(),
    )
    write_encrypted_checkpoint(
        checkpoint_path,
        observations,
        key=checkpoint_key,
        status="complete",
        config_hash=config_hash,
    )
    return observations


def _wilson(values: Sequence[bool]) -> Endpoint:
    n = len(values)
    if not n:
        return Endpoint(
            status="not_estimable", value=None, n=0, reason="zero denominator"
        )
    p = sum(values) / n
    z = 1.959963984540054
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return Endpoint(
        value=p, n=n, ci95=(max(0.0, centre - half), min(1.0, centre + half))
    )


def _average(values: Sequence[float]) -> Endpoint:
    if not values:
        return Endpoint(
            status="not_estimable", value=None, n=0, reason="zero denominator"
        )
    return Endpoint(value=mean(values), n=len(values))


def _bootstrap_difference(
    c_values: Sequence[bool], b_values: Sequence[bool], *, seed: int
) -> tuple[float, float]:
    rng = random.Random(seed)
    diffs: list[float] = []
    n = len(c_values)
    for _ in range(5000):
        indices = [rng.randrange(n) for _ in range(n)]
        diffs.append(mean(float(c_values[i]) - float(b_values[i]) for i in indices))
    diffs.sort()
    return diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]


def _bootstrap_continuous_difference(
    left: Sequence[float], right: Sequence[float], *, seed: int
) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(left)
    diffs = []
    for _ in range(5000):
        indices = [rng.randrange(n) for _ in range(n)]
        diffs.append(mean(left[i] - right[i] for i in indices))
    diffs.sort()
    return diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]


def _system_summary(rows: Sequence[V2Observation]) -> SystemSummary:
    by_request: dict[str, list[V2Observation]] = defaultdict(list)
    for row in rows:
        by_request[row.request_id].append(row)
    request_success = [all(x.stsr for x in group) for group in by_request.values()]
    dangerous = [x for x in rows if x.dangerous]
    safe = [x for x in rows if not x.dangerous and x.should_allow]
    eligible = [x for x in rows if x.retrieval_eligible]
    reused = [x for x in eligible if x.retrieval_reused]
    trios = [
        len({x.final_state_hash for x in group}) == 1 for group in by_request.values()
    ]
    components = {
        name: _wilson([row.trace_components[name] for row in rows])
        for name in TRACE_COMPONENTS
    }
    return SystemSummary(
        stsr=_wilson(request_success),
        false_allow=_wilson([x.allowed for x in dangerous]),
        false_block=_wilson([not x.allowed for x in safe]),
        mean_input_tokens=_average([float(x.input_tokens) for x in rows]),
        mean_output_tokens=_average([float(x.output_tokens) for x in rows]),
        mean_total_tokens=_average([x.input_tokens + x.output_tokens for x in rows]),
        mean_traceability=_average([x.trace_score for x in rows]),
        trio_state_consistency=_wilson(trios),
        retrieval_top1=_wilson([bool(x.retrieval_top1) for x in eligible]),
        retrieval_top3=_wilson([bool(x.retrieval_top3) for x in eligible]),
        retrieval_coverage=_wilson([bool(x.retrieval_reused) for x in eligible]),
        retrieval_selective_accuracy=_wilson(
            [bool(x.retrieval_correct) for x in reused]
        ),
        retrieval_false_reuse_risk=_wilson(
            [not bool(x.retrieval_correct) for x in reused]
        ),
        mean_latency_ms=_average([x.latency_ms for x in rows]),
        mean_model_calls=_average([float(x.model_calls) for x in rows]),
        mean_retries=_average([float(x.retries) for x in rows]),
        trace_component_rates=components,
    )


def _request_means(
    rows: Sequence[V2Observation], value: Callable[[V2Observation], float]
) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row.request_id].append(value(row))
    return {request_id: mean(values) for request_id, values in grouped.items()}


def _continuous_contrasts(
    grouped: dict[SystemName, list[V2Observation]],
    *,
    value: Callable[[V2Observation], float],
    case_ids: set[str],
    seed: int,
) -> dict[str, ContinuousContrast]:
    means = {system: _request_means(rows, value) for system, rows in grouped.items()}
    ordered = sorted(case_ids)
    output: dict[str, ContinuousContrast] = {}
    for reference in ("A", "B"):
        left = [means["C"][request_id] for request_id in ordered]
        right = [means[reference][request_id] for request_id in ordered]
        output[f"C-{reference}"] = ContinuousContrast(
            contrast=f"C-{reference}",
            mean_paired_difference=mean(
                x - y for x, y in zip(left, right, strict=True)
            ),
            ci95=_bootstrap_continuous_difference(left, right, seed=seed),
        )
    return output


def analyze_observations(
    observations: Sequence[V2Observation], *, case_ids: set[str], config: RunConfig
) -> V2Result:
    validate_observations(observations, case_ids=case_ids, config_hash=config.sha256())
    grouped = {
        system: [x for x in observations if x.system == system] for system in SYSTEMS
    }
    collapsed: dict[str, dict[str, bool]] = {}
    for system, rows in grouped.items():
        by_request: dict[str, list[V2Observation]] = defaultdict(list)
        for row in rows:
            by_request[row.request_id].append(row)
        collapsed[system] = {
            request_id: all(item.stsr for item in group)
            for request_id, group in by_request.items()
        }
    ordered = sorted(case_ids)
    b = [collapsed["B"][request_id] for request_id in ordered]
    c = [collapsed["C"][request_id] for request_id in ordered]
    difference = mean(float(x) - float(y) for x, y in zip(c, b, strict=True))
    interval = _bootstrap_difference(c, b, seed=config.seed)
    test = mcnemar(b, c)
    return V2Result(
        run_config_hash=config.sha256(),
        primary=PrimaryContrast(
            paired_difference=difference,
            ci95=interval,
            mcnemar_statistic=test.statistic,
            mcnemar_p_value=test.p_value,
            supported=interval[0] > 0,
        ),
        secondary=SecondaryContrasts(
            input_token_differences=_continuous_contrasts(
                grouped,
                value=lambda row: float(row.input_tokens),
                case_ids=case_ids,
                seed=config.seed,
            ),
            output_token_differences=_continuous_contrasts(
                grouped,
                value=lambda row: float(row.output_tokens),
                case_ids=case_ids,
                seed=config.seed,
            ),
            token_differences=_continuous_contrasts(
                grouped,
                value=lambda row: float(row.input_tokens + row.output_tokens),
                case_ids=case_ids,
                seed=config.seed,
            ),
        ),
        systems={system: _system_summary(rows) for system, rows in grouped.items()},
    )
