"""Strict raw-observation evidence contract for v2.1 (Task 7B).

docs/tfm-closure-no-human-v2.1.md section 11: every observation keeps a
fixed, versioned, `extra="forbid"` set of fields -- no aggregate may
substitute for a row, and freezing/analysis must fail if any required
field is absent. This module never reads v1's `ExecutionRecord`; v1
stays reproducible on its own schema (erp_agent_os.evidence), and this
module is additive, not a replacement of it.

`ObservationV21` is deliberately NOT a superset that tries to describe
every arm generically with optional fields everywhere -- section 11
lists what every row keeps, and `validate_arm_semantics` (Task 7B step
4) enforces the additional, arm-specific rows that a structurally valid
but semantically empty row would otherwise slip past: an H2 row with no
call events, an H4 dangerous row with no forbidden-delta evidence, or an
H7 row with a normalized trace but no raw one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from erp_agent_os.evidence import write_content_addressed

SCHEMA_VERSION_V21 = "2.1"

Population = Literal["main", "dangerous", "safe_control"]
System = Literal["A", "B", "C", "C_NO_ABSTENTION"]
Arm = Literal["main", "h2_tokens", "h3a_stability", "h3b_repetition", "h4_security"]
CallPurpose = Literal["tool_selection", "argument_extraction"]


class EvidenceV21Error(ValueError):
    """Raised for archive-level or semantic-completeness violations --
    distinct from Pydantic's own per-field ValidationError."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelCallEvent(_Model):
    """One attempt at one model call. Failed calls and retries are
    mandatory rows here, never folded into a summary count -- a system
    that silently retried three times and only kept the successful
    response would otherwise look identical to one that succeeded on
    its first try."""

    purpose: CallPurpose
    attempt: int
    success: bool
    error_class: str | None
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float
    cache_hit: bool = False

    @field_validator("attempt")
    @classmethod
    def attempt_is_at_least_one(cls, value: int) -> int:
        if value < 1:
            raise ValueError("attempt is 1-indexed, must be >= 1")
        return value

    @field_validator("prompt_tokens", "completion_tokens")
    @classmethod
    def tokens_are_not_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("token counts cannot be negative")
        return value

    @field_validator("latency_seconds")
    @classmethod
    def latency_is_not_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("latency_seconds cannot be negative")
        return value

    @model_validator(mode="after")
    def error_class_matches_outcome(self) -> ModelCallEvent:
        if self.success and self.error_class is not None:
            raise ValueError("a successful call must not carry an error_class")
        if not self.success and self.error_class is None:
            raise ValueError("a failed call must record an error_class")
        return self


class ObservationV21(_Model):
    """One raw observation row (docs/tfm-closure-no-human-v2.1.md
    section 11). Every field below is named directly in that section;
    nothing here is inferred or backfilled by this schema itself."""

    schema_version: Literal["2.1"] = "2.1"

    # protocol version y frozen commit
    protocol_version: str
    frozen_commit: str

    # dataset, scenario y surface IDs
    dataset_hash: str
    scenario_id: str
    surface_id: str
    surface_kind: Literal["S1", "S2", "S3"]

    # security pair ID, population y control stratum
    security_pair_id: str | None
    population: Population
    control_stratum: str | None

    # sistema y brazo
    system: System
    arm: Arm
    repetition_index: int

    # proveedor, modelo y parámetros
    provider: str
    model: str
    provider_config_hash: str

    # prompt hashes
    selection_prompt_hash: str | None
    extraction_prompt_hash: str

    # timestamps y correlation ID
    started_at: str
    completed_at: str
    correlation_id: str

    # texto de entrada
    request_text: str

    # argumentos extraídos
    extracted_arguments: dict[str, Any]

    # selección y ranking
    selected_skill_id: str | None
    ranked_skill_ids: tuple[str, ...]
    candidate_scores: dict[str, float]

    # decisión de política
    policy_decision: str
    policy_reasons: tuple[str, ...]

    # llamadas, reintentos y tokens por llamada
    call_events: tuple[ModelCallEvent, ...]

    # latencia
    latency_seconds: float

    # estado inicial y final
    initial_state: dict[str, Any]
    final_state: dict[str, Any]

    # delta observado
    observed_state_delta: dict[str, Any]

    # postcondiciones
    postcondition_evidence: dict[str, bool]

    # efectos laterales
    side_effects: tuple[str, ...]

    # traza cruda y normalizada
    raw_trace: dict[str, Any]
    normalized_trace: dict[str, Any]

    # resultado de cada componente del evaluator
    evaluator_components: dict[str, bool]

    # versión del código y dependencias
    code_version_hash: str
    dependency_lock_hash: str

    @field_validator("repetition_index")
    @classmethod
    def repetition_index_is_not_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("repetition_index cannot be negative")
        return value

    @field_validator("latency_seconds")
    @classmethod
    def latency_is_not_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("latency_seconds cannot be negative")
        return value

    @model_validator(mode="after")
    def population_and_stratum_are_consistent(self) -> ObservationV21:
        if self.population == "main":
            if self.security_pair_id is not None:
                raise ValueError(
                    "a 'main' population row must not carry security_pair_id"
                )
        else:
            if self.security_pair_id is None:
                raise ValueError(
                    f"population={self.population!r} requires security_pair_id"
                )
        return self


def surface_id_for(scenario_id: str, surface_kind: str) -> str:
    """The one place a surface ID is composed, so archive writers and
    consumers can never silently disagree on the convention."""
    return f"{scenario_id}:{surface_kind}"


def validate_arm_semantics(observation: ObservationV21) -> None:
    """Task 7B step 4: a structurally valid ObservationV21 can still be
    semantically empty for the arm it claims to belong to. Each check
    below targets exactly the gap CLAUDE.md's own audit history (units
    21-22) warns about: a check that can never fail is worse than none."""
    arm = observation.arm

    if arm == "h2_tokens":
        if not observation.call_events:
            raise EvidenceV21Error("h2_tokens row has no call_events")
        if any(event.cache_hit for event in observation.call_events):
            raise EvidenceV21Error("h2_tokens row has a cached call_event")

    if arm == "h3a_stability":
        if not observation.surface_id.strip():
            raise EvidenceV21Error("h3a_stability row has an empty surface_id")
        expected = surface_id_for(observation.scenario_id, observation.surface_kind)
        if observation.surface_id != expected:
            raise EvidenceV21Error(
                "h3a_stability row's surface_id does not match its own "
                f"scenario_id/surface_kind: {observation.surface_id!r} != {expected!r}"
            )

    if arm == "h4_security":
        if observation.security_pair_id is None:
            raise EvidenceV21Error("h4_security row has no security_pair_id")
        if observation.control_stratum is None:
            raise EvidenceV21Error("h4_security row has no control_stratum")
        if observation.population == "dangerous":
            # "Forbidden-delta evidence" is the observed_state_delta itself
            # -- a dangerous row must record what state was actually
            # observed (even when that turns out to be a correct no-op),
            # never an empty delta that leaves the question unanswered.
            if "operation_kind" not in observation.observed_state_delta:
                raise EvidenceV21Error(
                    "dangerous row is missing forbidden-delta evidence "
                    "(observed_state_delta.operation_kind)"
                )
        elif observation.population == "safe_control":
            if not observation.evaluator_components:
                raise EvidenceV21Error(
                    "safe_control row has no evaluator_components (its declared "
                    "safe gold outcome must be checkable)"
                )
        else:
            raise EvidenceV21Error(
                f"h4_security row has population={observation.population!r}, "
                "expected 'dangerous' or 'safe_control'"
            )

    if arm == "main":
        # H7's audit reconstructor needs both the raw trace and A/B/C's
        # own normalized mapping of it -- a row with only one of the two
        # cannot support the "recovered without inventing" contract.
        if not observation.raw_trace:
            raise EvidenceV21Error("main row has an empty raw_trace")
        if not observation.normalized_trace:
            raise EvidenceV21Error("main row has an empty normalized_trace")


def _archive_bytes(
    observations: list[ObservationV21], provenance: dict[str, Any]
) -> bytes:
    header = {
        "type": "manifest",
        "schema_version": SCHEMA_VERSION_V21,
        "provenance": provenance,
        "row_count": len(observations),
    }
    rows = [json.dumps(header, sort_keys=True, ensure_ascii=False)]
    rows.extend(
        json.dumps(
            {"type": "observation", "record": observation.model_dump(mode="json")},
            sort_keys=True,
            ensure_ascii=False,
        )
        for observation in observations
    )
    return ("\n".join(rows) + "\n").encode("utf-8")


@dataclass(frozen=True)
class ObservationArchiveV21:
    path: Path
    sha256: str
    row_count: int


def observations_v21_path_for(report_path: Path, sha256: str) -> Path:
    return report_path.with_name(f"{report_path.stem}_observations_v21_{sha256}.jsonl")


def write_observations_v21_jsonl(
    observations: list[ObservationV21],
    report_path: Path,
    *,
    provenance: dict[str, Any],
) -> ObservationArchiveV21:
    content = _archive_bytes(observations, provenance)
    destination, digest = write_content_addressed(
        content, lambda d: observations_v21_path_for(report_path, d)
    )
    return ObservationArchiveV21(destination, digest, len(observations))


@dataclass(frozen=True)
class LoadedObservationsV21:
    schema_version: str
    provenance: dict[str, Any]
    observations: list[ObservationV21]


def load_observations_v21_jsonl(path: Path) -> LoadedObservationsV21:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not path.name.endswith(f"_observations_v21_{digest}.jsonl"):
        raise EvidenceV21Error(
            f"archive filename hash does not match its bytes: {path.name}"
        )

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows or rows[0].get("type") != "manifest":
        raise EvidenceV21Error("observation archive is missing its manifest row")
    header = rows[0]
    observations = [
        ObservationV21(**row["record"])
        for row in rows[1:]
        if row.get("type") == "observation"
    ]
    if header.get("row_count") != len(observations):
        raise EvidenceV21Error("observation archive row count does not match manifest")

    return LoadedObservationsV21(
        schema_version=header["schema_version"],
        provenance=dict(header.get("provenance", {})),
        observations=observations,
    )


def validate_observation_units_v21(
    observations: list[ObservationV21],
    *,
    scenario_ids: set[str],
    systems: set[System],
    arm: Arm,
    repetitions: int,
) -> None:
    """Same duplicate/missing/extra discipline as v1's
    validate_observation_units, keyed by (scenario_id, system, arm,
    repetition_index) -- scenario_id already distinguishes dangerous
    from safe_control rows (their scenario_ids differ), so no separate
    per-population branch is needed here."""
    actual = [
        (o.scenario_id, o.system, o.arm, o.repetition_index)
        for o in observations
        if o.arm == arm
    ]
    unique = set(actual)
    if len(unique) != len(actual):
        raise EvidenceV21Error("duplicate v2.1 observation unit")

    expected = {
        (scenario_id, system, arm, repetition)
        for scenario_id in scenario_ids
        for system in systems
        for repetition in range(repetitions)
    }
    missing = expected - unique
    extra = unique - expected
    if missing:
        raise EvidenceV21Error(f"missing v2.1 observation units: {len(missing)}")
    if extra:
        raise EvidenceV21Error(f"unexpected v2.1 observation units: {len(extra)}")
