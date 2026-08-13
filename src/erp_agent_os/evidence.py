"""Authoritative protocol status and reporting guards for result artefacts."""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class EvidenceStatus(StrEnum):
    """Closed protocol-status vocabulary used by the evidence registry."""

    PENDING = "pending"
    CONFIRMATORY = "confirmatory"
    EXPLORATORY = "exploratory"
    SENSITIVITY = "sensitivity"
    DEMONSTRATION = "demonstration"


def _validate_repository_path(value: str) -> str:
    candidate = Path(value)
    if (
        not value
        or candidate.is_absolute()
        or "\\" in value
        or value.startswith("./")
        or ".." in candidate.parts
        or candidate.as_posix() != value
    ):
        raise ValueError(
            f"path must be an exact repository-relative POSIX path: {value}"
        )
    return value


def _sha256_file(path: Path) -> str:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read confirmation evidence {path}: {exc}") from exc
    return hashlib.sha256(content).hexdigest()


class EvidenceEntry(BaseModel):
    """Immutable provenance and claim boundary for one result artefact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    date: datetime.date | None = None
    source_commit: str | None = None
    protocol_status: EvidenceStatus
    reason: str = Field(min_length=1)
    implementation_observed: bool
    test_data_observed: bool
    permitted_claims: tuple[str, ...] = Field(min_length=1)
    prohibited_claims: tuple[str, ...] = Field(min_length=1)
    freeze_manifest_path: str | None = None
    result_validation_path: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _validate_repository_path(value)

    @field_validator("freeze_manifest_path", "result_validation_path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        return None if value is None else _validate_repository_path(value)

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[0-9a-f]{7,40}", value):
            raise ValueError("source_commit must be a 7-40 character Git SHA")
        return value

    @model_validator(mode="after")
    def validate_confirmation_evidence(self) -> Self:
        if self.protocol_status is not EvidenceStatus.CONFIRMATORY:
            return self
        missing = [
            name
            for name in ("freeze_manifest_path", "result_validation_path")
            if getattr(self, name) is None
        ]
        if missing:
            raise ValueError("confirmatory evidence requires " + " and ".join(missing))
        return self


_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ConfirmatoryFreezeEvidence(BaseModel):
    """Core proof fields emitted by the prospective v2 freeze verifier."""

    model_config = ConfigDict(frozen=True, extra="allow")

    schema_version: Literal["1.0"]
    status: Literal["verified"]
    protocol_id: Literal["erp-skills-bench-v2"]
    manifest_hash: str = Field(pattern=_SHA256_PATTERN)
    run_config_hash: str = Field(pattern=_SHA256_PATTERN)
    expected_observations: Literal[1080]


class ConfirmatoryResultValidation(BaseModel):
    """Core proof fields emitted by the prospective v2 result validator."""

    model_config = ConfigDict(frozen=True, extra="allow")

    schema_version: Literal["1.0"]
    artifact_path: str
    artifact_sha256: str = Field(pattern=_SHA256_PATTERN)
    freeze_manifest_path: str
    freeze_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    manifest_hash: str = Field(pattern=_SHA256_PATTERN)
    run_config_hash: str = Field(pattern=_SHA256_PATTERN)
    validation_status: Literal["passed"]
    completed_observations: Literal[1080]
    expected_observations: Literal[1080]
    primary_endpoint_complete: Literal[True]

    _paths_are_repository_relative = field_validator(
        "artifact_path", "freeze_manifest_path"
    )(_validate_repository_path)


class EvidenceRegistry(BaseModel):
    """Immutable, exact-path index that supersedes legacy result metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str
    legacy_cutoff_commit: str
    retained_annotation_audit_outputs: tuple[str, ...] = ()
    non_reportable_allowlist: tuple[str, ...] = ()
    entries: tuple[EvidenceEntry, ...]

    _retained_paths_are_repository_relative = field_validator(
        "retained_annotation_audit_outputs", "non_reportable_allowlist"
    )(lambda values: tuple(_validate_repository_path(value) for value in values))

    @field_validator("legacy_cutoff_commit")
    @classmethod
    def validate_legacy_cutoff(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{7,40}", value):
            raise ValueError("legacy_cutoff_commit must be a 7-40 character Git SHA")
        return value

    @model_validator(mode="after")
    def reject_duplicate_paths(self) -> Self:
        paths = [entry.path for entry in self.entries]
        duplicates = sorted(path for path in set(paths) if paths.count(path) > 1)
        if duplicates:
            raise ValueError(f"duplicate evidence path(s): {', '.join(duplicates)}")
        return self

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load and validate a registry from JSON."""

        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(payload)

    def entry_for(self, path: str) -> EvidenceEntry:
        """Return the entry for an exact repository-relative path."""

        for entry in self.entries:
            if entry.path == path:
                return entry
        raise KeyError(path)

    def status_for(self, path: str) -> EvidenceStatus:
        """Return authoritative status without consulting the artefact itself."""

        return self.entry_for(path).protocol_status

    def require_confirmatory(self, path: str, *, root: Path) -> EvidenceEntry:
        """Require cross-bound proof of a complete, prospectively frozen run."""

        entry = self.entry_for(path)
        if entry.protocol_status is not EvidenceStatus.CONFIRMATORY:
            raise ValueError(
                f"{path} is {entry.protocol_status.value}, not confirmatory"
            )
        freeze_relative = entry.freeze_manifest_path
        validation_relative = entry.result_validation_path
        evidence_paths = (entry.path, freeze_relative, validation_relative)
        missing: list[str] = []
        for evidence_path in evidence_paths:
            if evidence_path is None:
                missing.append("undeclared confirmation evidence")
            elif not (root / evidence_path).is_file():
                missing.append(evidence_path)
        if missing:
            raise ValueError(
                f"{path} lacks confirmation evidence: {', '.join(missing)}"
            )

        assert freeze_relative is not None
        assert validation_relative is not None
        artifact_path = root / entry.path
        freeze_path = root / freeze_relative
        validation_path = root / validation_relative

        try:
            freeze = ConfirmatoryFreezeEvidence.model_validate_json(
                freeze_path.read_bytes()
            )
        except (OSError, ValidationError) as exc:
            raise ValueError(
                f"{path} has invalid freeze evidence {freeze_relative}: {exc}"
            ) from exc
        try:
            validation = ConfirmatoryResultValidation.model_validate_json(
                validation_path.read_bytes()
            )
        except (OSError, ValidationError) as exc:
            raise ValueError(
                f"{path} has invalid result validation evidence "
                f"{validation_relative}: {exc}"
            ) from exc

        if validation.artifact_path != entry.path:
            raise ValueError(
                f"{path} artifact_path mismatch: {validation.artifact_path}"
            )
        if validation.freeze_manifest_path != freeze_relative:
            raise ValueError(
                f"{path} freeze_manifest_path mismatch: "
                f"{validation.freeze_manifest_path}"
            )
        if validation.artifact_sha256 != _sha256_file(artifact_path):
            raise ValueError(f"{path} artifact_sha256 mismatch")
        if validation.freeze_manifest_sha256 != _sha256_file(freeze_path):
            raise ValueError(f"{path} freeze_manifest_sha256 mismatch")
        if validation.manifest_hash != freeze.manifest_hash:
            raise ValueError(f"{path} manifest_hash mismatch")
        if validation.run_config_hash != freeze.run_config_hash:
            raise ValueError(f"{path} run_config_hash mismatch")
        if validation.expected_observations != freeze.expected_observations:
            raise ValueError(f"{path} expected_observations mismatch")
        return entry

    def unregistered_reportable_paths(self, root: Path) -> tuple[str, ...]:
        """List reportable outputs not governed or explicitly marked as fixtures."""

        data_dir = root / "data"
        paths = {
            path.relative_to(root).as_posix()
            for path in data_dir.glob("*results*.json")
            if path.is_file()
        }
        paths.update(
            path
            for path in self.retained_annotation_audit_outputs
            if (root / path).is_file()
        )
        registered = {entry.path for entry in self.entries}
        allowed = set(self.non_reportable_allowlist)
        return tuple(sorted(paths - registered - allowed))


@dataclass(frozen=True, slots=True)
class ClaimViolation:
    """One reporting statement that crosses the approved evidence boundary."""

    document: Path
    line: int
    message: str
    artifact: str | None = None

    def __str__(self) -> str:
        artifact = f" [{self.artifact}]" if self.artifact else ""
        return f"{self.document}:{self.line}:{artifact} {self.message}"


_CONFIRMATORY_WORDING = re.compile(
    r"confirmator(?:y|io|ia|ios|ias)|is_confirmatory_run", re.IGNORECASE
)
_CONFIRMATORY_DISCUSSION = re.compile(
    r"(?:classified|clasificad\w*)\W+(?:as|como)\W+explorator",
    re.IGNORECASE,
)
_GENERAL_SAFETY = re.compile(
    r"\b(?:inmunidad|inmune|immunity|immune)\b|"
    r"\bseguridad\s+(?:total|general|absoluta|garantizada)\b|"
    r"\b(?:general safety|completely safe|guarantees? safety)\b|"
    r"\b(?:resiste cualquier ataque|prompt[- ]injection[- ]proof)\b|"
    r"\b(?:es|sea)\s+segur[oa]\s+(?:frente\s+a|ante|contra)\s+"
    r"(?:cualquier|todo)\b|"
    r"\b(?:is|are)\s+safe\s+(?:against|from)\s+(?:any|all)\b",
    re.IGNORECASE,
)
_DIRECT_NEGATION_SUFFIX = re.compile(
    r"(?:\b(?:no|not)(?:\s+\w+){0,3}|\bnon[-])\s*$",
    re.IGNORECASE,
)
_SAFETY_DENIAL = re.compile(
    r"\b(?:no\s+(?:afirmamos|sostenemos|decimos)\s+que|"
    r"no\s+(?:prueba|demuestra|evidencia|garantiza)|"
    r"we\s+do\s+not\s+(?:claim|state)(?:\s+that)?|"
    r"does\s+not\s+(?:prove|demonstrate|guarantee))\b",
    re.IGNORECASE,
)
_PROHIBITION_HEADING = re.compile(
    r"\b(?:lo que no se debe decir|errores que arruinan)\b",
    re.IGNORECASE,
)
_ZERO_OF_1530 = re.compile(r"\b0\s*/\s*1[.,]?530\b")
_HUMAN_KAPPA = re.compile(
    r"\b(?:kappa\s+humano|human(?:\s+cohen(?:'s)?)?\s+kappa|"
    r"kappa(?:\s+de\s+cohen)?\s+entre\s+anotadores|"
    r"(?:cohen['’]s\s+)?kappa\s+(?:between|among)\s+(?:human\s+)?annotators|"
    r"kappa[^\n.]{0,60}interanotador|inter[- ]annotator[^\n.]{0,60}kappa)\b",
    re.IGNORECASE,
)
_KAPPA_UNAVAILABLE = re.compile(
    r"\b(?:pending|pendiente|unavailable|no disponible|unmet|no hay|"
    r"sigue sin|remains? unavailable|waived)\b|"
    r"\bno se (?:calcul[oó]|midi[oó]|estim[oó]|report[oó])\b|"
    r"\bnot (?:calculated|measured|estimated|reported)\b|"
    r"\bsin (?:calcular|medir|estimar|reportar)\b",
    re.IGNORECASE,
)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _paragraph_at(text: str, offset: int) -> str:
    previous_break = text.rfind("\n\n", 0, offset)
    start = 0 if previous_break == -1 else previous_break + 2
    next_break = text.find("\n\n", offset)
    end = len(text) if next_break == -1 else next_break
    return text[start:end]


def _sentence_at(text: str, start_offset: int, end_offset: int) -> str:
    boundaries = "\n.;!?"
    start = max(text.rfind(marker, 0, start_offset) for marker in boundaries)
    ends = [
        position
        for marker in boundaries
        if (position := text.find(marker, end_offset)) != -1
    ]
    end = min(ends) if ends else len(text)
    return text[start + 1 : end]


def _clause_prefix(text: str, offset: int) -> str:
    sentence = _sentence_at(text, offset, offset)
    sentence_start = text.rfind(sentence, 0, offset + len(sentence))
    relative_offset = offset - sentence_start
    prefix = sentence[:relative_offset]
    separators = list(
        re.finditer(
            r"(?:,|\bpero\b|\bsin embargo\b|\bbut\b|\bhowever\b|\by\b|\band\b)",
            prefix,
            re.IGNORECASE,
        )
    )
    return prefix[separators[-1].end() :] if separators else prefix


def _confirmatory_claim_is_negated(text: str, match: re.Match[str]) -> bool:
    prefix = _clause_prefix(text, match.start())
    sentence = _sentence_at(text, match.start(), match.end())
    return bool(
        _DIRECT_NEGATION_SUFFIX.search(prefix)
        or _CONFIRMATORY_DISCUSSION.search(sentence)
    )


def _safety_claim_is_negated(text: str, match: re.Match[str]) -> bool:
    prefix = _clause_prefix(text, match.start())
    return bool(_DIRECT_NEGATION_SUFFIX.search(prefix) or _SAFETY_DENIAL.search(prefix))


def _heading_at(text: str, offset: int) -> str:
    start = text.rfind("\n#", 0, offset)
    start = 0 if start == -1 else start + 1
    end = text.find("\n", start)
    return text[start : len(text) if end == -1 else end]


def second_annotation_available(path: Path) -> bool:
    """Return true only when every retained review row has a second decision."""

    if not path.is_file():
        return False
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return bool(rows) and all(
        (row.get("annotator2_decision") or "").strip() for row in rows
    )


def audit_document_claims(
    registry: EvidenceRegistry,
    document: Path,
    *,
    annotation_sheet: Path,
) -> tuple[ClaimViolation, ...]:
    """Validate only concrete, evidence-linked claims in one reporting document."""

    text = document.read_text(encoding="utf-8")
    violations: list[ClaimViolation] = []

    for entry in registry.entries:
        if entry.protocol_status is EvidenceStatus.CONFIRMATORY:
            continue
        for match in re.finditer(re.escape(entry.path), text):
            block = _paragraph_at(text, match.start())
            prohibited_claim = next(
                (
                    claim
                    for claim in _CONFIRMATORY_WORDING.finditer(block)
                    if not _confirmatory_claim_is_negated(block, claim)
                ),
                None,
            )
            if prohibited_claim is not None:
                violations.append(
                    ClaimViolation(
                        document=document,
                        line=_line_number(text, match.start()),
                        artifact=entry.path,
                        message=(
                            "confirmatory wording is not permitted for "
                            f"{entry.protocol_status.value} evidence"
                        ),
                    )
                )
                break

    for match in _GENERAL_SAFETY.finditer(text):
        in_prohibition_section = _PROHIBITION_HEADING.search(
            _heading_at(text, match.start())
        )
        if not in_prohibition_section and not _safety_claim_is_negated(text, match):
            violations.append(
                ClaimViolation(
                    document=document,
                    line=_line_number(text, match.start()),
                    message="general safety or immunity claim is prohibited",
                )
            )

    for match in _ZERO_OF_1530.finditer(text):
        context = text[max(0, match.start() - 350) : match.end() + 500]
        scoped = (
            re.search(r"explorator", context, re.IGNORECASE)
            and re.search(r"(?:confinamiento|confinement)", context, re.IGNORECASE)
            and re.search(
                r"(?:tres\s+canales|three[- ]channel)", context, re.IGNORECASE
            )
        )
        if not scoped:
            violations.append(
                ClaimViolation(
                    document=document,
                    line=_line_number(text, match.start()),
                    artifact="data/injection_resistance_results.json",
                    message=(
                        "0/1530 may only be reported as a scoped exploratory "
                        "three-channel confinement result"
                    ),
                )
            )

    if not second_annotation_available(annotation_sheet):
        for match in _HUMAN_KAPPA.finditer(text):
            sentence = _sentence_at(text, match.start(), match.end())
            sentence_start = text.rfind(sentence, 0, match.start() + len(sentence))
            relative_start = match.start() - sentence_start
            trailing_claim = sentence[relative_start:]
            if not _KAPPA_UNAVAILABLE.search(trailing_claim):
                violations.append(
                    ClaimViolation(
                        document=document,
                        line=_line_number(text, match.start()),
                        artifact="data/annotation_review_sheet.csv",
                        message=(
                            "human kappa cannot be claimed while annotator2_decision "
                            "is unavailable"
                        ),
                    )
                )

    return tuple(violations)


def reporting_document_paths(root: Path) -> tuple[Path, ...]:
    """Return competition-facing Markdown documents in stable order."""

    candidates = [root / "README.md", *sorted((root / "docs").glob("*.md"))]
    return tuple(path for path in candidates if path.is_file())


def audit_reporting_documents(
    registry: EvidenceRegistry,
    documents: tuple[Path, ...],
    *,
    annotation_sheet: Path,
) -> tuple[ClaimViolation, ...]:
    """Audit a set of reporting documents against the registry."""

    return tuple(
        violation
        for document in documents
        for violation in audit_document_claims(
            registry, document, annotation_sheet=annotation_sheet
        )
    )
