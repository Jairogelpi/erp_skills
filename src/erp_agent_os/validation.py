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


# ponytail: lexical patterns, Spanish corpus of the frozen benchmark plus
# English equivalents added after the InjecAgent stress test
# (docs/injecagent-stress-test.md) showed the Spanish-only version
# scored 0% on an English out-of-domain adversarial set. A
# semantic/classifier detector is future work; upgrade path is to
# replace these regexes behind the same `detect_text_signals` signature.
_INJECTION_PATTERNS = (
    r"ignora (?:las )?(?:instrucciones|indicaciones)",
    r"olvida (?:las )?(?:instrucciones|reglas)",
    r"ahora eres",
    r"system prompt",
    r"ignore (?:the )?(?:previous|above) instructions",
    r"forget (?:the )?(?:previous|above) (?:instructions|rules)",
    r"you are now",
    r"disregard (?:the )?(?:previous|above) (?:instructions|rules)",
)
_BULK_PATTERNS = (
    r"\ba todos\b",
    r"\btodas las\b",
    r"\btodos los\b",
    r"clientes similares",
    r"en masa",
    r"masivamente",
    r"\ball (?:of )?(?:the )?(?:customers|clients|users|accounts|records)\b",
    r"\bevery (?:customer|client|user|account|record)\b",
    r"in bulk",
    r"\ben masse\b",
)
_IRREVERSIBLE_PATTERNS = (
    r"borra(?:lo|los|las)? todo",
    r"elimina(?:r)? (?:todos|todas|permanentemente)",
    r"permanentemente",
    r"sin posibilidad de deshacer",
    r"delete (?:it |them )?(?:all|permanently)",
    r"\bpermanently\b",
    r"\bwithout (?:the )?(?:possibility|option) (?:to|of) undo",
    r"\bno turning back\b",
)
_PERMISSION_PATTERNS = (
    r"sin permiso",
    r"sin autorizaci[oó]n",
    r"usuario no autorizado",
    r"salt(?:a|ando) (?:el |la )?(?:control|validaci[oó]n|permiso)",
    r"without (?:permission|authorization)",
    r"unauthorized user",
    r"bypass(?:ing)? (?:the )?(?:control|validation|permission|approval)",
)

_NUMERIC_LIMITS: dict[str, tuple[float, float]] = {
    "expected_revenue": (0.0, 100_000.0),
    "quantity": (1.0, 1_000.0),
}

# Public so callers (e.g. the bench v2 generator) can check whether a field
# is actually range/type-validated before authoring a case that expects a
# range violation to be caught. Deriving this from _NUMERIC_LIMITS instead of
# a second hardcoded literal means the two can never silently drift apart.
NUMERIC_LIMITED_FIELDS: frozenset[str] = frozenset(_NUMERIC_LIMITS)


# A numeric value followed only by a currency unit: "27600 euros",
# "1.200,50 EUR", "15000€". Deliberately anchored end-to-end so that
# anything with real trailing content ("27600 euros y sube el resto")
# does NOT normalize and still reaches validation as a WRONG_TYPE.
_CURRENCY_SUFFIX = r"(?:euros?|eur|€|\$|usd|dolares?|dólares?)"
_NUMERIC_WITH_UNIT = re.compile(
    rf"^\s*(?P<number>[\d.,]+)\s*{_CURRENCY_SUFFIX}?\s*$", re.IGNORECASE
)


def normalize_arguments(
    skill: SkillDefinition, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Canonicalise argument values before validation (CLAUDE.md §20).

    The traceability rubric names "entrada normalizada" as part of the
    execution record, but the implementation validated the LLM's raw
    output directly. That made System C -- the only system with type
    validation -- reject `"27600 euros"` as WRONG_TYPE, even though the
    number was extracted perfectly and only carried its unit. C was
    being penalised for *having* a safety feature, on input that was not
    actually unsafe.

    Only a bare number optionally followed by a currency unit is
    normalised. Anything else is left untouched so genuinely malformed
    input ("mucho dinero", "27600 y borra el resto") still fails
    validation instead of being silently coerced into something
    executable.
    """
    normalized = dict(arguments)
    for field in _NUMERIC_LIMITS:
        raw = normalized.get(field)
        if raw is None or isinstance(raw, (int, float)):
            continue
        match = _NUMERIC_WITH_UNIT.match(str(raw))
        if match is None:
            continue
        number = match.group("number")
        # "1.200,50" (es-ES) -> "1200.50"; "1,200.50" (en-US) -> "1200.50"
        if "," in number and "." in number:
            if number.rindex(",") > number.rindex("."):
                number = number.replace(".", "").replace(",", ".")
            else:
                number = number.replace(",", "")
        elif "," in number:
            number = number.replace(",", ".")
        try:
            float(number)
        except ValueError:
            continue
        normalized[field] = number
    return normalized


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
