"""Machine-enforced evidence states and claim language for v2.1
(Task 11).

docs/tfm-closure-no-human-v2.1.md section 13: a hypothesis may only be
published as `confirmatory_supported` if ALL SIX named conditions hold
-- the campaign is RUN_COMPLETED, hashes are valid, raw observations
are complete, the registered analysis actually ran, the directional
criterion and its CI were met, and no protocol violation is open.

`determine_evidence_state` has exactly one return statement that can
produce `CONFIRMATORY_SUPPORTED`, reached only after five other
conditions have each already been checked and found NOT to disqualify
it -- there is no code path, including missing or raw-invalid data,
that reaches "supported" by omission. Missing data (zero raw rows, or
the analysis never running) becomes `NOT_MEASURED`; raw-invalid data
(a hash mismatch) becomes `PROTOCOL_VIOLATION`; the two are kept
separate because they are different failure modes a report reader
needs to tell apart (this project generated nothing vs. this project
generated something it can no longer trust).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from erp_agent_os.statistics_v2_1 import AnalysisResult


class ClaimsV21Error(ValueError):
    pass


class EvidenceState(str, Enum):
    """Section 13's seven registry states, plus PROTOCOL_VIOLATION --
    Task 11 step 1 explicitly names "not_measured or protocol_violation"
    as the two outcomes missing/raw-invalid data must produce, and
    PROTOCOL_VIOLATION is not one of section 13's original seven, so it
    is added here as an explicit eighth rather than folded silently into
    NOT_MEASURED (which would erase the distinction step 1 requires)."""

    OBSERVED_DESCRIPTIVE = "observed_descriptive"
    CONFIRMATORY_SUPPORTED = "confirmatory_supported"
    CONFIRMATORY_NOT_SUPPORTED = "confirmatory_not_supported"
    CONFIRMATORY_INCONCLUSIVE = "confirmatory_inconclusive"
    EXPLORATORY = "exploratory"
    SCENARIO_ONLY = "scenario_only"
    NOT_MEASURED = "not_measured"
    PROTOCOL_VIOLATION = "protocol_violation"


# ---------------------------------------------------------- verdict mapping

_POSITIVE_VERDICTS: frozenset[str] = frozenset(
    {
        "non_inferior",
        "superior",
        "fewer_tokens",
        "supported",
        "adequate",
        "abstention_reduces_false_reuse",
    }
)
_NEGATIVE_VERDICTS: frozenset[str] = frozenset(
    {
        "not_non_inferior",
        "not_superior",
        "not_fewer_tokens",
        "not_supported",
        "not_adequate",
    }
)
_INCONCLUSIVE_VERDICTS: frozenset[str] = frozenset({"inconclusive_ceiling"})


def verdict_indicates_criterion_met(verdict: str) -> bool | None:
    """True/False/None (inconclusive) for every verdict string
    erp_agent_os.statistics_v2_1's analyze_* functions actually produce.
    Raises on anything else -- an unrecognized verdict must never be
    silently treated as either outcome."""
    if verdict in _POSITIVE_VERDICTS:
        return True
    if verdict in _NEGATIVE_VERDICTS:
        return False
    if verdict in _INCONCLUSIVE_VERDICTS:
        return None
    raise ClaimsV21Error(f"unrecognized AnalysisResult verdict: {verdict!r}")


# -------------------------------------------------------------- the gate


@dataclass(frozen=True)
class ConfirmatoryGateInputs:
    """The six conditions section 13 lists, named to match its own
    numbering exactly, so a reviewer can check this dataclass field by
    field against the spec text."""

    run_completed: bool  # 1. la campaña está RUN_COMPLETED
    hashes_valid: bool  # 2. los hashes son válidos
    observations_complete: bool  # 3. las observaciones crudas están completas
    registered_analysis_ran: bool  # 4. se ejecutó el análisis registrado
    no_open_protocol_violation: bool  # 6. no existe una violación de protocolo abierta


def determine_evidence_state(
    gate: ConfirmatoryGateInputs, *, criterion_met: bool | None
) -> EvidenceState:
    """`criterion_met` is condition 5 ("se cumplió el criterio direccional
    y su IC"), passed separately because it is hypothesis-specific
    (derived from a real AnalysisResult.verdict, never invented here) --
    everything else in `gate` is campaign-level and shared by every
    hypothesis in the same run."""
    if not gate.no_open_protocol_violation:
        return EvidenceState.PROTOCOL_VIOLATION
    if not gate.hashes_valid:
        return EvidenceState.PROTOCOL_VIOLATION
    if not gate.run_completed:
        return EvidenceState.NOT_MEASURED
    if not gate.registered_analysis_ran:
        return EvidenceState.NOT_MEASURED
    if not gate.observations_complete:
        return EvidenceState.CONFIRMATORY_INCONCLUSIVE
    if criterion_met is None:
        return EvidenceState.CONFIRMATORY_INCONCLUSIVE
    if criterion_met is False:
        return EvidenceState.CONFIRMATORY_NOT_SUPPORTED
    return EvidenceState.CONFIRMATORY_SUPPORTED


def evidence_state_for_result(
    result: AnalysisResult, gate: ConfirmatoryGateInputs
) -> EvidenceState:
    """Convenience wrapper: derives condition 5 from a real
    AnalysisResult's own verdict instead of asking every caller to
    re-derive `criterion_met` by hand."""
    criterion_met = verdict_indicates_criterion_met(result.verdict)
    return determine_evidence_state(gate, criterion_met=criterion_met)


# ---------------------------------------------------------- claim language

# Section 13: "El validador impedirá frases como 'demostrado',
# 'confirmado' o 'superior' si el estado machine-readable no las
# habilita." These three are conditionally forbidden -- allowed only
# when the hypothesis they describe is genuinely CONFIRMATORY_SUPPORTED.
_CONDITIONALLY_FORBIDDEN: tuple[str, ...] = ("demostrado", "confirmado", "superior")

# Section 8/§1's own amendment: never authorized by ANY evidence state.
# H8 is a sensitivity grid, never an observed-savings claim, and v2.1
# never uses human annotation at all -- no evidence state can unlock
# either phrase.
_UNCONDITIONALLY_FORBIDDEN: tuple[str, ...] = ("ahorro real", "acuerdo humano")


def _find_phrase(text: str, phrase: str) -> bool:
    pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def find_forbidden_phrases(text: str, *, evidence_state: EvidenceState) -> list[str]:
    """Returns every forbidden phrase actually present in `text` --
    empty means the text is authorized for `evidence_state`."""
    found = [
        phrase for phrase in _UNCONDITIONALLY_FORBIDDEN if _find_phrase(text, phrase)
    ]
    if evidence_state is not EvidenceState.CONFIRMATORY_SUPPORTED:
        found.extend(
            phrase for phrase in _CONDITIONALLY_FORBIDDEN if _find_phrase(text, phrase)
        )
    return found


def assert_claim_text_is_authorized(
    text: str, *, evidence_state: EvidenceState
) -> None:
    violations = find_forbidden_phrases(text, evidence_state=evidence_state)
    if violations:
        raise ClaimsV21Error(
            f"claim text uses phrase(s) not authorized by evidence_state="
            f"{evidence_state.value!r}: {violations} -- text: {text!r}"
        )


# --------------------------------------------------------- registry entry


@dataclass(frozen=True)
class ClaimRecord:
    """One hypothesis's published claim, self-describing enough that a
    report reader never has to trust prose alone: the evidence_state
    IS the authorization, and claim_text has already been validated
    against it before this record could be constructed."""

    hypothesis: str
    evidence_state: EvidenceState
    claim_text: str
    observation_archive_hash: str
    analysis_code_hash: str
    protocol_hash: str

    def to_dict(self) -> dict[str, str]:
        return {
            "hypothesis": self.hypothesis,
            "evidence_state": self.evidence_state.value,
            "claim_text": self.claim_text,
            "observation_archive_hash": self.observation_archive_hash,
            "analysis_code_hash": self.analysis_code_hash,
            "protocol_hash": self.protocol_hash,
        }


def build_claim_record(
    *,
    hypothesis: str,
    evidence_state: EvidenceState,
    claim_text: str,
    observation_archive_hash: str,
    analysis_code_hash: str,
    protocol_hash: str,
) -> ClaimRecord:
    """The ONLY constructor path for a ClaimRecord -- language
    validation happens here, before the record can exist, not as a
    separate step a caller could forget to run."""
    assert_claim_text_is_authorized(claim_text, evidence_state=evidence_state)
    return ClaimRecord(
        hypothesis=hypothesis,
        evidence_state=evidence_state,
        claim_text=claim_text,
        observation_archive_hash=observation_archive_hash,
        analysis_code_hash=analysis_code_hash,
        protocol_hash=protocol_hash,
    )
