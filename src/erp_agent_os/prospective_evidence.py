"""Sealed v2 candidates and blinded human-annotation workflow artifacts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from erp_agent_os.agreement import cohens_kappa
from erp_agent_os.bench_intents import INTENTS_BY_ID
from erp_agent_os.catalog import CATALOG_BY_ID
from erp_agent_os.dataset import (
    ABSTENTION_SENTINEL,
    BenchmarkCase,
    CaseLabel,
    DatasetSplit,
    ExpectedDecision,
    RiskClass,
)
from erp_agent_os.experiment import _fresh_erp
from erp_agent_os.freeze import compute_manifest
from erp_agent_os.handlers import HANDLERS
from erp_agent_os.validation import normalize_arguments, validate_arguments

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_SCHEMA_VERSION = "1.0"
ANNOTATION_FIELDS = (
    "request_id",
    "request_text",
    "annotator_id",
    "annotated_intent",
    "annotated_skill",
    "annotated_arguments_json",
    "annotated_decision",
    "annotated_risk_class",
    "annotated_error_type",
    "annotated_case_label",
    "clarification_required",
    "state_transition",
    "annotation_status",
    "notes",
)


@dataclass(frozen=True)
class CandidateSeal:
    candidates_path: Path
    author_proposals_path: Path
    manifest_path: Path
    annotation_packets: tuple[Path, Path]
    candidates_sha256: str
    author_proposals_sha256: str


class HumanGateIncomplete(ValueError):
    """Raised when a human-only release gate is incomplete or inconsistent."""


@dataclass(frozen=True)
class HumanAnnotation:
    request_id: str
    request_text: str
    intent: str
    skill: str
    arguments: dict[str, Any]
    decision: str
    risk_class: str
    error_type: str
    case_label: str
    clarification_required: bool
    state_transition: str

    def comparison_payload(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "skill": self.skill,
            "arguments": self.arguments,
            "decision": self.decision,
            "risk_class": self.risk_class,
            "error_type": self.error_type,
            "case_label": self.case_label,
            "clarification_required": self.clarification_required,
            "state_transition": self.state_transition,
        }


@dataclass(frozen=True)
class AnnotationReview:
    n_cases: int
    agreement_rate: float
    decision_kappa: float
    annotator_ids: tuple[str, str]
    disagreements: tuple[str, ...]
    consensus: dict[str, HumanAnnotation]
    annotations: dict[str, tuple[HumanAnnotation, HumanAnnotation]]

    @property
    def semantic_gate_passed(self) -> bool:
        return not self.disagreements and len(self.consensus) == self.n_cases


@dataclass(frozen=True)
class StateReviewBundle:
    proposed_cases: list[BenchmarkCase]
    proposals_path: Path
    review_packets: tuple[Path, Path]
    proposals_sha256: str


@dataclass(frozen=True)
class FinalizedHoldout:
    gold_path: Path
    manifest_path: Path
    gold_sha256: str


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _jsonl(rows: list[dict[str, object]]) -> bytes:
    return (
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows)
        + "\n"
    ).encode("utf-8")


def _atomic_write_once(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(
                f"sealed artifact already exists with other bytes: {path}"
            )
        return
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _experiment_code_hash() -> str:
    paths = sorted((PROJECT_ROOT / "src" / "erp_agent_os").glob("*.py"))
    paths.append(PROJECT_ROOT / "scripts" / "run_experiment.py")
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _candidate_rows(cases: list[BenchmarkCase]) -> list[dict[str, object]]:
    return [
        {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "request_id": case.request_id,
            "request_text": case.request_text,
        }
        for case in cases
    ]


def _author_rows(cases: list[BenchmarkCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in cases:
        row = case.model_dump(mode="json")
        row["labels"] = sorted(row["labels"])
        row["evidence_role"] = "author_proposal_not_oracle"
        rows.append(row)
    return rows


def _gold_rows(cases: list[BenchmarkCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in cases:
        row = case.model_dump(mode="json")
        row["labels"] = sorted(row["labels"])
        rows.append(row)
    return rows


def _annotation_packet(cases: list[BenchmarkCase], annotator_id: str) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=ANNOTATION_FIELDS, lineterminator="\n")
    writer.writeheader()
    for case in cases:
        writer.writerow(
            {
                "request_id": case.request_id,
                "request_text": case.request_text,
                "annotator_id": annotator_id,
            }
        )
    return stream.getvalue().encode("utf-8")


def seal_candidate_holdout(
    cases: list[BenchmarkCase], destination_dir: Path
) -> CandidateSeal:
    """Seal candidates without enabling system evaluation or faking humans."""
    candidate_content = _jsonl(_candidate_rows(cases))
    author_content = _jsonl(_author_rows(cases))
    candidate_hash = _sha256(candidate_content)
    author_hash = _sha256(author_content)
    frozen_protocol = compute_manifest()
    candidates_path = destination_dir / f"bench_v2_candidates_{candidate_hash}.jsonl"
    author_path = destination_dir / f"bench_v2_author_proposals_{author_hash}.jsonl"
    _atomic_write_once(candidates_path, candidate_content)
    _atomic_write_once(author_path, author_content)

    packet_paths: list[Path] = []
    packet_hashes: dict[str, str] = {}
    for index in (1, 2):
        packet = _annotation_packet(cases, f"annotator_{index}")
        path = destination_dir / f"bench_v2_annotation_annotator_{index}.csv"
        # Human-editable packets are never overwritten after first creation.
        if not path.exists():
            _atomic_write_once(path, packet)
        packet_paths.append(path)
        packet_hashes[f"annotator_{index}_blank_template_sha256"] = _sha256(packet)

    manifest = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "status": "v2_candidates_sealed_awaiting_human_annotation",
        "system_evaluation_allowed": False,
        "n_cases": len(cases),
        "created_on": "2026-08-13",
        "human_requirements": {
            "independent_semantic_annotators": 2,
            "adjudication_required_for_disagreements": True,
            "independent_state_reviewers": 2,
        },
        "hashes": {
            "candidates_sha256": candidate_hash,
            "author_proposals_sha256": author_hash,
            "experiment_code_sha256": _experiment_code_hash(),
            "catalog_sha256": frozen_protocol.catalog_hash,
            "prompt_sha256": frozen_protocol.prompt_hash,
            "provider_config_sha256": frozen_protocol.provider_config_hash,
            **packet_hashes,
        },
        "paths": {
            "candidates": candidates_path.name,
            "author_proposals": author_path.name,
            "annotation_packets": [path.name for path in packet_paths],
        },
    }
    manifest_content = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    manifest_hash = _sha256(manifest_content)
    manifest_path = destination_dir / f"bench_v2_candidate_seal_{manifest_hash}.json"
    _atomic_write_once(manifest_path, manifest_content)
    return CandidateSeal(
        candidates_path=candidates_path,
        author_proposals_path=author_path,
        manifest_path=manifest_path,
        annotation_packets=(packet_paths[0], packet_paths[1]),
        candidates_sha256=candidate_hash,
        author_proposals_sha256=author_hash,
    )


def _load_annotation_packet(
    path: Path, cases: list[BenchmarkCase]
) -> tuple[str, dict[str, HumanAnnotation]]:
    expected = {case.request_id: case for case in cases}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(cases):
        raise HumanGateIncomplete(f"{path.name}: expected {len(cases)} rows")
    ids = [row.get("request_id", "") for row in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(expected):
        raise HumanGateIncomplete(f"{path.name}: duplicate, missing or extra cases")
    annotator_ids = {row.get("annotator_id", "").strip() for row in rows}
    if len(annotator_ids) != 1 or "" in annotator_ids:
        raise HumanGateIncomplete(f"{path.name}: one nonblank annotator_id required")

    incomplete = [
        row["request_id"]
        for row in rows
        if row.get("annotation_status", "").strip().upper() != "COMPLETE"
    ]
    if incomplete:
        raise HumanGateIncomplete(
            f"{path.name}: {len(incomplete)} incomplete human annotations"
        )

    parsed: dict[str, HumanAnnotation] = {}
    for row in rows:
        request_id = row["request_id"]
        if row.get("request_text") != expected[request_id].request_text:
            raise HumanGateIncomplete(
                f"{path.name}: request text changed for {request_id}"
            )
        intent = row.get("annotated_intent", "").strip()
        skill = row.get("annotated_skill", "").strip()
        decision = row.get("annotated_decision", "").strip()
        risk_class = row.get("annotated_risk_class", "").strip()
        error_type = row.get("annotated_error_type", "").strip()
        case_label = row.get("annotated_case_label", "").strip()
        clarification = row.get("clarification_required", "").strip().lower()
        state_transition = row.get("state_transition", "").strip().upper()
        try:
            arguments = json.loads(row.get("annotated_arguments_json", ""))
        except json.JSONDecodeError as exc:
            raise HumanGateIncomplete(
                f"{path.name}: invalid arguments JSON for {request_id}"
            ) from exc
        if not isinstance(arguments, dict):
            raise HumanGateIncomplete(
                f"{path.name}: arguments must be an object for {request_id}"
            )
        if intent not in INTENTS_BY_ID:
            raise HumanGateIncomplete(f"{path.name}: unknown intent for {request_id}")
        if skill not in CATALOG_BY_ID and skill != ABSTENTION_SENTINEL:
            raise HumanGateIncomplete(f"{path.name}: unknown skill for {request_id}")
        if decision not in {item.value for item in ExpectedDecision}:
            raise HumanGateIncomplete(f"{path.name}: invalid decision for {request_id}")
        if risk_class not in {item.value for item in RiskClass}:
            raise HumanGateIncomplete(f"{path.name}: invalid risk for {request_id}")
        if not error_type:
            raise HumanGateIncomplete(
                f"{path.name}: error type is required for {request_id}"
            )
        if case_label not in {item.value for item in CaseLabel}:
            raise HumanGateIncomplete(f"{path.name}: invalid label for {request_id}")
        if clarification not in {"true", "false"}:
            raise HumanGateIncomplete(
                f"{path.name}: clarification must be true/false for {request_id}"
            )
        if state_transition not in {"MAY_CHANGE", "UNCHANGED"}:
            raise HumanGateIncomplete(
                f"{path.name}: invalid state transition for {request_id}"
            )
        parsed[request_id] = HumanAnnotation(
            request_id=request_id,
            request_text=expected[request_id].request_text,
            intent=intent,
            skill=skill,
            arguments=arguments,
            decision=decision,
            risk_class=risk_class,
            error_type=error_type,
            case_label=case_label,
            clarification_required=clarification == "true",
            state_transition=state_transition,
        )
    return next(iter(annotator_ids)), parsed


def review_annotation_packets(
    cases: list[BenchmarkCase], first_path: Path, second_path: Path
) -> AnnotationReview:
    """Validate two human packets and compute agreement without author labels."""
    first_id, first = _load_annotation_packet(first_path, cases)
    second_id, second = _load_annotation_packet(second_path, cases)
    if first_id == second_id:
        raise HumanGateIncomplete("two distinct human annotator IDs are required")

    ordered_ids = [case.request_id for case in cases]
    disagreements: list[str] = []
    consensus: dict[str, HumanAnnotation] = {}
    annotations: dict[str, tuple[HumanAnnotation, HumanAnnotation]] = {}
    for request_id in ordered_ids:
        pair = (first[request_id], second[request_id])
        annotations[request_id] = pair
        if pair[0].comparison_payload() == pair[1].comparison_payload():
            consensus[request_id] = pair[0]
        else:
            disagreements.append(request_id)
    kappa = cohens_kappa(
        [first[request_id].decision for request_id in ordered_ids],
        [second[request_id].decision for request_id in ordered_ids],
    )
    return AnnotationReview(
        n_cases=len(cases),
        agreement_rate=(len(cases) - len(disagreements)) / len(cases),
        decision_kappa=kappa.kappa,
        annotator_ids=(first_id, second_id),
        disagreements=tuple(disagreements),
        consensus=consensus,
        annotations=annotations,
    )


def write_adjudication_packet(review: AnnotationReview, destination_dir: Path) -> Path:
    """Write only disagreements; never expose the author's proposed labels."""
    fieldnames = (
        "request_id",
        "request_text",
        "annotator_1_json",
        "annotator_2_json",
        "adjudicator_id",
        "adjudicated_intent",
        "adjudicated_skill",
        "adjudicated_arguments_json",
        "adjudicated_decision",
        "adjudicated_risk_class",
        "adjudicated_error_type",
        "adjudicated_case_label",
        "clarification_required",
        "state_transition",
        "adjudication_status",
        "notes",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for request_id in review.disagreements:
        first, second = review.annotations[request_id]
        writer.writerow(
            {
                "request_id": request_id,
                "request_text": first.request_text,
                "annotator_1_json": json.dumps(
                    first.comparison_payload(), sort_keys=True, ensure_ascii=False
                ),
                "annotator_2_json": json.dumps(
                    second.comparison_payload(), sort_keys=True, ensure_ascii=False
                ),
            }
        )
    path = destination_dir / "bench_v2_adjudication.csv"
    if not path.exists():
        _atomic_write_once(path, stream.getvalue().encode("utf-8"))
    return path


def apply_adjudication_packet(
    review: AnnotationReview, adjudication_path: Path
) -> AnnotationReview:
    """Validate third-party resolutions and merge them into semantic consensus."""
    if not review.disagreements:
        return review
    with adjudication_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected_ids = set(review.disagreements)
    row_ids = [row.get("request_id", "") for row in rows]
    if len(rows) != len(expected_ids) or set(row_ids) != expected_ids:
        raise HumanGateIncomplete(
            f"{adjudication_path.name}: incomplete adjudication coverage"
        )
    if len(set(row_ids)) != len(row_ids):
        raise HumanGateIncomplete(
            f"{adjudication_path.name}: duplicate adjudication rows"
        )
    incomplete = [
        row["request_id"]
        for row in rows
        if row.get("adjudication_status", "").strip().upper() != "COMPLETE"
    ]
    if incomplete:
        raise HumanGateIncomplete(
            f"{adjudication_path.name}: {len(incomplete)} incomplete adjudication rows"
        )
    adjudicator_ids = {row.get("adjudicator_id", "").strip() for row in rows}
    if len(adjudicator_ids) != 1 or "" in adjudicator_ids:
        raise HumanGateIncomplete(
            f"{adjudication_path.name}: one nonblank adjudicator_id required"
        )
    adjudicator_id = next(iter(adjudicator_ids))
    if adjudicator_id in review.annotator_ids:
        raise HumanGateIncomplete(
            f"{adjudication_path.name}: adjudicator must be a third person"
        )

    consensus = dict(review.consensus)
    allowed_decisions = {item.value for item in ExpectedDecision}
    allowed_risks = {item.value for item in RiskClass}
    allowed_labels = {item.value for item in CaseLabel}
    for row in rows:
        request_id = row["request_id"]
        first, second = review.annotations[request_id]
        if row.get("request_text") != first.request_text:
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: request text changed for {request_id}"
            )
        try:
            first_snapshot = json.loads(row.get("annotator_1_json", ""))
            second_snapshot = json.loads(row.get("annotator_2_json", ""))
            arguments = json.loads(row.get("adjudicated_arguments_json", ""))
        except json.JSONDecodeError as exc:
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: invalid JSON for {request_id}"
            ) from exc
        if (
            first_snapshot != first.comparison_payload()
            or second_snapshot != second.comparison_payload()
        ):
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: human annotations changed for {request_id}"
            )
        intent = row.get("adjudicated_intent", "").strip()
        skill = row.get("adjudicated_skill", "").strip()
        decision = row.get("adjudicated_decision", "").strip()
        risk_class = row.get("adjudicated_risk_class", "").strip()
        error_type = row.get("adjudicated_error_type", "").strip()
        case_label = row.get("adjudicated_case_label", "").strip()
        clarification = row.get("clarification_required", "").strip().lower()
        state_transition = row.get("state_transition", "").strip().upper()
        if not isinstance(arguments, dict):
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: arguments must be an object "
                f"for {request_id}"
            )
        if intent not in INTENTS_BY_ID:
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: unknown intent for {request_id}"
            )
        if skill not in CATALOG_BY_ID and skill != ABSTENTION_SENTINEL:
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: unknown skill for {request_id}"
            )
        if decision not in allowed_decisions or risk_class not in allowed_risks:
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: invalid decision or risk for {request_id}"
            )
        if not error_type or case_label not in allowed_labels:
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: invalid error type or label "
                f"for {request_id}"
            )
        if clarification not in {"true", "false"}:
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: clarification must be true/false "
                f"for {request_id}"
            )
        if state_transition not in {"MAY_CHANGE", "UNCHANGED"}:
            raise HumanGateIncomplete(
                f"{adjudication_path.name}: invalid state transition for {request_id}"
            )
        consensus[request_id] = HumanAnnotation(
            request_id=request_id,
            request_text=first.request_text,
            intent=intent,
            skill=skill,
            arguments=arguments,
            decision=decision,
            risk_class=risk_class,
            error_type=error_type,
            case_label=case_label,
            clarification_required=clarification == "true",
            state_transition=state_transition,
        )
    return AnnotationReview(
        n_cases=review.n_cases,
        agreement_rate=review.agreement_rate,
        decision_kappa=review.decision_kappa,
        annotator_ids=review.annotator_ids,
        disagreements=(),
        consensus=consensus,
        annotations=review.annotations,
    )


def _case_from_annotation(
    original: BenchmarkCase, annotation: HumanAnnotation
) -> BenchmarkCase:
    return original.model_copy(
        update={
            "canonical_intent": annotation.intent,
            "expected_skill": annotation.skill,
            "expected_arguments": annotation.arguments,
            "expected_decision": ExpectedDecision(annotation.decision),
            "risk_class": RiskClass(annotation.risk_class),
            "module": INTENTS_BY_ID[annotation.intent].family,
            "clarification_required": annotation.clarification_required,
            "approval_required": annotation.decision
            == ExpectedDecision.REQUIRE_APPROVAL.value,
            "error_type": annotation.error_type,
            "labels": {CaseLabel(annotation.case_label)},
        }
    )


def _propose_exact_states(case: BenchmarkCase) -> BenchmarkCase:
    erp = _fresh_erp(case)
    initial_state = erp.snapshot()
    if (
        case.expected_decision is ExpectedDecision.ALLOW
        and case.expected_skill != ABSTENTION_SENTINEL
    ):
        skill = CATALOG_BY_ID[case.expected_skill]
        arguments = normalize_arguments(skill, case.expected_arguments)
        findings = validate_arguments(skill, arguments)
        if findings:
            raise HumanGateIncomplete(
                f"reference state proposal has invalid arguments for {case.request_id}"
            )
        try:
            HANDLERS[case.expected_skill](erp, arguments)
        except Exception as exc:
            raise HumanGateIncomplete(
                f"reference state proposal failed for {case.request_id}: {exc}"
            ) from exc
    return case.model_copy(
        update={
            "initial_state": initial_state,
            "expected_final_state": erp.snapshot(),
        }
    )


def _state_review_packet(
    cases: list[BenchmarkCase], reviewer_id: str, proposal_hash: str
) -> bytes:
    fields = (
        "request_id",
        "request_text",
        "reviewer_id",
        "proposal_sha256",
        "initial_state_json",
        "expected_final_state_json",
        "state_verdict",
        "state_review_status",
        "notes",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for case in cases:
        writer.writerow(
            {
                "request_id": case.request_id,
                "request_text": case.request_text,
                "reviewer_id": reviewer_id,
                "proposal_sha256": proposal_hash,
                "initial_state_json": json.dumps(
                    case.initial_state, sort_keys=True, ensure_ascii=False
                ),
                "expected_final_state_json": json.dumps(
                    case.expected_final_state, sort_keys=True, ensure_ascii=False
                ),
            }
        )
    return stream.getvalue().encode("utf-8")


def write_state_review_packets(
    cases: list[BenchmarkCase],
    semantic_review: AnnotationReview,
    destination_dir: Path,
) -> StateReviewBundle:
    if not semantic_review.semantic_gate_passed:
        raise HumanGateIncomplete("semantic disagreements require adjudication")
    proposed = [
        _propose_exact_states(
            _case_from_annotation(case, semantic_review.consensus[case.request_id])
        )
        for case in cases
    ]
    proposal_rows = _author_rows(proposed)
    for row in proposal_rows:
        row["evidence_role"] = "deterministic_state_proposal_not_human_oracle"
    content = _jsonl(proposal_rows)
    proposal_hash = _sha256(content)
    proposal_path = destination_dir / f"bench_v2_state_proposals_{proposal_hash}.jsonl"
    _atomic_write_once(proposal_path, content)

    packet_paths: list[Path] = []
    for index in (1, 2):
        packet_path = destination_dir / f"bench_v2_state_reviewer_{index}.csv"
        if not packet_path.exists():
            _atomic_write_once(
                packet_path,
                _state_review_packet(
                    proposed, f"state_reviewer_{index}", proposal_hash
                ),
            )
        packet_paths.append(packet_path)
    return StateReviewBundle(
        proposed_cases=proposed,
        proposals_path=proposal_path,
        review_packets=(packet_paths[0], packet_paths[1]),
        proposals_sha256=proposal_hash,
    )


def _validate_state_packet(path: Path, bundle: StateReviewBundle) -> str:
    expected = {case.request_id: case for case in bundle.proposed_cases}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(expected) or {row["request_id"] for row in rows} != set(
        expected
    ):
        raise HumanGateIncomplete(f"{path.name}: incomplete state review coverage")
    reviewers = {row.get("reviewer_id", "").strip() for row in rows}
    if len(reviewers) != 1 or "" in reviewers:
        raise HumanGateIncomplete(f"{path.name}: one state reviewer is required")
    incomplete = [
        row["request_id"]
        for row in rows
        if row.get("state_review_status", "").strip().upper() != "COMPLETE"
    ]
    if incomplete:
        raise HumanGateIncomplete(
            f"{path.name}: {len(incomplete)} incomplete state review rows"
        )
    for row in rows:
        case = expected[row["request_id"]]
        if row.get("proposal_sha256") != bundle.proposals_sha256:
            raise HumanGateIncomplete(f"{path.name}: state proposal hash changed")
        if row.get("request_text") != case.request_text:
            raise HumanGateIncomplete(f"{path.name}: request text changed")
        expected_initial = json.dumps(
            case.initial_state, sort_keys=True, ensure_ascii=False
        )
        expected_final = json.dumps(
            case.expected_final_state, sort_keys=True, ensure_ascii=False
        )
        if row.get("initial_state_json") != expected_initial:
            raise HumanGateIncomplete(f"{path.name}: initial state changed")
        if row.get("expected_final_state_json") != expected_final:
            raise HumanGateIncomplete(f"{path.name}: final state changed")
        if row.get("state_verdict", "").strip().upper() != "ACCEPT":
            raise HumanGateIncomplete(
                f"{path.name}: state review rejected for {case.request_id}"
            )
    return next(iter(reviewers))


def _validate_candidate_seal(
    cases: list[BenchmarkCase], candidate_manifest_path: Path
) -> dict[str, Any]:
    manifest = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("system_evaluation_allowed") is not False:
        raise HumanGateIncomplete("candidate seal has invalid evaluation status")
    if (
        manifest.get("hashes", {}).get("experiment_code_sha256")
        != _experiment_code_hash()
    ):
        raise HumanGateIncomplete("experiment code changed after candidate seal")
    frozen_protocol = compute_manifest()
    current_protocol = {
        "catalog_sha256": frozen_protocol.catalog_hash,
        "prompt_sha256": frozen_protocol.prompt_hash,
        "provider_config_sha256": frozen_protocol.provider_config_hash,
    }
    for name, current_hash in current_protocol.items():
        if manifest.get("hashes", {}).get(name) != current_hash:
            raise HumanGateIncomplete(f"{name} changed after candidate seal")
    candidate_hash = _sha256(_jsonl(_candidate_rows(cases)))
    if manifest.get("hashes", {}).get("candidates_sha256") != candidate_hash:
        raise HumanGateIncomplete("candidate cases changed after seal")
    return manifest


def finalize_v2_holdout(
    cases: list[BenchmarkCase],
    semantic_review: AnnotationReview,
    states: StateReviewBundle,
    destination_dir: Path,
    *,
    candidate_manifest_path: Path,
) -> FinalizedHoldout:
    """Release gold only after semantic and exact-state human gates pass."""
    if not semantic_review.semantic_gate_passed:
        raise HumanGateIncomplete("semantic human gate has not passed")
    candidate_manifest = _validate_candidate_seal(cases, candidate_manifest_path)
    reviewer_ids = [
        _validate_state_packet(path, states) for path in states.review_packets
    ]
    if reviewer_ids[0] == reviewer_ids[1]:
        raise HumanGateIncomplete("two distinct state reviewers are required")

    content = _jsonl(_gold_rows(states.proposed_cases))
    gold_hash = _sha256(content)
    gold_path = destination_dir / f"bench_v2_gold_{gold_hash}.jsonl"
    _atomic_write_once(gold_path, content)
    manifest = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "status": "prospectively_frozen_unseen_ready_for_one_shot_evaluation",
        "system_evaluation_allowed": True,
        "n_cases": len(states.proposed_cases),
        "decision_kappa": semantic_review.decision_kappa,
        "semantic_agreement_rate": semantic_review.agreement_rate,
        "human_semantic_annotators": 2,
        "human_state_reviewers": 2,
        "hashes": {
            "candidate_manifest_sha256": _sha256(candidate_manifest_path.read_bytes()),
            "candidates_sha256": candidate_manifest["hashes"]["candidates_sha256"],
            "experiment_code_sha256": _experiment_code_hash(),
            "catalog_sha256": candidate_manifest["hashes"]["catalog_sha256"],
            "prompt_sha256": candidate_manifest["hashes"]["prompt_sha256"],
            "provider_config_sha256": candidate_manifest["hashes"][
                "provider_config_sha256"
            ],
            "state_proposals_sha256": states.proposals_sha256,
            "gold_sha256": gold_hash,
            "semantic_packet_1_sha256": _sha256(
                (destination_dir / "bench_v2_annotation_annotator_1.csv").read_bytes()
            ),
            "semantic_packet_2_sha256": _sha256(
                (destination_dir / "bench_v2_annotation_annotator_2.csv").read_bytes()
            ),
            "state_packet_1_sha256": _sha256(states.review_packets[0].read_bytes()),
            "state_packet_2_sha256": _sha256(states.review_packets[1].read_bytes()),
        },
    }
    manifest_content = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    manifest_hash = _sha256(manifest_content)
    manifest_path = destination_dir / f"bench_v2_final_freeze_{manifest_hash}.json"
    _atomic_write_once(manifest_path, manifest_content)
    return FinalizedHoldout(gold_path, manifest_path, gold_hash)


def load_finalized_holdout(gold_path: Path, manifest_path: Path) -> list[BenchmarkCase]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("system_evaluation_allowed") is not True:
        raise HumanGateIncomplete("v2 final manifest does not allow evaluation")
    if (
        manifest.get("hashes", {}).get("experiment_code_sha256")
        != _experiment_code_hash()
    ):
        raise HumanGateIncomplete("experiment code changed after v2 freeze")
    if _sha256(gold_path.read_bytes()) != manifest.get("hashes", {}).get("gold_sha256"):
        raise HumanGateIncomplete("v2 gold hash does not match final manifest")
    cases = []
    for line in gold_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row["split"] = DatasetSplit(row["split"])
        row["expected_decision"] = ExpectedDecision(row["expected_decision"])
        row["risk_class"] = RiskClass(row["risk_class"])
        row["labels"] = {CaseLabel(label) for label in row["labels"]}
        cases.append(BenchmarkCase.model_validate(row))
    if any(
        case.initial_state == {"oracle_pending": True}
        or case.expected_final_state == {"oracle_pending": True}
        for case in cases
    ):
        raise HumanGateIncomplete("v2 gold still contains pending oracle states")
    return cases
