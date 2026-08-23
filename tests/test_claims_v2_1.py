"""TDD for erp_agent_os.claims_v2_1 (v2.1 plan, Task 11)."""

from __future__ import annotations

import pytest

from erp_agent_os.claims_v2_1 import (
    ClaimsV21Error,
    ConfirmatoryGateInputs,
    EvidenceState,
    assert_claim_text_is_authorized,
    build_claim_record,
    determine_evidence_state,
    evidence_state_for_result,
    find_forbidden_phrases,
    verdict_indicates_criterion_met,
)
from erp_agent_os.statistics_v2_1 import AnalysisResult


def _gate(**overrides) -> ConfirmatoryGateInputs:
    base = dict(
        run_completed=True,
        hashes_valid=True,
        observations_complete=True,
        registered_analysis_ran=True,
        no_open_protocol_violation=True,
    )
    base.update(overrides)
    return ConfirmatoryGateInputs(**base)


def _result(verdict: str) -> AnalysisResult:
    return AnalysisResult(
        hypothesis="h1b",
        population="main",
        unit="scenario",
        n=100,
        estimate=0.1,
        ci_low=0.05,
        ci_high=0.15,
        test="mcnemar",
        p_value=0.01,
        adjusted_p_value=0.01,
        effect_size=1.5,
        effect_size_name="odds_ratio",
        criterion="lower bound of (C - A) > 0",
        verdict=verdict,
    )


# ================================================== step 1: never defaults


def test_all_six_conditions_true_and_criterion_met_yields_supported():
    state = determine_evidence_state(_gate(), criterion_met=True)
    assert state == EvidenceState.CONFIRMATORY_SUPPORTED


@pytest.mark.parametrize(
    "flag",
    [
        "run_completed",
        "hashes_valid",
        "observations_complete",
        "registered_analysis_ran",
    ],
)
def test_flipping_any_single_condition_prevents_supported(flag):
    """No code path defaults to supported: flip exactly one of the four
    boolean gate conditions (holding criterion_met=True, the most
    favorable possible hypothesis-level input) and confirm the result
    is never CONFIRMATORY_SUPPORTED."""
    state = determine_evidence_state(_gate(**{flag: False}), criterion_met=True)
    assert state != EvidenceState.CONFIRMATORY_SUPPORTED


def test_missing_data_is_not_measured_not_supported():
    """ "Missing" data: nothing to analyze at all (analysis never ran)."""
    state = determine_evidence_state(
        _gate(registered_analysis_ran=False), criterion_met=None
    )
    assert state == EvidenceState.NOT_MEASURED


def test_raw_invalid_data_is_protocol_violation_not_supported():
    """ "Raw-invalid" data: a hash mismatch -- the campaign ran but its
    artifacts can no longer be trusted."""
    state = determine_evidence_state(_gate(hashes_valid=False), criterion_met=True)
    assert state == EvidenceState.PROTOCOL_VIOLATION


def test_open_protocol_violation_always_wins_even_with_everything_else_true():
    state = determine_evidence_state(
        _gate(no_open_protocol_violation=False), criterion_met=True
    )
    assert state == EvidenceState.PROTOCOL_VIOLATION


def test_incomplete_observations_is_inconclusive_not_supported():
    state = determine_evidence_state(
        _gate(observations_complete=False), criterion_met=True
    )
    assert state == EvidenceState.CONFIRMATORY_INCONCLUSIVE


def test_criterion_not_met_is_not_supported():
    state = determine_evidence_state(_gate(), criterion_met=False)
    assert state == EvidenceState.CONFIRMATORY_NOT_SUPPORTED


def test_criterion_inconclusive_yields_confirmatory_inconclusive():
    state = determine_evidence_state(_gate(), criterion_met=None)
    assert state == EvidenceState.CONFIRMATORY_INCONCLUSIVE


def test_no_evidence_state_reachable_ever_equals_a_bare_python_truthy_default():
    """Structural check: EvidenceState has no member literally named
    just "supported" or "success" that a lazy default could return."""
    values = {member.value for member in EvidenceState}
    assert "supported" not in values
    assert "success" not in values
    assert "confirmatory_supported" in values  # the one real positive state


@pytest.mark.parametrize(
    "verdict,expected",
    [
        ("non_inferior", True),
        ("not_non_inferior", False),
        ("superior", True),
        ("not_superior", False),
        ("fewer_tokens", True),
        ("not_fewer_tokens", False),
        ("supported", True),
        ("not_supported", False),
        ("adequate", True),
        ("not_adequate", False),
        ("abstention_reduces_false_reuse", True),
        ("inconclusive_ceiling", None),
    ],
)
def test_verdict_indicates_criterion_met_covers_every_real_verdict(verdict, expected):
    assert verdict_indicates_criterion_met(verdict) is expected


def test_verdict_indicates_criterion_met_rejects_an_unknown_verdict():
    with pytest.raises(ClaimsV21Error):
        verdict_indicates_criterion_met("definitely_not_a_real_verdict")


def test_verdict_indicates_criterion_met_rejects_observed():
    """H3b/H8 (docs/tfm-closure-no-human-v2.1.md section 8/10) are
    descriptive, not confirmatory: erp_agent_os.statistics_v2_1.
    analyze_h3b always sets verdict="observed" specifically so it
    CANNOT pass through this confirmatory gate -- a report generator
    must route it through EvidenceState.OBSERVED_DESCRIPTIVE directly.
    If "observed" were ever added to a recognized verdict set, this
    protection would silently disappear."""
    with pytest.raises(ClaimsV21Error):
        verdict_indicates_criterion_met("observed")


def test_evidence_state_for_result_wires_a_real_analysis_result_through():
    result = _result("superior")
    assert (
        evidence_state_for_result(result, _gate())
        == EvidenceState.CONFIRMATORY_SUPPORTED
    )

    result = _result("not_superior")
    assert (
        evidence_state_for_result(result, _gate())
        == EvidenceState.CONFIRMATORY_NOT_SUPPORTED
    )

    result = _result("inconclusive_ceiling")
    assert (
        evidence_state_for_result(result, _gate())
        == EvidenceState.CONFIRMATORY_INCONCLUSIVE
    )


# ======================================================= step 2: language


def test_conditionally_forbidden_phrases_are_rejected_without_support():
    for phrase in ("demostrado", "confirmado", "superior"):
        violations = find_forbidden_phrases(
            f"El sistema ha {phrase} su eficacia.",
            evidence_state=EvidenceState.CONFIRMATORY_NOT_SUPPORTED,
        )
        assert phrase in violations


def test_conditionally_forbidden_phrases_are_allowed_when_supported():
    for phrase in ("demostrado", "confirmado", "superior"):
        violations = find_forbidden_phrases(
            f"El sistema ha {phrase} su eficacia.",
            evidence_state=EvidenceState.CONFIRMATORY_SUPPORTED,
        )
        assert phrase not in violations


def test_unconditionally_forbidden_phrases_are_rejected_even_when_supported():
    """Section 8/1's amendment: "ahorro real" and "acuerdo humano" are
    never authorized, regardless of evidence_state -- unlike the three
    conditionally forbidden phrases above."""
    for phrase in ("ahorro real", "acuerdo humano"):
        violations = find_forbidden_phrases(
            f"Se ha basado en un {phrase} verificado.",
            evidence_state=EvidenceState.CONFIRMATORY_SUPPORTED,
        )
        assert phrase in violations


def test_clean_text_has_no_violations_at_any_state():
    text = "C alcanzó una diferencia estimada de 0.15 con IC95 [0.04, 0.26]."
    for state in EvidenceState:
        assert find_forbidden_phrases(text, evidence_state=state) == []


def test_assert_claim_text_is_authorized_raises_on_violation():
    with pytest.raises(ClaimsV21Error):
        assert_claim_text_is_authorized(
            "Esto queda demostrado.", evidence_state=EvidenceState.NOT_MEASURED
        )


def test_assert_claim_text_is_authorized_passes_clean_text():
    assert_claim_text_is_authorized(
        "C no mostró una ventaja estadísticamente significativa.",
        evidence_state=EvidenceState.CONFIRMATORY_NOT_SUPPORTED,
    )  # does not raise


def test_phrase_matching_is_word_bounded_not_a_naive_substring():
    """ "superior" must not falsely flag on an unrelated word that
    happens to contain it as a substring."""
    violations = find_forbidden_phrases(
        "Un valor superioridad no es lo mismo que la palabra exacta.",
        evidence_state=EvidenceState.NOT_MEASURED,
    )
    assert "superior" not in violations


# --------------------------------------------------------- ClaimRecord


def test_build_claim_record_rejects_unauthorized_text():
    with pytest.raises(ClaimsV21Error):
        build_claim_record(
            hypothesis="h1b",
            evidence_state=EvidenceState.CONFIRMATORY_NOT_SUPPORTED,
            claim_text="H1b queda demostrado.",
            observation_archive_hash="a" * 64,
            analysis_code_hash="b" * 64,
            protocol_hash="c" * 64,
        )


def test_build_claim_record_accepts_authorized_text_and_round_trips():
    record = build_claim_record(
        hypothesis="h1b",
        evidence_state=EvidenceState.CONFIRMATORY_SUPPORTED,
        claim_text="H1b queda confirmado por el criterio preregistrado.",
        observation_archive_hash="a" * 64,
        analysis_code_hash="b" * 64,
        protocol_hash="c" * 64,
    )
    payload = record.to_dict()
    assert payload["evidence_state"] == "confirmatory_supported"
    assert payload["hypothesis"] == "h1b"
    assert payload["observation_archive_hash"] == "a" * 64
