"""Blinded machine consistency audit for benchmark annotations.

This module is deliberately separate from human inter-annotator agreement.  A
reviewer sees only request text and neutral label definitions; canonical labels
are joined after every review call solely to compute diagnostic disagreement.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROMPT_VERSION = "ai-annotation-audit-v1"
EVIDENCE_STATUS = "ai_consistency_audit"
ALLOWED_LABELS = (
    "ALLOW",
    "DENY",
    "REQUIRE_APPROVAL",
    "SIMULATE",
    "CLARIFY",
    "ABSTAIN",
)


class AnnotationAuditError(RuntimeError):
    """Sanitized failure which must not modify canonical data or prior output."""


class AuditReviewer(Protocol):
    """Provider-neutral structured reviewer contract."""

    def review(
        self, *, prompt: str, response_schema: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...


class BlindedAuditItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1)
    request_text: str = Field(min_length=1)


class MachineReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("label")
    @classmethod
    def valid_label(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALLOWED_LABELS:
            raise ValueError("unsupported audit label")
        return normalized


class AuditProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    model: str
    temperature: float
    prompt_version: str
    prompt_hash: str


class AuditDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    machine_label: str
    confidence: float
    reason: str
    canonical_label: str
    agrees: bool


class AnnotationAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    evidence_status: str = EVIDENCE_STATUS
    diagnostic_only: bool = True
    manual_adjudication_required: bool = True
    human_inter_annotator_agreement: bool = False
    provenance: AuditProvenance
    n: int
    agreement_rate: float
    disagreement_request_ids: tuple[str, ...]
    decisions: tuple[AuditDecision, ...]


def response_schema() -> dict[str, Any]:
    return MachineReview.model_json_schema()


def build_blinded_prompt(item: BlindedAuditItem) -> str:
    labels = ", ".join(ALLOWED_LABELS)
    return (
        f"Protocol {PROMPT_VERSION}. Review one Spanish ERP request independently.\n"
        f"Allowed decisions: {labels}.\n"
        "Return only the structured decision, confidence, and a short reason.\n"
        f"request_id: {item.request_id}\n"
        f"request_text: {item.request_text}"
    )


def prompt_hash() -> str:
    template = build_blinded_prompt(
        BlindedAuditItem(request_id="{request_id}", request_text="{request_text}")
    )
    return hashlib.sha256(template.encode("utf-8")).hexdigest()


def load_review_rows(path: Path) -> tuple[list[BlindedAuditItem], dict[str, str]]:
    """Load only allowlisted prompt fields; keep canonical labels in a local join."""
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise AnnotationAuditError("annotation input could not be read") from exc

    items: list[BlindedAuditItem] = []
    canonical: dict[str, str] = {}
    for row in rows:
        request_id = (row.get("request_id") or "").strip()
        if not request_id or request_id in canonical:
            raise AnnotationAuditError(
                "annotation input has missing or duplicate request ids"
            )
        try:
            item = BlindedAuditItem(
                request_id=request_id,
                request_text=(row.get("request_text") or "").strip(),
            )
        except Exception as exc:
            raise AnnotationAuditError("annotation input is invalid") from exc
        label = (row.get("annotator1_decision") or "").strip().upper()
        if label not in ALLOWED_LABELS:
            raise AnnotationAuditError("canonical annotation label is invalid")
        items.append(item)
        canonical[request_id] = label
    if not items:
        raise AnnotationAuditError("annotation input is empty")
    return items, canonical


def run_blinded_audit(
    *,
    items: Sequence[BlindedAuditItem],
    canonical_labels: Mapping[str, str],
    reviewer: AuditReviewer,
    provider: str,
    model: str,
    temperature: float = 0.0,
) -> AnnotationAuditReport:
    if len({item.request_id for item in items}) != len(items):
        raise AnnotationAuditError("audit request ids must be unique")
    reviewed: list[tuple[BlindedAuditItem, MachineReview]] = []
    schema = response_schema()
    for item in items:
        try:
            raw = reviewer.review(
                prompt=build_blinded_prompt(item), response_schema=schema
            )
            reviewed.append((item, MachineReview.model_validate(raw)))
        except Exception as exc:
            raise AnnotationAuditError(
                "machine review failed; no audit was written"
            ) from exc

    # Canonical labels are accessed only after all blinded calls complete.
    decisions: list[AuditDecision] = []
    for item, machine in reviewed:
        canonical = canonical_labels.get(item.request_id, "")
        if canonical not in ALLOWED_LABELS:
            raise AnnotationAuditError("canonical label join is incomplete")
        decisions.append(
            AuditDecision(
                request_id=item.request_id,
                machine_label=machine.label,
                confidence=machine.confidence,
                reason=machine.reason,
                canonical_label=canonical,
                agrees=machine.label == canonical,
            )
        )
    disagreements = tuple(d.request_id for d in decisions if not d.agrees)
    return AnnotationAuditReport(
        provenance=AuditProvenance(
            provider=provider,
            model=model,
            temperature=temperature,
            prompt_version=PROMPT_VERSION,
            prompt_hash=prompt_hash(),
        ),
        n=len(decisions),
        agreement_rate=(len(decisions) - len(disagreements)) / len(decisions),
        disagreement_request_ids=disagreements,
        decisions=tuple(decisions),
    )


def write_report_atomic(report: AnnotationAuditReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump_json(indent=2) + "\n"
    temp_path: Path | None = None
    try:
        fd, raw_path = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
        temp_path = Path(raw_path)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(output)
    except OSError as exc:
        raise AnnotationAuditError("audit output could not be written") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


class RecordedResponseReviewer:
    """Offline reviewer used by the CLI; never performs network I/O."""

    def __init__(self, responses: Mapping[str, Mapping[str, Any]]) -> None:
        self._responses = responses

    def review(
        self, *, prompt: str, response_schema: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        del response_schema
        marker = "request_id: "
        request_id = prompt.split(marker, 1)[1].splitlines()[0]
        if request_id not in self._responses:
            raise AnnotationAuditError("recorded response is missing")
        return self._responses[request_id]


def load_recorded_responses(path: Path) -> dict[str, Mapping[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError
        return {
            str(key): value for key, value in raw.items() if isinstance(value, dict)
        }
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise AnnotationAuditError("recorded responses could not be read") from exc
