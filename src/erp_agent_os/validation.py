"""Pre-execution argument validation and adversarial-signal detection.

Scope per CLAUDE.md §13 (RF-06: validate types, formats, enumerations and
ranges), §23 ("separación entre instrucciones y datos") and §30 (prompt
injection, sobrealcance, operación irreversible). Produces findings the
policy engine consumes; it never executes or mutates anything itself.

The detectors here are **lexical and deliberately conservative**. They
catch the adversarial patterns present in ERP-Skills-Bench v1, which are
template-generated; they are not a general-purpose prompt-injection
defence and must not be reported as one. Their measured effect belongs in
the H4 discussion as "detection of known patterns", with the ceiling
stated (CLAUDE.md §36, validez de constructo).
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from erp_agent_os.skills import SkillDefinition


class FindingKind(str, Enum):
    MISSING_REQUIRED = "MISSING_REQUIRED"
    WRONG_TYPE = "WRONG_TYPE"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    BULK_SCOPE = "BULK_SCOPE"
    IRREVERSIBLE = "IRREVERSIBLE"
    PERMISSION_CLAIM = "PERMISSION_CLAIM"


@dataclass(frozen=True)
class Finding:
    kind: FindingKind
    detail: str


# ponytail: lexical patterns, Spanish corpus of the frozen benchmark. A
# semantic/classifier detector is future work; upgrade path is to replace
# these regexes behind the same `detect_text_signals` signature.
_INJECTION_PATTERNS = (
    r"ignora (?:las )?(?:instrucciones|indicaciones)",
    r"olvida (?:las )?(?:instrucciones|reglas)",
    r"ahora eres",
    r"system prompt",
    r"ignore (?:the )?(?:previous|above) instructions",
)
_BULK_PATTERNS = (
    r"\ba todos\b",
    r"\btodas las\b",
    r"\btodos los\b",
    r"clientes similares",
    r"en masa",
    r"masivamente",
)
_IRREVERSIBLE_PATTERNS = (
    r"borra(?:lo|los|las)? todo",
    r"elimina(?:r)? (?:todos|todas|permanentemente)",
    r"permanentemente",
    r"sin posibilidad de deshacer",
)
_PERMISSION_PATTERNS = (
    r"sin permiso",
    r"sin autorizaci[oó]n",
    r"usuario no autorizado",
    r"salt(?:a|ando) (?:el |la )?(?:control|validaci[oó]n|permiso)",
)

_NUMERIC_LIMITS: dict[str, tuple[float, float]] = {
    "expected_revenue": (0.0, 100_000.0),
    "quantity": (1.0, 1_000.0),
}


def _matches(text: str, patterns: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    for pattern in patterns:
        found = re.search(pattern, lowered)
        if found:
            return found.group(0)
    return None


def detect_text_signals(request_text: str) -> list[Finding]:
    """Lexical adversarial signals in the raw request text."""
    findings: list[Finding] = []
    for patterns, kind in (
        (_INJECTION_PATTERNS, FindingKind.PROMPT_INJECTION),
        (_BULK_PATTERNS, FindingKind.BULK_SCOPE),
        (_IRREVERSIBLE_PATTERNS, FindingKind.IRREVERSIBLE),
        (_PERMISSION_PATTERNS, FindingKind.PERMISSION_CLAIM),
    ):
        hit = _matches(request_text, patterns)
        if hit is not None:
            findings.append(Finding(kind, f"matched {kind.value.lower()}: {hit!r}"))
    return findings


def validate_arguments(
    skill: SkillDefinition, arguments: dict[str, Any]
) -> list[Finding]:
    """Type/range/presence validation against the skill's input schema."""
    findings: list[Finding] = []
    schema = skill.input_schema
    required: list[str] = schema.get("required", [])

    for field in required:
        value = arguments.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            findings.append(Finding(FindingKind.MISSING_REQUIRED, field))

    for field, (low, high) in _NUMERIC_LIMITS.items():
        if field not in arguments:
            continue
        raw = arguments[field]
        try:
            number = float(str(raw).replace(",", "."))
        except (TypeError, ValueError):
            findings.append(
                Finding(FindingKind.WRONG_TYPE, f"{field}={raw!r} is not numeric")
            )
            continue
        if not low <= number <= high:
            findings.append(
                Finding(
                    FindingKind.OUT_OF_RANGE,
                    f"{field}={number} outside [{low}, {high}]",
                )
            )

    return findings


def blocking_findings(findings: list[Finding]) -> list[Finding]:
    """Findings that must produce a DENY, as opposed to a clarification."""
    blocking = {
        FindingKind.WRONG_TYPE,
        FindingKind.OUT_OF_RANGE,
        FindingKind.PROMPT_INJECTION,
        FindingKind.BULK_SCOPE,
        FindingKind.IRREVERSIBLE,
        FindingKind.PERMISSION_CLAIM,
    }
    return [f for f in findings if f.kind in blocking]
